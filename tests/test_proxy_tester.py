import json
from pathlib import Path
from proxy_tester import parse_link, export_singbox_config, TestResult

def test_parse_hysteria2_full():
    link = "hy2://mypass@example.com:443?sni=mysni&insecure=1&obfs=salamander&obfs-password=obfspass&up=100&down=100"
    protocol, outbound = parse_link(link)
    assert protocol == "hysteria2"
    assert outbound["type"] == "hysteria2"
    assert outbound["server"] == "example.com"
    assert outbound["server_port"] == 443
    assert outbound["password"] == "mypass"
    assert outbound["up_mbps"] == 100
    assert outbound["down_mbps"] == 100
    assert outbound["tls"]["server_name"] == "mysni"
    assert outbound["tls"]["insecure"] is True
    assert outbound["obfs"]["type"] == "salamander"
    assert outbound["obfs"]["password"] == "obfspass"

def test_parse_hysteria2_defaults():
    link = "hy2://pass@example.com:443"
    protocol, outbound = parse_link(link)
    assert protocol == "hysteria2"
    assert outbound["up_mbps"] == 200
    assert outbound["down_mbps"] == 200
    assert outbound["tls"]["server_name"] == "example.com"
    assert outbound["tls"]["insecure"] is False

def test_parse_hysteria2_alt_scheme():
    link = "hysteria2://pass@example.com:443"
    protocol, outbound = parse_link(link)
    assert protocol == "hysteria2"

def test_export_singbox_shuffling(tmp_path):
    results = [
        TestResult(key=f"hy2://pass@node{i}.com:443", protocol="hysteria2", working=True,
                   startup_error=None, website_success_ratio=1.0, website_avg_latency_ms=100,
                   website_details=[], youtube_ok=True, youtube_speed_mbps=10, youtube_bytes=1000,
                   torrent_ok=True, torrent_speed_mbps=10, torrent_bytes=1000,
                   stability_score=1.0, total_score=1.0)
        for i in range(10)
    ]

    out1 = tmp_path / "config1.json"
    out2 = tmp_path / "config2.json"

    # We use a fixed seed for one of them to test if shuffling happens
    import random

    export_singbox_config(results, out1, shuffle_output=True)
    export_singbox_config(results, out2, shuffle_output=True)

    with open(out1) as f1, open(out2) as f2:
        cfg1 = json.load(f1)
        cfg2 = json.load(f2)

        nodes1 = [o["server"] for o in cfg1["outbounds"] if o["tag"].startswith("node-")]
        nodes2 = [o["server"] for o in cfg2["outbounds"] if o["tag"].startswith("node-")]

        # There is a very small chance that they are identical even with shuffling
        # But with 10 nodes it is 1/10! which is very small.
        assert nodes1 != nodes2
