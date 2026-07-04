import json
from pathlib import Path
from proxy_tester import parse_link, export_singbox_config, TestResult

def test_parse_hysteria_v1():
    # Test basic parsing
    scheme, out = parse_link("hysteria://auth_token@1.2.3.4:443?up=100&down=50&obfs=some_obfs")
    assert scheme == "hysteria"
    assert out["type"] == "hysteria"
    assert out["auth_str"] == "auth_token"
    assert out["up_mbps"] == 100
    assert out["down_mbps"] == 50
    assert out["obfs"] == "some_obfs"
    assert out["tls"]["enabled"] is True

    # Test auth in query param
    _, out = parse_link("hysteria://1.2.3.4:443?auth=query_auth")
    assert out["auth_str"] == "query_auth"

def test_parse_hysteria2_bandwidth():
    # Test up/down
    _, out = parse_link("hysteria2://pass@1.2.3.4:443?up=100&down=50")
    assert out["up_mbps"] == 100
    assert out["down_mbps"] == 50

    # Test up_mbps/down_mbps
    _, out = parse_link("hy2://pass@1.2.3.4:443?up_mbps=120&down_mbps=60")
    assert out["up_mbps"] == 120
    assert out["down_mbps"] == 60

    # Test defaults
    _, out = parse_link("hy2://pass@1.2.3.4:443")
    assert out["up_mbps"] == 200
    assert out["down_mbps"] == 200

    # Test custom default
    _, out = parse_link("hy2://pass@1.2.3.4:443", default_bandwidth=500)
    assert out["up_mbps"] == 500
    assert out["down_mbps"] == 500

    # Test invalid values fallback
    _, out = parse_link("hy2://pass@1.2.3.4:443?up=abc")
    assert out["up_mbps"] == 200

def test_parse_reality_fingerprint():
    _, out = parse_link("vless://uuid@1.2.3.4:443?security=reality&fp=chrome&pbk=pub&sid=sid")
    assert out["tls"]["utls"]["enabled"] is True
    assert out["tls"]["utls"]["fingerprint"] == "chrome"

def test_parse_tls_insecure():
    _, out = parse_link("trojan://pass@1.2.3.4:443?security=tls&insecure=1")
    assert out["tls"]["insecure"] is True

    _, out = parse_link("trojan://pass@1.2.3.4:443?security=tls&allowInsecure=true")
    assert out["tls"]["insecure"] is True

def test_export_shuffling(tmp_path):
    results = [
        TestResult("vless://k1@1.1.1.1:443", "vless", True, None, 1.0, 10.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 1.0),
        TestResult("vless://k2@2.2.2.2:443", "vless", True, None, 1.0, 20.0, [], True, 5.0, 500, True, 5.0, 500, 0.9, 0.9),
    ]
    out_path = tmp_path / "config.json"

    # We want to see if tags are node-1, node-2 but they can point to either k1 or k2 due to shuffle
    # To be sure, we'd need multiple runs or a mock to check if shuffle was called.
    # But we can at least check if node-1 and node-2 exist.
    export_singbox_config(results, out_path, 2, shuffle_output=True)
    config = json.loads(out_path.read_text())

    tags = [o.get("tag") for o in config["outbounds"]]
    assert "node-1" in tags
    assert "node-2" in tags

    # Check loadbalance
    lb = next(o for o in config["outbounds"] if o["tag"] == "random")
    assert lb["type"] == "loadbalance"
    assert "node-1" in lb["outbounds"]
    assert "node-2" in lb["outbounds"]

def test_export_bandwidth_propagation(tmp_path):
    results = [
        TestResult("hysteria://k1@1.1.1.1:443", "hysteria", True, None, 1.0, 10.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 1.0),
    ]
    out_path = tmp_path / "config.json"

    export_singbox_config(results, out_path, 1, shuffle_output=False, default_bandwidth=333)
    config = json.loads(out_path.read_text())

    node = next(o for o in config["outbounds"] if o["tag"] == "node-1")
    assert node["up_mbps"] == 333
    assert node["down_mbps"] == 333
