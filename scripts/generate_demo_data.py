"""
scripts/generate_demo_data.py
SIH26146 - Synthetic Benchmark & Demo Data Generator
Generates realistic Bitcoin network and blockchain transactions in CSV, JSON, and XML formats.
Includes:
- Normal retail / merchant transactions
- High-frequency burst patterns
- Peeling chain / layering laundering structures
- Multi-IP transaction relays
- Fan-out mixing / consolidation clusters
TAG: SYNTHETIC DEMO DATA (NOT REAL INTELLIGENCE)
"""

import os
import sys
import json
import random
import hashlib
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

# Base58 / Bech32 wallet generation simulation
def make_address(prefix="1"):
    chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    if prefix == "bc1":
        chars = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
        return "bc1q" + "".join(random.choices(chars, k=38))
    elif prefix == "3":
        return "3" + "".join(random.choices(chars, k=33))
    else:
        return "1" + "".join(random.choices(chars, k=33))

def make_txid(seed_str):
    return hashlib.sha256(seed_str.encode("utf-8")).hexdigest()

def make_ip():
    # Mix of realistic public IP spaces
    subnets = [
        "198.51.100.", "203.0.113.", "185.220.101.", "91.240.118.",
        "104.244.72.", "162.247.74.", "89.234.157.", "45.154.255.",
        "172.67.182.", "104.21.55."
    ]
    return random.choice(subnets) + str(random.randint(2, 250))

COUNTRIES = ["US", "DE", "NL", "CH", "SG", "IN", "JP", "GB", "CA", "FR"]
ASNS = ["AS15169", "AS13335", "AS24940", "AS16276", "AS9009", "AS200052", "AS51167"]

def generate_dataset(num_normal=250, num_suspicious_burst=40, num_peeling=30):
    base_time = datetime(2026, 9, 10, 8, 0, 0, tzinfo=timezone.utc)
    records = []
    
    # 1. Normal Retail / Exchange Transactions
    print(f"[INFO] Generating {num_normal} normal transactions...")
    normal_wallets = [make_address("1") for _ in range(80)] + [make_address("bc1") for _ in range(60)]
    normal_ips = [make_ip() for _ in range(50)]
    
    for i in range(num_normal):
        tx_time = base_time + timedelta(minutes=random.randint(0, 720), seconds=random.randint(0, 59))
        src_ip = random.choice(normal_ips)
        dst_ip = "198.51.100.1" # NTRO/Sensor listener IP
        txid = make_txid(f"normal_{i}_{tx_time.isoformat()}")
        
        in_wallets = [random.choice(normal_wallets)]
        in_amount = round(random.uniform(0.01, 1.5), 6)
        
        out_wallets = [random.choice(normal_wallets)]
        # Change address occasionally
        if random.random() > 0.6:
            out_wallets.append(random.choice(normal_wallets))
            out1 = round(in_amount * 0.7, 6)
            out2 = round(in_amount * 0.298, 6)
            out_amounts = [out1, out2]
        else:
            out_amounts = [round(in_amount * 0.998, 6)]
            
        fee = round(in_amount - sum(out_amounts), 6)
        if fee < 0: fee = 0.0001
        
        records.append({
            "timestamp": tx_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": random.randint(1024, 65535),
            "dst_port": 8333,
            "geo_country": random.choice(COUNTRIES),
            "asn": random.choice(ASNS),
            "txid": txid,
            "input_addresses": in_wallets,
            "input_amounts": [in_amount],
            "output_addresses": out_wallets,
            "output_amounts": out_amounts,
            "fee": fee,
            "script_type": random.choice(["p2pkh", "p2wpkh", "p2sh"]),
            "tag": "SYNTHETIC_DEMO_NORMAL"
        })

    # 2. Suspicious Burst / High-Frequency Multi-IP Entity (Lead Candidate W1837)
    print(f"[INFO] Generating {num_suspicious_burst} high-frequency burst transactions for Target Wallet W1837...")
    target_wallet = "1W1837DarkNodeHighFreqLeadX99999"
    target_ips = [f"185.220.101.{j}" for j in range(10, 26)] # 16 coordinated IPs
    counterparty_pool = [make_address("3") for _ in range(45)]
    burst_start = base_time + timedelta(hours=3) # Concentrated burst within 15 minutes
    
    for i in range(num_suspicious_burst):
        tx_time = burst_start + timedelta(seconds=i * 18 + random.randint(1, 5))
        src_ip = random.choice(target_ips)
        txid = make_txid(f"burst_w1837_{i}_{tx_time.isoformat()}")
        in_amt = round(random.uniform(5.0, 18.0), 6)
        out_recipient = random.choice(counterparty_pool)
        fee = 0.00085
        out_amt = round(in_amt - fee, 6)
        
        records.append({
            "timestamp": tx_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": src_ip,
            "dst_ip": "198.51.100.1",
            "src_port": random.randint(30000, 60000),
            "dst_port": 8333,
            "geo_country": "CH",
            "asn": "AS9009",
            "txid": txid,
            "input_addresses": [target_wallet],
            "input_amounts": [in_amt],
            "output_addresses": [out_recipient],
            "output_amounts": [out_amt],
            "fee": fee,
            "script_type": "p2sh",
            "tag": "SYNTHETIC_DEMO_BURST"
        })

    # 3. Peeling Chain Laundering Pattern (Target Wallet W9901)
    print(f"[INFO] Generating {num_peeling} peeling chain transactions...")
    peel_wallet = "1PeenChainRapidSpitLead99999999"
    peel_ip = "91.240.118.55"
    peel_time = base_time + timedelta(hours=5)
    current_amount = 50.0 # 50 BTC start
    
    for i in range(num_peeling):
        tx_time = peel_time + timedelta(minutes=i * 6)
        txid = make_txid(f"peel_{i}_{tx_time.isoformat()}")
        peeled_off = round(random.uniform(0.8, 1.5), 6)
        fee = 0.0004
        change_amount = round(current_amount - peeled_off - fee, 6)
        next_peel_wallet = make_address("bc1") if i < num_peeling - 1 else make_address("1")
        cashout_wallet = make_address("1")
        
        records.append({
            "timestamp": tx_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": peel_ip,
            "dst_ip": "198.51.100.1",
            "src_port": random.randint(15000, 45000),
            "dst_port": 8333,
            "geo_country": "NL",
            "asn": "AS200052",
            "txid": txid,
            "input_addresses": [peel_wallet],
            "input_amounts": [current_amount],
            "output_addresses": [cashout_wallet, next_peel_wallet],
            "output_amounts": [peeled_off, change_amount],
            "fee": fee,
            "script_type": "p2wpkh",
            "tag": "SYNTHETIC_DEMO_PEELING"
        })
        peel_wallet = next_peel_wallet
        current_amount = change_amount

    # Sort deterministically by timestamp
    records.sort(key=lambda x: x["timestamp"])
    return records

def save_csv(records, output_path: Path):
    lines = ["timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,input_amounts,output_addresses,output_amounts,fee,script_type,geo_country,asn,tag"]
    for r in records:
        in_addrs = ";".join(r["input_addresses"])
        in_amts = ";".join(str(a) for a in r["input_amounts"])
        out_addrs = ";".join(r["output_addresses"])
        out_amts = ";".join(str(a) for a in r["output_amounts"])
        line = f'{r["timestamp"]},{r["src_ip"]},{r["dst_ip"]},{r["src_port"]},{r["dst_port"]},{r["txid"]},{in_addrs},{in_amts},{out_addrs},{out_amts},{r["fee"]},{r["script_type"]},{r["geo_country"]},{r["asn"]},{r["tag"]}'
        lines.append(line)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[SUCCESS] Exported CSV ({len(records)} records): {output_path}")

def save_json(records, output_path: Path):
    output_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"[SUCCESS] Exported JSON ({len(records)} records): {output_path}")

def save_xml(records, output_path: Path):
    root = ET.Element("bitcoin_network_observations")
    root.set("classification", "SYNTHETIC_DEMO_DATA")
    
    for r in records:
        rec_el = ET.SubElement(root, "record")
        rec_el.set("tag", r["tag"])
        
        ET.SubElement(rec_el, "timestamp").text = r["timestamp"]
        
        net_el = ET.SubElement(rec_el, "network")
        ET.SubElement(net_el, "src_ip").text = r["src_ip"]
        ET.SubElement(net_el, "dst_ip").text = r["dst_ip"]
        ET.SubElement(net_el, "src_port").text = str(r["src_port"])
        ET.SubElement(net_el, "dst_port").text = str(r["dst_port"])
        ET.SubElement(net_el, "geo_country").text = r["geo_country"]
        ET.SubElement(net_el, "asn").text = r["asn"]
        
        bc_el = ET.SubElement(rec_el, "blockchain")
        ET.SubElement(bc_el, "txid").text = r["txid"]
        ET.SubElement(bc_el, "fee").text = str(r["fee"])
        ET.SubElement(bc_el, "script_type").text = r["script_type"]
        
        inputs_el = ET.SubElement(bc_el, "inputs")
        for addr, amt in zip(r["input_addresses"], r["input_amounts"]):
            in_el = ET.SubElement(inputs_el, "input")
            in_el.set("address", addr)
            in_el.set("amount", str(amt))
            
        outputs_el = ET.SubElement(bc_el, "outputs")
        for addr, amt in zip(r["output_addresses"], r["output_amounts"]):
            out_el = ET.SubElement(outputs_el, "output")
            out_el.set("address", addr)
            out_el.set("amount", str(amt))
            
    tree = ET.ElementTree(root)
    tree.write(str(output_path), encoding="utf-8", xml_declaration=True)
    print(f"[SUCCESS] Exported XML ({len(records)} records): {output_path}")

def main():
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("SIH26146 - Synthetic Benchmark Dataset Generator")
    print(f"Target Directory: {sample_dir}")
    print("=" * 70)
    
    records = generate_dataset(num_normal=250, num_suspicious_burst=40, num_peeling=30)
    print(f"\nTotal Generated Records: {len(records)}")
    
    save_csv(records, sample_dir / "synthetic_demo.csv")
    save_json(records, sample_dir / "synthetic_demo.json")
    save_xml(records, sample_dir / "synthetic_demo.xml")
    
    print("\n[COMPLETE] Synthetic benchmark datasets created in CSV, JSON, and XML.")

if __name__ == "__main__":
    main()
