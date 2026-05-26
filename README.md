# Proxy Tester

A tool to test and rank VLESS, Trojan, and Hysteria2 proxy links.

## Features

- **Protocol Support**: VLESS, Trojan, Hysteria2 (hy2).
- **Comprehensive Testing**: Measures website accessibility, YouTube streaming speed, and Torrent download performance.
- **Scoring System**: Ranks proxies based on stability, latency, and speed.
- **Sing-box Export**: Generates a ready-to-use `sing-box` client configuration.
- **Randomization & Fairness**:
  - Shuffles the order of nodes in the exported configuration to avoid user bias.
  - Includes a `random` load-balancing outbound as the default choice to distribute traffic across servers.
  - Hysteria2 nodes are configured with a performant 200 Mbps default for gaming.

## Usage

```bash
python3 proxy_tester.py --keys keys.txt --export-singbox config.json
```

### Options

- `--keys`: Path to a file containing proxy links (one per line).
- `--top`: Number of top-ranked keys to include in the export (default: 5).
- `--shuffle`: Shuffle keys before testing.
- `--auto-install`: Automatically attempt to install missing dependencies (`sing-box`, `aria2c`, `yt-dlp`).
