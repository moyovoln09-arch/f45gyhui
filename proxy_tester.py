#!/usr/bin/env python3
import argparse
import json
import os
import random
import shutil
import signal
import socket
import statistics
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import urllib.request

DEFAULT_SITES = [
    "https://www.google.com",
    "https://www.youtube.com",
    "https://github.com",
    "https://www.cloudflare.com",
]
DEFAULT_MAGNET = (
    "magnet:?xt=urn:btih:49b0124411cd26948be543abc18e6e78fbb3c33f"
    "&dn=Avatar.The.Last.Airbender.2024.S01.400p.NewComers"
)
DEFAULT_YT_VIDEO = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@dataclass
class TestResult:
    key: str
    protocol: str
    working: bool
    startup_error: Optional[str]
    website_success_ratio: float
    website_avg_latency_ms: float
    website_details: List[Dict]
    youtube_ok: bool
    youtube_speed_mbps: float
    youtube_bytes: int
    torrent_ok: bool
    torrent_speed_mbps: float
    torrent_bytes: int
    stability_score: float
    total_score: float


def run_cmd(cmd: List[str], timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def ensure_dependencies(auto_install: bool) -> None:
    needed_bins = ["sing-box", "aria2c", "yt-dlp"]
    missing_bins = [b for b in needed_bins if shutil.which(b) is None]

    if missing_bins and auto_install:
        print(f"[*] Missing binaries: {', '.join(missing_bins)}. Trying auto-install...")
        if shutil.which("apt-get") and shutil.which("sudo"):
            cmd = ["sudo", "apt-get", "update"]
            print("[+] Running:", " ".join(cmd))
            run_cmd(cmd)
            cmd = ["sudo", "apt-get", "install", "-y"] + [b for b in missing_bins if b != "yt-dlp"]
            if len(cmd) > 5:
                print("[+] Running:", " ".join(cmd))
                run_cmd(cmd)

        if "yt-dlp" in missing_bins and shutil.which("python3"):
            cmd = [
                "python3",
                "-m",
                "pip",
                "install",
                "yt-dlp",
                "--break-system-packages",
            ]
            print("[+] Running:", " ".join(cmd))
            run_cmd(cmd)

    still_missing = [b for b in needed_bins if shutil.which(b) is None]
    if still_missing:
        raise RuntimeError(
            "Missing required tools: "
            + ", ".join(still_missing)
            + ". Install them manually and retry."
        )


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def parse_link(link: str) -> Tuple[str, Dict]:
    parsed = urlparse(link.strip())
    scheme = parsed.scheme.lower()
    if scheme not in {"vless", "trojan", "hysteria2", "hy2"}:
        raise ValueError(f"Unsupported protocol: {scheme}")

    server = parsed.hostname
    port = parsed.port
    if not server or not port:
        raise ValueError("Invalid link: no host/port")

    qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}

    if scheme == "vless":
        if not parsed.username:
            raise ValueError("Invalid VLESS link: no uuid")
        outbound = {
            "type": "vless",
            "tag": "proxy",
            "server": server,
            "server_port": port,
            "uuid": unquote(parsed.username),
            "packet_encoding": "xudp",
        }
        if qs.get("flow"):
            outbound["flow"] = qs["flow"]
    elif scheme == "trojan":
        if not parsed.username:
            raise ValueError("Invalid Trojan link: no password")
        outbound = {
            "type": "trojan",
            "tag": "proxy",
            "server": server,
            "server_port": port,
            "password": unquote(parsed.username),
        }
    else:  # hysteria2 or hy2
        outbound = {
            "type": "hysteria2",
            "tag": "proxy",
            "server": server,
            "server_port": port,
            "password": unquote(parsed.username or ""),
            "up_mbps": int(qs.get("up_mbps", 200)),
            "down_mbps": int(qs.get("down_mbps", 200)),
        }
        tls = {
            "enabled": True,
            "server_name": qs.get("sni") or server,
            "insecure": qs.get("insecure", "0") in {"1", "true", "True"},
        }
        if qs.get("obfs"):
            outbound["obfs"] = {
                "type": qs["obfs"],
                "password": qs.get("obfs-password", ""),
            }
        outbound["tls"] = tls
        return scheme, outbound

    security = qs.get("security", "")
    if security in {"tls", "reality"}:
        tls = {
            "enabled": True,
            "server_name": qs.get("sni") or qs.get("host") or server,
            "insecure": qs.get("allowInsecure", "0") in {"1", "true", "True"},
        }
        if security == "reality":
            tls["reality"] = {
                "enabled": True,
                "public_key": qs.get("pbk", ""),
                "short_id": qs.get("sid", ""),
            }
        outbound["tls"] = tls

    transport = qs.get("type", "")
    if transport == "ws":
        headers = {}
        if qs.get("host"):
            headers["Host"] = qs["host"]
        outbound["transport"] = {
            "type": "ws",
            "path": qs.get("path", "/"),
            "headers": headers,
        }
    elif transport == "grpc":
        outbound["transport"] = {
            "type": "grpc",
            "service_name": qs.get("serviceName", ""),
        }
    elif transport == "httpupgrade":
        outbound["transport"] = {
            "type": "httpupgrade",
            "path": qs.get("path", "/"),
            "host": qs.get("host", ""),
        }

    return scheme, outbound


def build_config(outbound: Dict, listen_port: int, path: Path) -> None:
    cfg = {
        "log": {"level": "warn"},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": listen_port,
            }
        ],
        "outbounds": [
            outbound,
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"},
        ],
        "route": {"final": "proxy", "auto_detect_interface": True},
    }
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


def start_singbox(config_path: Path) -> subprocess.Popen:
    return subprocess.Popen(
        ["sing-box", "run", "-c", str(config_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_websites(proxy_url: str, timeout_s: int, sites: List[str]) -> Tuple[float, float, List[Dict]]:
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    )
    deadline = time.time() + timeout_s
    results = []

    while time.time() < deadline:
        for site in sites:
            if time.time() >= deadline:
                break
            t0 = time.time()
            ok = False
            status = None
            try:
                req = urllib.request.Request(site, headers={"User-Agent": "Mozilla/5.0"})
                with opener.open(req, timeout=8) as resp:
                    status = getattr(resp, "status", None) or resp.getcode()
                    ok = 200 <= int(status) < 400
            except Exception:
                ok = False
            elapsed = (time.time() - t0) * 1000
            results.append({"site": site, "ok": ok, "status": status, "latency_ms": elapsed})

    if not results:
        return 0.0, 0.0, results

    success = sum(1 for x in results if x["ok"])
    ratio = success / len(results)
    latencies = [x["latency_ms"] for x in results if x["ok"]]
    avg_latency = statistics.mean(latencies) if latencies else 9999.0
    return ratio, avg_latency, results


def test_youtube(proxy_url: str, timeout_s: int, temp_dir: Path, yt_url: str) -> Tuple[bool, float, int]:
    temp_dir.mkdir(parents=True, exist_ok=True)
    out_file = temp_dir / "yt_test.%(ext)s"
    cmd = [
        "yt-dlp",
        "--proxy",
        proxy_url,
        "--no-playlist",
        "--socket-timeout",
        "10",
        "--format",
        "bv*[height<=480]+ba/b[height<=480]/b",
        "--output",
        str(out_file),
        yt_url,
    ]
    t0 = time.time()
    try:
        proc = run_cmd(cmd, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc = None

    elapsed = max(time.time() - t0, 0.001)
    total_bytes = sum(f.stat().st_size for f in temp_dir.glob("yt_test.*") if f.is_file())
    speed_mbps = (total_bytes * 8 / 1_000_000) / elapsed

    ok = total_bytes > 0 and proc is not None and proc.returncode == 0
    return ok, speed_mbps, total_bytes


def test_torrent(proxy_url: str, timeout_s: int, temp_dir: Path, magnet: str) -> Tuple[bool, float, int]:
    temp_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "aria2c",
        "--all-proxy",
        proxy_url,
        "--seed-time=0",
        "--bt-stop-timeout=120",
        "--summary-interval=0",
        "--check-certificate=false",
        "--dir",
        str(temp_dir),
        magnet,
    ]

    t0 = time.time()
    try:
        run_cmd(cmd, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        pass
    elapsed = max(time.time() - t0, 0.001)

    total_bytes = 0
    for p in temp_dir.rglob("*"):
        if p.is_file() and not p.name.endswith(".aria2"):
            total_bytes += p.stat().st_size

    speed_mbps = (total_bytes * 8 / 1_000_000) / elapsed
    ok = total_bytes > 0
    return ok, speed_mbps, total_bytes


def calculate_score(
    website_ratio: float,
    website_latency: float,
    yt_ok: bool,
    yt_speed: float,
    tor_ok: bool,
    tor_speed: float,
) -> Tuple[float, float]:
    latency_score = max(0.0, min(1.0, 1 - website_latency / 3000))
    stability_score = (website_ratio * 0.7) + (latency_score * 0.3)

    yt_score = min(1.0, yt_speed / 12.0) * (1.0 if yt_ok else 0.2)
    tor_score = min(1.0, tor_speed / 12.0) * (1.0 if tor_ok else 0.1)

    total = stability_score * 0.4 + yt_score * 0.3 + tor_score * 0.3
    return stability_score, total


def load_keys(path: Path) -> List[str]:
    keys = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            keys.append(line)
    return keys


def evaluate_key(key: str, timeout_s: int, sites: List[str], magnet: str, yt_url: str) -> TestResult:
    with tempfile.TemporaryDirectory(prefix="keytest_") as td:
        td_path = Path(td)
        cfg_path = td_path / "config.json"

        try:
            protocol, outbound = parse_link(key)
        except Exception as e:
            return TestResult(
                key=key,
                protocol="unknown",
                working=False,
                startup_error=f"parse_error: {e}",
                website_success_ratio=0.0,
                website_avg_latency_ms=9999.0,
                website_details=[],
                youtube_ok=False,
                youtube_speed_mbps=0.0,
                youtube_bytes=0,
                torrent_ok=False,
                torrent_speed_mbps=0.0,
                torrent_bytes=0,
                stability_score=0.0,
                total_score=0.0,
            )

        port = free_port()
        build_config(outbound, port, cfg_path)
        proc = start_singbox(cfg_path)
        time.sleep(2.0)

        if proc.poll() is not None:
            err = (proc.stderr.read() or "sing-box failed").strip()
            return TestResult(
                key=key,
                protocol=protocol,
                working=False,
                startup_error=err[:600],
                website_success_ratio=0.0,
                website_avg_latency_ms=9999.0,
                website_details=[],
                youtube_ok=False,
                youtube_speed_mbps=0.0,
                youtube_bytes=0,
                torrent_ok=False,
                torrent_speed_mbps=0.0,
                torrent_bytes=0,
                stability_score=0.0,
                total_score=0.0,
            )

        proxy = f"http://127.0.0.1:{port}"

        try:
            web_ratio, web_latency, details = test_websites(proxy, timeout_s, sites)
            yt_ok, yt_speed, yt_bytes = test_youtube(proxy, timeout_s, td_path / "yt", yt_url)
            tor_ok, tor_speed, tor_bytes = test_torrent(proxy, timeout_s, td_path / "tor", magnet)
            stability, total = calculate_score(web_ratio, web_latency, yt_ok, yt_speed, tor_ok, tor_speed)
        finally:
            stop_process(proc)

        return TestResult(
            key=key,
            protocol=protocol,
            working=True,
            startup_error=None,
            website_success_ratio=web_ratio,
            website_avg_latency_ms=web_latency,
            website_details=details,
            youtube_ok=yt_ok,
            youtube_speed_mbps=yt_speed,
            youtube_bytes=yt_bytes,
            torrent_ok=tor_ok,
            torrent_speed_mbps=tor_speed,
            torrent_bytes=tor_bytes,
            stability_score=stability,
            total_score=total,
        )


def print_top(results: List[TestResult], top_n: int) -> None:
    ranked = sorted(results, key=lambda r: r.total_score, reverse=True)
    print("\n=== TOP {} KEYS ===".format(top_n))
    for idx, r in enumerate(ranked[:top_n], start=1):
        print(
            f"{idx:>2}. score={r.total_score:.3f} | {r.protocol:<6} | "
            f"sites={r.website_success_ratio:.2f} | yt={r.youtube_speed_mbps:.2f}Mbps | "
            f"tor={r.torrent_speed_mbps:.2f}Mbps"
        )


def save_report(results: List[TestResult], report_path: Path) -> None:
    data = [asdict(r) for r in sorted(results, key=lambda r: r.total_score, reverse=True)]
    report_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def export_singbox_config(results: List[TestResult], export_path: Path, top_n: int, shuffle_output: bool = True) -> None:
    working_results = [r for r in results if r.working]
    ranked = sorted(working_results, key=lambda r: r.total_score, reverse=True)[:top_n]
    if not ranked:
        print("[!] No working keys to export.")
        return

    # Randomize the order of outbounds to avoid bias
    if shuffle_output:
        random.shuffle(ranked)

    outbounds = []
    for i, res in enumerate(ranked):
        _, outbound = parse_link(res.key)
        outbound["tag"] = f"proxy-{i+1}"
        outbounds.append(outbound)

    proxy_tags = [o["tag"] for o in outbounds]

    config = {
        "log": {"level": "info"},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "::",
                "listen_port": 2080,
                "sniff": True,
            }
        ],
        "outbounds": [
            {
                "type": "selector",
                "tag": "select",
                "outbounds": ["random", "auto"] + proxy_tags,
            },
            {
                "type": "load-balance",
                "tag": "random",
                "outbounds": proxy_tags,
                "strategy": "random",
            },
            {
                "type": "urltest",
                "tag": "auto",
                "outbounds": proxy_tags,
                "url": "https://www.gstatic.com/generate_204",
                "interval": "1m",
                "tolerance": 50,
            },
        ] + outbounds + [
            {
                "type": "direct",
                "tag": "direct"
            },
            {
                "type": "dns",
                "tag": "dns-out"
            },
            {
                "type": "block",
                "tag": "block"
            }
        ],
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "dns-out"},
                {"ip_is_private": True, "outbound": "direct"}
            ],
            "final": "select",
            "auto_detect_interface": True
        }
    }

    export_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] Sing-box configuration exported to: {export_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test VLESS/Trojan/Hysteria2 keys and rank best 5 by average score."
    )
    parser.add_argument("--keys", required=True, help="Path to text file with vless://, trojan:// and hysteria2:// links")
    parser.add_argument("--top", type=int, default=5, help="How many keys to show in top")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle keys before testing")
    parser.add_argument("--timeout", type=int, default=30, help="Seconds per test category (sites/youtube/torrent)")
    parser.add_argument("--magnet", default=DEFAULT_MAGNET, help="Magnet link for torrent test")
    parser.add_argument("--youtube-url", default=DEFAULT_YT_VIDEO, help="YouTube URL for video test")
    parser.add_argument("--report", default="report.json", help="Where to save detailed report JSON")
    parser.add_argument("--export-singbox", help="Path to export final sing-box configuration")
    parser.add_argument("--no-shuffle-output", action="store_false", dest="shuffle_output", help="Disable shuffling of the outbounds in the exported sing-box configuration")
    parser.set_defaults(shuffle_output=True)
    parser.add_argument("--auto-install", action="store_true", help="Try to install missing dependencies")
    args = parser.parse_args()

    ensure_dependencies(auto_install=args.auto_install)

    key_file = Path(args.keys)
    if not key_file.exists():
        raise FileNotFoundError(f"Keys file not found: {key_file}")

    keys = load_keys(key_file)
    if not keys:
        raise ValueError("No keys found in file")

    if args.shuffle:
        print("[*] Shuffling keys...")
        random.shuffle(keys)

    print(f"[*] Loaded {len(keys)} keys")

    results = []
    for i, key in enumerate(keys, start=1):
        print(f"\n[{i}/{len(keys)}] Testing key...")
        res = evaluate_key(key, args.timeout, DEFAULT_SITES, args.magnet, args.youtube_url)
        results.append(res)
        print(f"    -> score={res.total_score:.3f}, working={res.working}, protocol={res.protocol}")

    print_top(results, args.top)
    save_report(results, Path(args.report))
    print(f"\n[+] Detailed report saved to: {args.report}")

    if args.export_singbox:
        export_singbox_config(results, Path(args.export_singbox), args.top, args.shuffle_output)


if __name__ == "__main__":
    main()
