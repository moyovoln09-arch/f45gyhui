import json
import random
from pathlib import Path
from proxy_tester import parse_link, export_singbox_config, TestResult

def test_parse_link_hysteria2():
    link = "hysteria2://pass@example.com:443?sni=sni.com&obfs=emerald&obfs-password=sec"
    proto, outbound = parse_link(link)
    assert proto == "hysteria2"
    assert outbound["type"] == "hysteria2"
    assert outbound["password"] == "pass"
    assert outbound["server"] == "example.com"
    assert outbound["server_port"] == 443
    assert outbound["tls"]["server_name"] == "sni.com"
    assert outbound["obfs"]["type"] == "emerald"
    assert outbound["obfs"]["password"] == "sec"
    assert outbound["up_mbps"] == 200
    assert outbound["down_mbps"] == 200

def test_parse_link_hy2_alias():
    link = "hy2://pass@example.com:443"
    proto, outbound = parse_link(link)
    assert proto == "hysteria2"
    assert outbound["up_mbps"] == 200

def test_parse_link_hysteria2_bandwidth():
    link = "hysteria2://pass@example.com:443?up=100&down=50"
    proto, outbound = parse_link(link)
    assert outbound["up_mbps"] == 100
    assert outbound["down_mbps"] == 50

def test_parse_link_hysteria2_fp():
    link = "hysteria2://pass@example.com:443?fp=chrome"
    proto, outbound = parse_link(link)
    assert outbound["tls"]["utls"]["fingerprint"] == "chrome"

def test_parse_link_vless_reality_fp():
    link = "vless://uuid@example.com:443?security=reality&pbk=pubkey&fp=firefox"
    proto, outbound = parse_link(link)
    assert outbound["tls"]["reality"]["public_key"] == "pubkey"
    assert outbound["tls"]["utls"]["fingerprint"] == "firefox"

def test_export_singbox_config(tmp_path):
    results = [
        TestResult(key="hy2://p1@h1:443", protocol="hysteria2", working=True, startup_error=None,
                   website_success_ratio=1.0, website_avg_latency_ms=100.0, website_details=[],
                   youtube_ok=True, youtube_speed_mbps=10.0, youtube_bytes=1000,
                   torrent_ok=True, torrent_speed_mbps=5.0, torrent_bytes=500,
                   stability_score=1.0, total_score=0.9),
        TestResult(key="hy2://p2@h2:443", protocol="hysteria2", working=True, startup_error=None,
                   website_success_ratio=1.0, website_avg_latency_ms=110.0, website_details=[],
                   youtube_ok=True, youtube_speed_mbps=9.0, youtube_bytes=900,
                   torrent_ok=True, torrent_speed_mbps=4.0, torrent_bytes=400,
                   stability_score=1.0, total_score=0.8),
    ]
    export_path = tmp_path / "config.json"
    export_singbox_config(results, top_n=2, export_path=export_path, shuffle_output=False)

    config = json.loads(export_path.read_text())

    # Check selector
    selector = next(o for o in config["outbounds"] if o["tag"] == "select")
    assert selector["default"] == "random"
    assert "random" in selector["outbounds"]

    # Check loadbalance
    lb = next(o for o in config["outbounds"] if o["tag"] == "random")
    assert lb["type"] == "loadbalance"
    assert lb["strategy"] == "random"
    assert len(lb["outbounds"]) == 2

def test_export_shuffling(tmp_path):
    results = [
        TestResult(key=f"hy2://p{i}@h{i}:443", protocol="hysteria2", working=True, startup_error=None,
                   website_success_ratio=1.0, website_avg_latency_ms=100.0, website_details=[],
                   youtube_ok=True, youtube_speed_mbps=10.0, youtube_bytes=1000,
                   torrent_ok=True, torrent_speed_mbps=5.0, torrent_bytes=500,
                   stability_score=1.0, total_score=1.0 - i/100)
        for i in range(10)
    ]

    export_path1 = tmp_path / "config1.json"
    export_path2 = tmp_path / "config2.json"

    random.seed(42)
    export_singbox_config(results, top_n=10, export_path=export_path1, shuffle_output=True)
    random.seed(43)
    export_singbox_config(results, top_n=10, export_path=export_path2, shuffle_output=True)

    config1 = json.loads(export_path1.read_text())
    config2 = json.loads(export_path2.read_text())

    tags1 = [o["tag"] for o in config1["outbounds"] if o["tag"].startswith("node-")]
    tags2 = [o["tag"] for o in config2["outbounds"] if o["tag"].startswith("node-")]

    assert tags1 != tags2
    assert set(tags1) == set(tags2)
