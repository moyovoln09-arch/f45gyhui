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
        TestResult("vless://u1@h1:443", "vless", True, None, 1.0, 100.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 1.0),
        TestResult("vless://u2@h2:443", "vless", True, None, 1.0, 100.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 0.9),
        TestResult("vless://u3@h3:443", "vless", True, None, 1.0, 100.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 0.8),
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

def test_export_singbox_structure(tmp_path):
    results = [
        TestResult("vless://u1@h1:443", "vless", True, None, 1.0, 100.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 1.0),
        TestResult("hy2://p2@h2:443", "hysteria2", True, None, 1.0, 100.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 0.9),
    ]
    output = tmp_path / "structure.json"
    export_singbox_config(results, 2, output, shuffle_output=False)

    config = json.loads(output.read_text())

    # Check selector
    selector = next(o for o in config["outbounds"] if o["tag"] == "select")
    assert selector["type"] == "selector"
    assert selector["outbounds"][0] == "random"
    assert selector["outbounds"][1] == "auto"
    assert "node-1" in selector["outbounds"]
    assert "node-2" in selector["outbounds"]

    # Check random loadbalancer
    lb = next(o for o in config["outbounds"] if o["tag"] == "random")
    assert lb["type"] == "loadbalance"
    assert lb["strategy"] == "random"
    assert "node-1" in lb["outbounds"]
    assert "node-2" in lb["outbounds"]

    # Check node tags
    node1 = next(o for o in config["outbounds"] if o["tag"] == "node-1")
    node2 = next(o for o in config["outbounds"] if o["tag"] == "node-2")
    assert node1["server"] == "h1"
    assert node2["server"] == "h2"

def test_hysteria2_bandwidth_robustness():
    link = "hy2://pass@1.1.1.1:1234?up=invalid&down="
    scheme, outbound = parse_link(link)
    assert outbound["up_mbps"] == 200
    assert outbound["down_mbps"] == 200

def test_parse_hysteria_v1_link():
    link = "hysteria://auth_secret@1.2.3.4:1234?sni=test.com&obfs=magic&upmbps=50&downmbps=100"
    scheme, outbound = parse_link(link)

    assert scheme == "hysteria"
    assert outbound["type"] == "hysteria"
    assert outbound["server"] == "1.2.3.4"
    assert outbound["server_port"] == 1234
    assert outbound["auth_str"] == "auth_secret"
    assert outbound["up_mbps"] == 50
    assert outbound["down_mbps"] == 100
    assert outbound["obfs"] == "magic"
    assert outbound["tls"]["enabled"] is True
    assert outbound["tls"]["server_name"] == "test.com"

def test_parse_hysteria_v1_defaults():
    link = "hysteria://1.1.1.1:1234?auth=secret"
    scheme, outbound = parse_link(link)

    assert scheme == "hysteria"
    assert outbound["auth_str"] == "secret"
    assert outbound["up_mbps"] == 200
    assert outbound["down_mbps"] == 200
