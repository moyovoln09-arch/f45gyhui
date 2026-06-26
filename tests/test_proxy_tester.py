import json
from pathlib import Path
from proxy_tester import parse_link, export_singbox_config, TestResult

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

    # Check selector default
    sel = next(o for o in config["outbounds"] if o["tag"] == "select")
    assert sel["default"] == "random"
