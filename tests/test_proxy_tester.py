import json
import unittest
from pathlib import Path
from proxy_tester import parse_link, export_singbox_config, TestResult

class TestProxyTester(unittest.TestCase):
    def test_parse_hysteria2_basic(self):
        link = "hysteria2://pass123@server.com:443?sni=my-sni&obfs=salamander&obfs-password=obfspass"
        proto, outbound = parse_link(link)
        self.assertEqual(proto, "hysteria2")
        self.assertEqual(outbound["type"], "hysteria2")
        self.assertEqual(outbound["server"], "server.com")
        self.assertEqual(outbound["server_port"], 443)
        self.assertEqual(outbound["password"], "pass123")
        self.assertEqual(outbound["tls"]["server_name"], "my-sni")
        self.assertEqual(outbound["obfs"]["type"], "salamander")
        self.assertEqual(outbound["obfs"]["password"], "obfspass")
        self.assertEqual(outbound["up_mbps"], 200)  # Default
        self.assertEqual(outbound["down_mbps"], 200) # Default

    def test_parse_hysteria2_bandwidth(self):
        link = "hy2://p@s.com:1234?up=50&down=100"
        proto, outbound = parse_link(link)
        self.assertEqual(outbound["up_mbps"], 50)
        self.assertEqual(outbound["down_mbps"], 100)

    def test_export_shuffling(self):
        # Create dummy results
        results = [
            TestResult(f"hy2://p{i}@s.com:{i}", "hysteria2", True, None, 1.0, 100.0, [], True, 10.0, 1000, True, 10.0, 1000, 1.0, 1.0 - i/100)
            for i in range(1, 11)
        ]

        export_path = Path("test_config.json")
        # Run export multiple times to see if order changes
        configs = []
        for _ in range(5):
            export_singbox_config(results, top_n=10, export_path=export_path, shuffle_output=True)
            cfg = json.loads(export_path.read_text())
            # Extract tags of nodes (excluding selector, random, auto, etc.)
            tags = [o["tag"] for o in cfg["outbounds"] if o["tag"].startswith("node-")]
            # Extract servers from node outbounds
            servers = [o["server_port"] for o in cfg["outbounds"] if o["tag"].startswith("node-")]
            configs.append(servers)

        # At least some configs should be different if shuffling works
        unique_configs = set(tuple(c) for c in configs)
        self.assertTrue(len(unique_configs) > 1, "Shuffling should produce different node orders")

        # Verify sequential tags (node-1, node-2...)
        cfg = json.loads(export_path.read_text())
        tags = [o["tag"] for o in cfg["outbounds"] if o["tag"].startswith("node-")]
        # Sort tags naturally to handle node-10 correctly
        tags.sort(key=lambda x: int(x.split("-")[1]))
        expected_tags = [f"node-{i}-hysteria2" for i in range(1, 11)]
        self.assertEqual(tags, expected_tags)

        if export_path.exists():
            export_path.unlink()

if __name__ == "__main__":
    unittest.main()
