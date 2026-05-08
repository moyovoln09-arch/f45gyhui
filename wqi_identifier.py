import json
import regex as re
import requests
from bs4 import BeautifulSoup, Tag, NavigableString
import os

# --- Constants from Chromium source (components/autofill/core/browser/form_parsing/form_field_parser.h) ---
# Base score for search parser. Search has the lowest priority among parsers.
K_BASE_SEARCH_PARSER_SCORE = 0.8
# Chromium requires at least 3 fillable fields to apply most heuristics.
K_MIN_REQUIRED_FIELDS_FOR_HEURISTICS = 3

# Priority scores for various parsers to simulate competition (competition defines the winning type)
# Values taken from FormFieldParser::kBase*ParserScore
PARSER_SCORES = {
    "EMAIL_ADDRESS": 1.4,
    "PHONE": 1.3,
    "TRAVEL_ORIGIN": 1.2,
    "TRAVEL_DESTINATION": 1.2,
    "ADDRESS_LINE_1": 1.1,
    "ZIP_CODE": 1.1,
    "CITY": 1.1,
    "STATE": 1.1,
    "COUNTRY": 1.1,
    "CREDIT_CARD_NUMBER": 1.0,
    "NAME_ON_CARD": 1.0,
    "CREDIT_CARD_VERIFICATION_CODE": 1.0,
    "IBAN_VALUE": 0.975,
    "PRICE": 0.95,
    "LOYALTY_MEMBERSHIP_ID": 1.1,
    "FIRST_NAME": 0.9,
    "LAST_NAME": 0.9,
    "FULL_NAME": 0.9,
    "MERCHANT_PROMO_CODE": 0.85,
    "SEARCH_TERM": K_BASE_SEARCH_PARSER_SCORE
}

class FormFieldData:
    """Represents FormFieldData from Chromium (components/autofill/core/common/form_field_data.h)"""
    def __init__(self, element_id="", name="", label="", placeholder="", control_type="INPUT_TEXT", label_source="kUnknown"):
        self.id_attribute = element_id
        self.name_attribute = name
        self.label = label
        self.placeholder = placeholder
        self.control_type = control_type
        self.label_source = label_source
        self.global_id = f"{element_id}|{name}"

    def __repr__(self):
        return f"Field(name='{self.name_attribute}', id='{self.id_attribute}', type='{self.control_type}', label='{self.label}')"

class FieldCandidates:
    """Represents FieldCandidates from Chromium (components/autofill/core/browser/form_parsing/field_candidates.h)"""
    def __init__(self):
        self.candidates = {} # type_name -> score

    def add_candidate(self, field_type, score):
        # Only keep the highest score for each type
        if field_type not in self.candidates or score > self.candidates[field_type]:
            self.candidates[field_type] = score

    def best_heuristic_type(self):
        if not self.candidates:
            return "UNKNOWN_TYPE"
        return max(self.candidates, key=self.candidates.get)

    def best_score(self):
        if not self.candidates:
            return 0.0
        return max(self.candidates.values())

class WQIIdentifier:
    """Implementation of Chromium's Web Query Interface (WQI) identification logic"""
    def __init__(self, patterns_path='legacy_regex_patterns.json'):
        if not os.path.exists(patterns_path):
            raise FileNotFoundError(f"Regex patterns file not found: {patterns_path}")
        with open(patterns_path, 'r', encoding='utf-8') as f:
            self.patterns = json.load(f)

    def map_control_type(self, element):
        """Map HTML element to Chromium FormControlType (form_autofill_util.cc)"""
        tag = element.name
        if tag == 'textarea': return 'TEXT_AREA'
        if tag == 'select': return 'SELECT_ONE'
        if tag == 'input':
            t = element.get('type', 'text').lower()
            if t == 'search': return 'INPUT_SEARCH'
            if t == 'tel': return 'INPUT_TELEPHONE'
            if t == 'number': return 'INPUT_NUMBER'
            if t == 'email': return 'INPUT_EMAIL'
            if t == 'url': return 'INPUT_URL'
            if t == 'password': return 'INPUT_PASSWORD'
            return 'INPUT_TEXT'
        return 'UNKNOWN'

    def is_autofillable(self, element):
        """Basic check if element is considered for autofill heuristics"""
        ctype = self.map_control_type(element)
        # Chromium avoids passwords in general heuristics to prevent privacy leaks
        return ctype != 'UNKNOWN' and ctype != 'INPUT_PASSWORD'

    def get_text_content(self, element):
        """Simplified FindChildText from form_autofill_util.cc"""
        if not element: return ""
        # Create a copy to not modify original soup
        temp_el = BeautifulSoup(str(element), 'lxml')
        # Remove scripts, styles
        for s in temp_el(['script', 'style']):
            s.decompose()
        return " ".join(temp_el.get_text().split()).strip()

    def infer_label(self, element, soup):
        """Label inference logic from form_autofill_util.cc"""
        # 1. <label for="..."> (MatchLabelsAndFields)
        field_id = element.get('id')
        if field_id:
            label_tag = soup.find('label', attrs={'for': field_id})
            if label_tag:
                return self.get_text_content(label_tag), "kLabelTag"

        # 2. Wrapping <label>
        parent = element.parent
        while parent:
            if parent.name == 'label':
                return self.get_text_content(parent), "kLabelTag"
            parent = parent.parent

        # 3. aria-label / aria-labelledby (GetAriaLabel)
        aria_label = element.get('aria-label')
        if aria_label: return aria_label.strip(), "kAriaLabel"

        aria_labelledby = element.get('aria-labelledby')
        if aria_labelledby:
            ids = aria_labelledby.split()
            texts = []
            for i in ids:
                l_el = soup.find(id=i)
                if l_el: texts.append(self.get_text_content(l_el))
            if any(texts): return " ".join(texts).strip(), "kAriaLabel"

        # 4. placeholder (InferLabelFromPlaceholder)
        placeholder = element.get('placeholder')
        if placeholder: return placeholder.strip(), "kPlaceHolder"

        # 5. siblings (InferLabelFromSibling - Previous)
        prev = element.previous_sibling
        while prev:
            if isinstance(prev, NavigableString):
                text = prev.strip()
                if text: return text, "kCombined"
            elif isinstance(prev, Tag):
                if prev.name in ['input', 'select', 'textarea', 'br']:
                    if prev.name != 'br': break
                else:
                    text = self.get_text_content(prev)
                    if text: return text, "kCombined"
            prev = prev.previous_sibling

        # 6. Ancestors (InferLabelFromAncestors - div, td, li, dd)
        parent = element.parent
        while parent and parent.name not in ['form', 'body']:
            if parent.name in ['div', 'td', 'li', 'dd']:
                text = self.get_text_content(parent)
                # Avoid taking entire page content if form is messy
                if text and len(text) < 150:
                    return text, "kDivTable"
            parent = parent.parent

        return "", "kUnknown"

    def extract_field_data(self, element, soup):
        """Extract metadata for a single field"""
        data = FormFieldData()
        data.id_attribute = element.get('id', '')
        data.name_attribute = element.get('name', '')
        data.placeholder = element.get('placeholder', '')
        data.control_type = self.map_control_type(element)
        data.label, data.label_source = self.infer_label(element, soup)
        # global_id is used to uniquely identify field within the page analysis
        data.global_id = f"{data.id_attribute}|{data.name_attribute}|{element.sourceline}|{element.sourcepos}"
        return data

    def match_pattern_category(self, field, category_name, lang):
        """Local heuristic matching using regex patterns (form_field_parser.cc)"""
        cat_data = self.patterns.get(category_name)
        if not cat_data: return None

        # Use page language, fallback to English
        lang_patterns = cat_data.get(lang, cat_data.get('en', []))
        if not lang_patterns: return None

        if isinstance(lang_patterns, dict):
            lang_patterns = lang_patterns.get("", [])

        for p in lang_patterns:
            pos_regex = p['positive_pattern']
            neg_regex = p.get('negative_pattern')
            match_attrs = p['match_field_attributes']
            ctrl_types = p['form_control_types']

            # Type compatibility check
            if field.control_type not in ctrl_types:
                # Chromium allows some flexibility between general TEXT and SEARCH types
                if field.control_type == 'INPUT_TEXT' and 'INPUT_SEARCH' in ctrl_types: pass
                elif field.control_type == 'INPUT_SEARCH' and 'INPUT_TEXT' in ctrl_types: pass
                else: continue

            # Attribute matching (Label first, then Name as per FormFieldParser::Match)
            matched = False
            is_high_quality = False

            # Check LABEL attribute
            if 'LABEL' in match_attrs and field.label:
                val = field.label
                if not (neg_regex and re.search(neg_regex, val, re.IGNORECASE)):
                    if re.search(pos_regex, val, re.IGNORECASE):
                        matched = True
                        # Quality check (IsLabelHigherQualityThanPlaceholder)
                        if field.label_source in ['kLabelTag', 'kPTag', 'kForId', 'kForName', 'kCombined']:
                            is_high_quality = True

            # Check NAME attribute (if not already matched with high quality)
            if not is_high_quality and 'NAME' in match_attrs:
                for val in [field.name_attribute, field.id_attribute]:
                    if not val: continue
                    if neg_regex and re.search(neg_regex, val, re.IGNORECASE): continue
                    if re.search(pos_regex, val, re.IGNORECASE):
                        matched = True
                        is_high_quality = True
                        break

            if matched:
                return {"is_high_quality": is_high_quality, "base_score": PARSER_SCORES.get(category_name, 0.0)}

        return None

    def identify(self, url_or_path):
        """Main entry point for analysis"""
        if url_or_path.startswith(('http://', 'https://')):
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                response = requests.get(url_or_path, headers=headers, timeout=10)
                response.raise_for_status()
                html = response.text
                source = url_or_path
            except Exception as e:
                return {"error": str(e)}
        else:
            if os.path.exists(url_or_path):
                with open(url_or_path, 'r', encoding='utf-8') as f:
                    html = f.read()
                source = url_or_path
            else:
                return {"error": f"File not found or invalid URL: {url_or_path}"}

        soup = BeautifulSoup(html, 'lxml')

        # 1. Language detection
        lang = 'en'
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            lang = html_tag.get('lang').split('-')[0].split('_')[0].lower()
        else:
            meta_lang = soup.find('meta', attrs={'http-equiv': 'content-language'}) or \
                        soup.find('meta', attrs={'name': 'language'})
            if meta_lang:
                lang = meta_lang.get('content', '').split('-')[0].split('_')[0].lower()

        # Categories from pattern database
        categories = [k for k in self.patterns.keys() if not k.startswith("__") and k != "PATTERN_FILE_DUMMY"]
        detected_search_fields = []

        # 2. Form extraction
        forms = soup.find_all('form')
        unassociated_els = []
        for el in soup.find_all(['input', 'textarea', 'select']):
            if not el.find_parent('form') and self.is_autofillable(el):
                unassociated_els.append(self.extract_field_data(el, soup))

        form_groups = []
        for form in forms:
            fields = []
            for el in form.find_all(['input', 'textarea', 'select']):
                if self.is_autofillable(el):
                    fields.append(self.extract_field_data(el, soup))
            if fields:
                form_groups.append(fields)

        if unassociated_els:
            form_groups.append(unassociated_els)

        # 3. Pipeline Processing
        for group in form_groups:
            group_candidates = {} # gid -> (field, candidates)
            fillable_distinct_types = set()

            for field in group:
                candidates = FieldCandidates()
                # Run all parsers to simulate Chromium's competition logic
                for cat in categories:
                    res = self.match_pattern_category(field, cat, lang)
                    if res:
                        # Score calculation (form_field_parser.cc: AddClassification)
                        # High quality matches get +2.0 boost
                        score = res['base_score'] + (2.0 if res['is_high_quality'] else 0.0)
                        candidates.add_candidate(cat, score)

                if candidates.candidates:
                    best_type = candidates.best_heuristic_type()
                    group_candidates[field.global_id] = (field, candidates)

                    # Track fillable types for Small Forms Heuristic (field_types.cc)
                    # SEARCH_TERM is unfillable (kUnfillable)
                    if best_type not in ["SEARCH_TERM", "PRICE", "NUMERIC_QUANTITY", "UNKNOWN_TYPE"]:
                        fillable_distinct_types.add(best_type)

            # 4. Rationalization (Small Forms Heuristic awareness)
            is_small_form = len(fillable_distinct_types) < K_MIN_REQUIRED_FIELDS_FOR_HEURISTICS

            for gid, (field, candidates) in group_candidates.items():
                best_type = candidates.best_heuristic_type()
                if best_type == "SEARCH_TERM":
                    detected_search_fields.append({
                        "id": field.id_attribute,
                        "name": field.name_attribute,
                        "label": field.label,
                        "label_source": field.label_source,
                        "control_type": field.control_type,
                        "confidence_score": round(candidates.best_score(), 2),
                        "would_be_hidden_by_small_form_heuristic": is_small_form
                    })

        return {
            "source": source,
            "language": lang,
            "wqi_detected_fields": detected_search_fields
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python wqi_identifier.py <URL or Path to HTML>")
        sys.exit(1)

    target = sys.argv[1]
    identifier = WQIIdentifier()
    results = identifier.identify(target)
    print(json.dumps(results, indent=2, ensure_ascii=False))
