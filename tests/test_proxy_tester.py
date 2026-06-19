import json
from pathlib import Path
import pytest
from proxy_tester import parse_link, export_singbox_config, TestResult

def test_parse_hysteria2_link():
    link = "hy2://my-password@server.com:443?sni=sni.com&insecure=1&obfs=sysnative&obfs-password=obfs-pass&up=100&down=150"
    scheme, outbound = parse_link(link)

    assert scheme == "hysteria2"
    assert outbound["type"] == "hysteria2"
    assert outbound["server"] == "server.com"
    assert outbound["server_port"] == 443
    assert outbound["password"] == "my-password"
    assert outbound["up_mbps"] == 100
    assert outbound["down_mbps"] == 150
    assert outbound["obfs"]["type"] == "sysnative"
    assert outbound["obfs"]["password"] == "obfs-pass"
    assert outbound["tls"]["enabled"] is True
    assert outbound["tls"]["server_name"] == "sni.com"
    assert outbound["tls"]["insecure"] is True

def test_parse_hysteria2_default_bandwidth():
    link = "hy2://pass@server:443"
    _, outbound = parse_link(link)
    assert outbound["up_mbps"] == 200
    assert outbound["down_mbps"] == 200

def test_export_singbox_config(tmp_path):
    results = [
        TestResult(
            key="hy2://pass1@s1:443",
            protocol="hysteria2",
            working=True,
            startup_error=None,
            website_success_ratio=1.0,
            website_avg_latency_ms=100.0,
            website_details=[],
            youtube_ok=True,
            youtube_speed_mbps=10.0,
            youtube_bytes=1000,
            torrent_ok=True,
            torrent_speed_mbps=5.0,
            torrent_bytes=1000,
            stability_score=1.0,
            total_score=1.0
        ),
        TestResult(
            key="vless://uuid@s2:443?security=tls",
            protocol="vless",
            working=True,
            startup_error=None,
            website_success_ratio=1.0,
            website_avg_latency_ms=150.0,
            website_details=[],
            youtube_ok=True,
            youtube_speed_mbps=8.0,
            youtube_bytes=800,
            torrent_ok=True,
            torrent_speed_mbps=4.0,
            torrent_bytes=800,
            stability_score=0.9,
            total_score=0.9
        )
    ]

    output_file = tmp_path / "config.json"
    export_singbox_config(results, output_file, shuffle_output=False)

    with open(output_file, "r") as f:
        config = json.load(f)

    assert "outbounds" in config
    tags = [o["tag"] for o in config["outbounds"]]
    assert "select" in tags
    assert "auto" in tags
    assert "random" in tags
    assert "node-1" in tags
    assert "node-2" in tags

    random_outbound = next(o for o in config["outbounds"] if o["tag"] == "random")
    assert random_outbound["type"] == "loadbalance"
    assert random_outbound["strategy"] == "random"
    assert "node-1" in random_outbound["outbounds"]
    assert "node-2" in random_outbound["outbounds"]
