import json
import random
from pathlib import Path
from proxy_tester import parse_link, export_singbox_config, TestResult

def test_parse_hysteria2_link():
    # Test basic hy2 link
    link = "hy2://password@example.com:443?sni=mysni&insecure=1&obfs=salamander&obfs-password=obfspass"
    protocol, outbound = parse_link(link)

    assert protocol == "hy2"
    assert outbound["type"] == "hysteria2"
    assert outbound["server"] == "example.com"
    assert outbound["server_port"] == 443
    assert outbound["password"] == "password"
    assert outbound["up_mbps"] == 200 # default
    assert outbound["down_mbps"] == 200 # default
    assert outbound["tls"]["enabled"] is True
    assert outbound["tls"]["server_name"] == "mysni"
    assert outbound["tls"]["insecure"] is True
    assert outbound["obfs"]["type"] == "salamander"
    assert outbound["obfs"]["password"] == "obfspass"

    # Test hysteria2 link with explicit bandwidth
    link2 = "hysteria2://pass@1.1.1.1:8888?up=100&down_mbps=50"
    protocol2, outbound2 = parse_link(link2)
    assert protocol2 == "hysteria2"
    assert outbound2["up_mbps"] == 100
    assert outbound2["down_mbps"] == 50

def test_parse_vless_reality_fp():
    link = "vless://uuid@example.com:443?security=reality&sni=mysni&pbk=mypbk&sid=mysid&fp=chrome"
    protocol, outbound = parse_link(link)
    assert protocol == "vless"
    assert outbound["tls"]["utls"]["fingerprint"] == "chrome"

def test_export_randomization(tmp_path):
    # Mock some results
    results = [
        TestResult(
            key=f"vless://uuid{i}@host{i}:443?security=tls",
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
            stability_score=1.0,
            total_score=1.0 - (i * 0.1)
        )
        for i in range(5)
    ]

    output_path = tmp_path / "config.json"

    # We want to check if randomization happens.
    # Since it's random, we might need multiple checks or just verify it calls random.shuffle
    # Better: check if the tags node-1, node-2... correspond to different servers in different exports

    servers_runs = []
    for _ in range(20):
        export_singbox_config(results, output_path, top_n=5, shuffle_output=True)
        config = json.loads(output_path.read_text())

        # Get server list in order of node-1, node-2...
        outbounds = {o["tag"]: o.get("server") for o in config["outbounds"] if o["tag"].startswith("node-")}
        server_order = [outbounds[f"node-{i}"] for i in range(1, 6)]
        servers_runs.append(tuple(server_order))

    # It's highly unlikely that 20 runs produce the exact same order if shuffled
    assert len(set(servers_runs)) > 1
