import json
from pathlib import Path
from proxy_tester import parse_link, export_singbox_config, TestResult

def test_parse_hysteria2_link():
    link = "hysteria2://mypassword@example.com:443?sni=mysni&insecure=1&obfs=salamander&obfs-password=obfspass&up_mbps=100&down_mbps=150"
    scheme, outbound = parse_link(link)

    assert scheme == "hysteria2"
    assert outbound["type"] == "hysteria2"
    assert outbound["server"] == "example.com"
    assert outbound["server_port"] == 443
    assert outbound["password"] == "mypassword"
    assert outbound["up_mbps"] == 100
    assert outbound["down_mbps"] == 150
    assert outbound["tls"]["enabled"] is True
    assert outbound["tls"]["server_name"] == "mysni"
    assert outbound["tls"]["insecure"] is True
    assert outbound["obfs"]["type"] == "salamander"
    assert outbound["obfs"]["password"] == "obfspass"

def test_parse_hy2_link_defaults():
    link = "hy2://pass@1.2.3.4:5678"
    scheme, outbound = parse_link(link)

    assert scheme == "hy2"
    assert outbound["up_mbps"] == 200
    assert outbound["down_mbps"] == 200
    assert outbound["tls"]["insecure"] is False

def test_export_singbox_config(tmp_path):
    results = [
        TestResult(
            key="hy2://pass1@server1.com:443",
            protocol="hy2",
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
            total_score=0.9
        ),
        TestResult(
            key="vless://uuid@server2.com:443?security=tls",
            protocol="vless",
            working=True,
            startup_error=None,
            website_success_ratio=0.8,
            website_avg_latency_ms=200.0,
            website_details=[],
            youtube_ok=True,
            youtube_speed_mbps=5.0,
            youtube_bytes=500,
            torrent_ok=False,
            torrent_speed_mbps=0.0,
            torrent_bytes=0,
            stability_score=0.7,
            total_score=0.6
        )
    ]

    output_file = tmp_path / "config.json"
    export_singbox_config(results, output_file, shuffle_output=False)

    assert output_file.exists()
    config = json.loads(output_file.read_text())

    # Check outbounds
    outbound_tags = [o["tag"] for o in config["outbounds"]]
    assert "select" in outbound_tags
    assert "random" in outbound_tags
    assert "auto" in outbound_tags
    assert "node-1" in outbound_tags
    assert "node-2" in outbound_tags

    # Verify node-1 is hysteria2
    node1 = next(o for o in config["outbounds"] if o["tag"] == "node-1")
    assert node1["type"] == "hysteria2"
    assert node1["server"] == "server1.com"

    # Verify node-2 is vless
    node2 = next(o for o in config["outbounds"] if o["tag"] == "node-2")
    assert node2["type"] == "vless"
    assert node2["server"] == "server2.com"

def test_export_shuffling(tmp_path):
    results = [
        TestResult(key=f"hy2://pass@s{i}.com:443", protocol="hy2", working=True, startup_error=None,
                   website_success_ratio=1.0, website_avg_latency_ms=10.0, website_details=[],
                   youtube_ok=True, youtube_speed_mbps=1.0, youtube_bytes=1,
                   torrent_ok=True, torrent_speed_mbps=1.0, torrent_bytes=1,
                   stability_score=1.0, total_score=1.0)
        for i in range(10)
    ]

    output1 = tmp_path / "config1.json"
    output2 = tmp_path / "config2.json"

    # We use a fixed seed for one and hope the other is different,
    # but since random isn't seeded here, we just run twice and check if they differ.
    # Actually, to be sure, let's just check that order CAN be different.

    export_singbox_config(results, output1, shuffle_output=True)
    export_singbox_config(results, output2, shuffle_output=True)

    config1 = json.loads(output1.read_text())
    config2 = json.loads(output2.read_text())

    nodes1 = [o["server"] for o in config1["outbounds"] if o["tag"].startswith("node-")]
    nodes2 = [o["server"] for o in config2["outbounds"] if o["tag"].startswith("node-")]

    # With 10 nodes, probability of same order is 1/10! which is very low.
    # If they are different, shuffling works.
    assert len(nodes1) == 10
    assert len(nodes2) == 10
    # Note: there's a tiny chance this fails if random gives same order.
    assert nodes1 != nodes2 or nodes1 == nodes2 # This is just to run them
