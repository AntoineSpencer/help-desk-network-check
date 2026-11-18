# help-desk-network-check

A small Help Desk network diagnostic, written in Python (standard library only).
It checks a host layer by layer — DNS, ping, then a TCP port — and saves the
result as a ticket-style note, the way you'd log it on a support ticket.

## Why this project exists

For a Help Desk role, "I can't get online" is almost always one of three things:
DNS failed, the network path is down, or the service itself isn't answering.
This script tests each layer separately so the answer is which layer failed,
not a guess.

## What it uses

- **Python** — the whole script, stdlib only, no packages to install
- **Linux** — runs from a terminal; uses the system `ping`
- **Nmap** — optional; `--with-nmap` runs `nmap -sn` if nmap is installed,
  and says so plainly if it isn't
- **Wireshark** — see "Watch it in Wireshark" below

## Run it

```bash
python3 network_check.py
python3 network_check.py --host example.com --port 443
python3 network_check.py --host 8.8.8.8 --no-ping
python3 network_check.py --host example.com --with-nmap
```

It prints the results and saves them to a file like
`network-check-20261116-153000.log`.

Sample output — from a real run in this workspace on 2026-11-16 (DNS and TCP
passed; ping failed there only because that sandbox blocks raw ICMP sockets
— `ping: socket: Operation not permitted` — which is itself a useful
diagnostic: ping failing while TCP passes means the path isn't dead, ICMP
is just blocked):

```
Help Desk network check — 2026-11-16 20:25 UTC
Target: example.com (TCP port 443)

[PASS] DNS: resolved example.com -> 198.18.180.216
[FAIL] Ping (ICMP): ping to 198.18.180.216 failed (exit 2)
[PASS] TCP :443: TCP example.com:443 open (1 ms)

Result: 1 check(s) failed — Ping (ICMP). Start with the first failure: DNS first, then ping, then TCP.
```

On a normal Linux machine where ping is allowed, the ping line should read
`[PASS]`. The full log of that run is saved as `sample-output.txt`.

## Watch it in Wireshark

Run the script while capturing, then filter:

- `dns` — see the lookup for the hostname
- `icmp` — see the ping requests and replies
- `tcp.port == 443` — see the TCP handshake to the port

If DNS passes but ping fails, the problem is the path, not name resolution.
If ping passes but TCP fails, the host is up and the service/port is the
problem. That distinction is the whole point of the tool.

## How to put it on GitHub

```bash
git init
git add network_check.py README.md
git commit -m "Add Help Desk network diagnostic (DNS, ping, TCP)"
git branch -M main
git remote add origin https://github.com/AntoineSpencer/help-desk-network-check.git
git push -u origin main
```

(Only run the `git remote add` / `push` lines if you create that repo first
on github.com — the repo name above is a suggestion, not a claim it exists.)

## What I can explain about it

- How DNS resolution works and why it fails first when it fails
- ICMP echo (ping) vs. TCP connect, and what each one proves
- Reading the log file as a ticket note: what failed, in what order
- What the Wireshark capture shows for each check

## Limits — stated honestly

- This is a learning / portfolio project, not a production monitoring tool.
- It only tests hosts you point it at. Only test hosts you own or public
  test hosts like `example.com` — never scan a network you don't have
  permission to test.
- The Nmap step is optional and skipped with a clear message when nmap
  isn't installed.
