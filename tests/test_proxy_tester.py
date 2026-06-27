import json
import pytest
from pathlib import Path
from proxy_tester import parse_link, export_singbox_config, TestResult

def test_parse_hysteria2_basic():
    link = "hysteria2://pass@example.com:443?sni=mysni&obfs=simple&obfs-password=obfspass"
    scheme, outbound = parse_link(link)
    assert scheme == "hysteria2"
    assert outbound["type"] == "hysteria2"
    assert outbound["server"] == "example.com"
    assert outbound["server_port"] == 443
    assert outbound["password"] == "pass"
    assert outbound["up_mbps"] == 200
    assert outbound["down_mbps"] == 200
    assert outbound["obfs"]["type"] == "simple"
    assert outbound["obfs"]["password"] == "obfspass"
    assert outbound["tls"]["server_name"] == "mysni"

def test_parse_hysteria2_bandwidth():
    link = "hy2://pass@example.com:443?up=100&down=50"
    scheme, outbound = parse_link(link)
    assert outbound["up_mbps"] == 100
    assert outbound["down_mbps"] == 50

def test_export_singbox_config_randomization(tmp_path):
    results = [
        TestResult(
            key=f"vless://uuid{i}@server{i}.com:443?security=tls",
            protocol="vless",
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
            torrent_bytes=500,
            stability_score=0.9,
            total_score=0.8 + (i * 0.01)
        ) for i in range(5)
    ]

    out_path = tmp_path / "config.json"
    export_singbox_config(results, top_n=5, output_path=out_path, shuffle_output=True)

    config = json.loads(out_path.read_text())

    # Check for random and select outbounds
    outbound_tags = [o["tag"] for o in config["outbounds"]]
    assert "select" in outbound_tags
    assert "random" in outbound_tags
    assert "auto" in outbound_tags

    select = next(o for o in config["outbounds"] if o["tag"] == "select")
    assert select["outbounds"][0] == "random"

    random_lb = next(o for o in config["outbounds"] if o["tag"] == "random")
    assert random_lb["type"] == "loadbalance"
    assert random_lb["strategy"] == "random"

    # Check that nodes have sequential tags node-1, node-2...
    node_tags = [t for t in outbound_tags if t.startswith("node-")]
    assert len(node_tags) == 5
    assert "node-1" in node_tags
    assert "node-5" in node_tags
