#!/usr/bin/env python3
"""help-desk-network-check — a small Help Desk network diagnostic.

What it does, in plain terms:
  1. Resolves a hostname to an IP (DNS check).
  2. Pings a host (ICMP reachability check).
  3. Tries a TCP connection to a host/port (is the service listening?).
  4. Writes the results as a ticket-style note to a timestamped log file.

Why this matters for Help Desk work: "I can't get online" is usually one of
DNS, the local link, or the remote service. This script checks each layer
separately so you can say which one failed, instead of guessing.

Tools it touches: Python (stdlib only — no installs), Linux `ping`,
and the same traffic you can watch in Wireshark (see README.md).
Nmap is used only if it is installed; if it is not, the script says so
and still runs the Python checks.

Usage:
    python3 network_check.py
    python3 network_check.py --host example.com --port 443
    python3 network_check.py --host 8.8.8.8 --no-ping

Only run this against hosts you own or public test hosts (the defaults).
Do not scan networks or hosts you do not have permission to test.
"""

import argparse
import datetime
import shutil
import socket
import subprocess
import sys
import time

DEFAULT_HOST = "example.com"
DEFAULT_PORT = 443


def dns_check(hostname: str) -> tuple[bool, str]:
    """Resolve a hostname. Returns (ok, detail)."""
    try:
        ip = socket.gethostbyname(hostname)
        return True, f"resolved {hostname} -> {ip}"
    except socket.gaierror as exc:
        return False, f"DNS failed for {hostname}: {exc}"


def ping_check(host: str, count: int = 2) -> tuple[bool, str]:
    """Ping a host using the system ping. Returns (ok, detail)."""
    ping = shutil.which("ping")
    if ping is None:
        return False, "ping not found on this system"
    try:
        result = subprocess.run(
            [ping, "-c", str(count), "-W", "2", host],
            capture_output=True, text=True, timeout=15,
        )
    except subprocess.TimeoutExpired:
        return False, f"ping to {host} timed out"
    if result.returncode == 0:
        # Last line of ping output usually holds the round-trip summary.
        summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "reply received"
        return True, f"ping to {host} OK ({summary})"
    return False, f"ping to {host} failed (exit {result.returncode})"


def tcp_check(host: str, port: int, timeout: float = 5.0) -> tuple[bool, str]:
    """Try a TCP connection. Returns (ok, detail)."""
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed_ms = (time.monotonic() - start) * 1000
            return True, f"TCP {host}:{port} open ({elapsed_ms:.0f} ms)"
    except OSError as exc:
        return False, f"TCP {host}:{port} failed: {exc}"


def nmap_check(host: str) -> tuple[bool, str]:
    """Optional: a quick nmap ping-scan, only if nmap is installed."""
    nmap = shutil.which("nmap")
    if nmap is None:
        return False, "nmap not installed on this system — skipping (Python checks still ran)"
    try:
        result = subprocess.run(
            [nmap, "-sn", host], capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, "nmap scan timed out"
    if result.returncode == 0:
        return True, f"nmap -sn {host}: host up"
    return False, f"nmap -sn {host} failed (exit {result.returncode})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Help Desk network diagnostic")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help="host to check (default: %(default)s)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="TCP port to test (default: %(default)s)")
    parser.add_argument("--no-ping", action="store_true",
                        help="skip the ping check")
    parser.add_argument("--with-nmap", action="store_true",
                        help="also run nmap -sn if nmap is installed")
    args = parser.parse_args()

    now = datetime.datetime.now().astimezone()
    lines = [
        f"Help Desk network check — {now:%Y-%m-%d %H:%M %Z}",
        f"Target: {args.host} (TCP port {args.port})",
        "",
    ]
    checks = []

    ok, detail = dns_check(args.host)
    checks.append(("DNS", ok, detail))

    if not args.no_ping:
        # Ping the resolved IP when we have one, so DNS and ping stay separate.
        ping_target = args.host
        try:
            ping_target = socket.gethostbyname(args.host)
        except socket.gaierror:
            pass
        ok, detail = ping_check(ping_target)
        checks.append(("Ping (ICMP)", ok, detail))

    ok, detail = tcp_check(args.host, args.port)
    checks.append((f"TCP :{args.port}", ok, detail))

    if args.with_nmap:
        ok, detail = nmap_check(args.host)
        checks.append(("Nmap -sn", ok, detail))

    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        lines.append(f"[{status}] {name}: {detail}")

    failed = [name for name, ok, _ in checks if not ok]
    lines.append("")
    if failed:
        lines.append(f"Result: {len(failed)} check(s) failed — {', '.join(failed)}. "
                     "Start with the first failure: DNS first, then ping, then TCP.")
    else:
        passed = ", ".join(name for name, _, _ in checks)
        lines.append(f"Result: all checks passed — {passed} all responded.")

    report = "\n".join(lines)
    print(report)

    log_name = f"network-check-{now:%Y%m%d-%H%M%S}.log"
    with open(log_name, "w", encoding="utf-8") as log:
        log.write(report + "\n")
    print(f"\nSaved ticket note: {log_name}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
