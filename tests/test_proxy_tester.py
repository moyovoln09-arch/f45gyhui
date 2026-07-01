import json
import pytest
from pathlib import Path
from proxy_tester import parse_link, export_singbox_config, TestResult

def test_parse_hysteria2_link():
    link = "hysteria2://pass@1.2.3.4:1234?sni=test.com&obfs=magic&obfs-password=secret&up=50&down=100"
    scheme, outbound = parse_link(link)

    assert scheme == "hysteria2"
    assert outbound["type"] == "hysteria2"
    assert outbound["server"] == "1.2.3.4"
    assert outbound["server_port"] == 1234
    assert outbound["password"] == "pass"
    assert outbound["up_mbps"] == 50
    assert outbound["down_mbps"] == 100
    assert outbound["obfs"]["type"] == "magic"
    assert outbound["obfs"]["password"] == "secret"
    assert outbound["tls"]["enabled"] is True
    assert outbound["tls"]["server_name"] == "test.com"

def test_parse_hysteria2_defaults():
    link = "hy2://pass@5.6.7.8:5678"
    scheme, outbound = parse_link(link)

    assert scheme == "hy2"
    assert outbound["up_mbps"] == 200
    assert outbound["down_mbps"] == 200
    assert outbound["tls"]["server_name"] == "5.6.7.8"

def test_export_singbox_randomization(tmp_path):
    results = [
        TestResult("vless://u1@h1:443", "vless", True, None, 1.0, 100.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 1.0, {"type": "vless", "server": "h1"}),
        TestResult("vless://u2@h2:443", "vless", True, None, 1.0, 100.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 0.9, {"type": "vless", "server": "h2"}),
        TestResult("vless://u3@h3:443", "vless", True, None, 1.0, 100.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 0.8, {"type": "vless", "server": "h3"}),
    ]

    output = tmp_path / "config.json"

    # Run export multiple times to see if it shuffles
    all_tags = []
    for _ in range(20):
        export_singbox_config(results, 3, output, shuffle_output=True)
        config = json.loads(output.read_text())
        # Find which server became node-1
        node1 = next(o for o in config["outbounds"] if o["tag"] == "node-1")
        all_tags.append(node1["server"])

    # If it's truly random, we should see more than one unique server as node-1 over 20 runs
    assert len(set(all_tags)) > 1

def test_hysteria2_bandwidth_robustness():
    link = "hy2://pass@1.1.1.1:1234?up=invalid&down="
    scheme, outbound = parse_link(link)
    assert outbound["up_mbps"] == 200
    assert outbound["down_mbps"] == 200

def test_parse_hysteria2_obfs_none():
    link = "hy2://pass@1.2.3.4:1234?obfs=none"
    _, outbound = parse_link(link)
    assert "obfs" not in outbound

def test_export_singbox_selector_priority(tmp_path):
    results = [
        TestResult("vless://u1@h1:443", "vless", True, None, 1.0, 100.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 1.0, {"type": "vless", "server": "h1"}),
    ]
    output = tmp_path / "config.json"
    export_singbox_config(results, 1, output)
    config = json.loads(output.read_text())

    selector = next(o for o in config["outbounds"] if o["tag"] == "select")
    # 'random' should be the first choice in the selector
    assert selector["outbounds"][0] == "random"

def test_parse_hysteria2_custom_default_bandwidth():
    link = "hy2://pass@1.2.3.4:1234"
    scheme, outbound = parse_link(link, default_hy2_bw=500)
    assert outbound["up_mbps"] == 500
    assert outbound["down_mbps"] == 500

def test_parse_hysteria_v1_link():
    link = "hysteria://auth_str@1.2.3.4:1234?sni=test.com&obfs=magic&up=50&down=100"
    scheme, outbound = parse_link(link)

    assert scheme == "hysteria"
    assert outbound["type"] == "hysteria"
    assert outbound["server"] == "1.2.3.4"
    assert outbound["server_port"] == 1234
    assert outbound["auth_str"] == "auth_str"
    assert outbound["up_mbps"] == 50
    assert outbound["down_mbps"] == 100
    assert outbound["obfs"] == "magic"
    assert outbound["tls"]["enabled"] is True
    assert outbound["tls"]["server_name"] == "test.com"

def test_parse_hysteria_v1_defaults():
    link = "hysteria://pass@5.6.7.8:5678"
    scheme, outbound = parse_link(link)

    assert scheme == "hysteria"
    assert outbound["up_mbps"] == 200
    assert outbound["down_mbps"] == 200
    assert outbound["tls"]["server_name"] == "5.6.7.8"

def test_evaluate_key_uses_custom_bandwidth(monkeypatch):
    # Mock parse_link to see if it receives the correct default_hy2_bw
    captured_bw = []
    def mock_parse_link(link, default_hy2_bw=200):
        captured_bw.append(default_hy2_bw)
        return "hy2", {"type": "hysteria2", "tag": "proxy"}

    monkeypatch.setattr("proxy_tester.parse_link", mock_parse_link)
    # Mock other things to avoid actual execution
    monkeypatch.setattr("proxy_tester.free_port", lambda: 12345)
    monkeypatch.setattr("proxy_tester.build_config", lambda *a: None)

    class MockProc:
        def poll(self): return 0
        def terminate(self): pass
        @property
        def stderr(self):
            import io
            return io.StringIO("error")

    monkeypatch.setattr("proxy_tester.start_singbox", lambda *a: MockProc())

    from proxy_tester import evaluate_key
    evaluate_key("hy2://p@h:443", 1, [], "mag", "yt", default_hy2_bw=456)
    assert 456 in captured_bw
