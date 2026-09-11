#!/usr/bin/env python3
import os
import sys
import json
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd

def inspect_csv(file_path: Path):
    print("=" * 70)
    print(f"Inspecting CSV File: {file_path.name} ({file_path.stat().st_size:,} bytes)")
    print("=" * 70)
    try:
        df = pd.read_csv(file_path)
        print(f"Total Records: {len(df):,}")
        print(f"Columns ({len(df.columns)}): {list(df.columns)}")
        print("\nData Types & Non-Null Counts:")
        for col in df.columns:
            null_count = int(df[col].isnull().sum())
            sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
            print(f"  - {col:<25} | dtype: {str(df[col].dtype):<10} | Nulls: {null_count:<6} | Sample: {repr(sample_val)[:50]}")
        
        dup_count = int(df.duplicated().sum())
        print(f"\nDuplicate Rows: {dup_count}")
        
        print("\nSIH26146 Field Mapping Detection:")
        cols_lower = {c.lower(): c for c in df.columns}
        for expected in ["timestamp", "src_ip", "dst_ip", "src_port", "dst_port", "txid", "inputs", "outputs", "fee", "script_type", "country", "asn"]:
            matched = [cols_lower[k] for k in cols_lower if expected in k]
            print(f"  - '{expected}': {matched if matched else 'NOT FOUND'}")
            
        return {
            "format": "CSV",
            "filename": file_path.name,
            "record_count": len(df),
            "columns": list(df.columns),
            "duplicates": dup_count
        }
    except Exception as e:
        print(f"Error inspecting CSV: {e}")
        return {"format": "CSV", "error": str(e)}

def inspect_json(file_path: Path):
    print("=" * 70)
    print(f"Inspecting JSON File: {file_path.name} ({file_path.stat().st_size:,} bytes)")
    print("=" * 70)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            record_count = len(data)
            print(f"Structure: Array of JSON Objects. Total Records: {record_count:,}")
            if record_count > 0:
                sample = data[0]
                print(f"Keys in first record ({len(sample.keys())}):")
                for k, v in sample.items():
                    print(f"  - {k:<25} | type: {type(v).__name__:<10} | Sample: {repr(v)[:50]}")
        elif isinstance(data, dict):
            print(f"Structure: Top-level JSON Dict with keys: {list(data.keys())}")
            record_count = 1
        else:
            record_count = 0
            print(f"Structure: {type(data)}")
            
        return {
            "format": "JSON",
            "filename": file_path.name,
            "record_count": record_count
        }
    except Exception as e:
        print(f"Error inspecting JSON: {e}")
        return {"format": "JSON", "error": str(e)}

def inspect_xml(file_path: Path):
    print("=" * 70)
    print(f"Inspecting XML File: {file_path.name} ({file_path.stat().st_size:,} bytes)")
    print("=" * 70)
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        children = list(root)
        print(f"Root Tag: <{root.tag}> | Child Elements: {len(children):,}")
        if children:
            first_child = children[0]
            print(f"First Child Tag: <{first_child.tag}> with fields:")
            for sub in first_child:
                print(f"  - <{sub.tag}> : {repr(sub.text)[:50]}")
        return {
            "format": "XML",
            "filename": file_path.name,
            "record_count": len(children)
        }
    except Exception as e:
        print(f"Error inspecting XML: {e}")
        return {"format": "XML", "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Inspect raw datasets for SIH26146")
    parser.add_argument("--dir", type=str, default="data/raw", help="Directory containing raw files")
    parser.add_argument("--file", type=str, default=None, help="Specific file to inspect")
    args = parser.parse_args()

    target_dir = Path(args.dir)
    target_files = []

    if args.file:
        target_files.append(Path(args.file))
    elif target_dir.exists():
        for ext in ["*.csv", "*.json", "*.xml"]:
            target_files.extend(list(target_dir.glob(ext)))

    print(f"SIH26146 Dataset Inspector")
    print(f"Search Directory: {target_dir.resolve()}")
    print(f"Found {len(target_files)} dataset file(s).")

    if not target_files:
        print("\n[NOTICE] No raw files found in data/raw/ yet.")
        print("As specified by SIH 2026 Problem Statement 5 (National Technical Research Organisation):")
        print("  - 'Dataset Link: Nil'")
        print("  - 'Participants will work with a synthetic dataset modelled on real Bitcoin P2P/transaction fields.'")
        print("Use 'scripts/generate_demo_data.py' (Phase 5) to generate benchmark datasets.")
        return

    for fp in target_files:
        suffix = fp.suffix.lower()
        if suffix == ".csv":
            inspect_csv(fp)
        elif suffix == ".json":
            inspect_json(fp)
        elif suffix == ".xml":
            inspect_xml(fp)

if __name__ == "__main__":
    main()
