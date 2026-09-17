"""
backend/app/ingestion/pipeline.py
Ingestion pipeline for SIH26146.
Supports CSV, JSON, and XML formats.
Performs:
1. Format detection & parsing
2. Schema & field validation
3. Verbatim raw record logging with validation statuses
4. Ingestion batch tracking
5. Relational normalization into DuckDB tables:
   - transactions
   - transaction_inputs
   - transaction_outputs
   - network_observations
   - wallets
   - ip_addresses
   - entities
"""

import os
import sys
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET
import pandas as pd

from app.database.connection import DatabaseManager
from app.utils.validation import validate_record, validate_timestamp
from app.utils.geoip import resolve_ip

class IngestionPipeline:
    def __init__(self, db_conn=None):
        self.db_mgr = DatabaseManager.get_instance()
        self._external_conn = db_conn

    def _get_conn(self):
        return self._external_conn if self._external_conn else self.db_mgr.get_connection()

    def detect_format(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()
        if ext == ".csv":
            return "CSV"
        elif ext == ".json":
            return "JSON"
        elif ext == ".xml":
            return "XML"
        raise ValueError(f"Unsupported file format for ingestion: {file_path.name}")

    def parse_csv(self, file_path: Path) -> List[Dict[str, Any]]:
        df = pd.read_csv(file_path)
        records = []
        
        # Build normalized column index
        col_map = {str(c).strip().lower(): c for c in df.columns}
        def get_val(r, *candidates):
            for c in candidates:
                c_low = c.strip().lower()
                if c_low in col_map:
                    val = r[col_map[c_low]]
                    if pd.notna(val):
                        return val
            return None

        def parse_array_field(raw):
            if pd.isna(raw) or raw is None or raw == "":
                return []
            if isinstance(raw, list):
                return raw
            s = str(raw).strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    return json.loads(s)
                except Exception:
                    clean = s[1:-1].replace("'", "").replace('"', "")
                    return [x.strip() for x in clean.split(",") if x.strip()]
            if ";" in s:
                return [x.strip() for x in s.split(";") if x.strip()]
            if "," in s:
                return [x.strip() for x in s.split(",") if x.strip()]
            return [s]

        def parse_amount_array(raw):
            arr = parse_array_field(raw)
            out = []
            for item in arr:
                try:
                    out.append(float(item))
                except (ValueError, TypeError):
                    pass
            return out

        for idx, row in df.iterrows():
            r_dict = row.to_dict()
            rec = {
                "timestamp": get_val(row, "timestamp", "time", "block_time") or r_dict.get("timestamp"),
                "txid": get_val(row, "txid", "tx_id", "hash") or r_dict.get("txid"),
                "src_ip": get_val(row, "src_ip", "source_ip", "ip") or r_dict.get("src_ip"),
                "dst_ip": get_val(row, "dst_ip", "destination_ip") or r_dict.get("dst_ip", "0.0.0.0"),
                "src_port": get_val(row, "src_port", "source_port") or r_dict.get("src_port", 8333),
                "dst_port": get_val(row, "dst_port", "destination_port") or r_dict.get("dst_port", 8333),
                "fee": float(get_val(row, "fee", "tx_fee") or r_dict.get("fee", 0.0) or 0.0),
                "script_type": get_val(row, "script_type") or r_dict.get("script_type", "p2pkh"),
                "geo_country": get_val(row, "geo_country", "country") or r_dict.get("geo_country", ""),
                "asn": get_val(row, "asn") or r_dict.get("asn", ""),
                "scenario": get_val(row, "scenario", "label") or r_dict.get("scenario", "NORMAL")
            }

            raw_in_addr = get_val(row, "input_addresses[]", "input_addresses", "inputs", "in_addr")
            raw_out_addr = get_val(row, "output_addresses[]", "output_addresses", "outputs", "out_addr")
            raw_in_amt = get_val(row, "input_amounts[]", "input_amounts", "in_amount")
            raw_out_amt = get_val(row, "output_amounts[]", "output_amounts", "out_amount")

            rec["input_addresses"] = parse_array_field(raw_in_addr)
            rec["output_addresses"] = parse_array_field(raw_out_addr)
            rec["input_amounts"] = parse_amount_array(raw_in_amt)
            rec["output_amounts"] = parse_amount_array(raw_out_amt)

            # Preserve any remaining columns
            for k, v in r_dict.items():
                if k not in rec:
                    rec[k] = v

            records.append(rec)
        return records


    def parse_json(self, file_path: Path) -> List[Dict[str, Any]]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        return []

    def parse_xml(self, file_path: Path) -> List[Dict[str, Any]]:
        tree = ET.parse(file_path)
        root = tree.getroot()
        records = []
        for rec_el in root.findall("record"):
            ts = rec_el.findtext("timestamp")
            
            # Network
            net_el = rec_el.find("network")
            src_ip = net_el.findtext("src_ip") if net_el is not None else ""
            dst_ip = net_el.findtext("dst_ip") if net_el is not None else ""
            src_port = int(net_el.findtext("src_port", "0")) if net_el is not None else 0
            dst_port = int(net_el.findtext("dst_port", "8333")) if net_el is not None else 8333
            geo_country = net_el.findtext("geo_country", "") if net_el is not None else ""
            asn = net_el.findtext("asn", "") if net_el is not None else ""
            
            # Blockchain
            bc_el = rec_el.find("blockchain")
            txid = bc_el.findtext("txid") if bc_el is not None else ""
            fee = float(bc_el.findtext("fee", "0.0")) if bc_el is not None else 0.0
            script_type = bc_el.findtext("script_type", "p2pkh") if bc_el is not None else "p2pkh"
            
            in_addrs, in_amts = [], []
            if bc_el is not None and bc_el.find("inputs") is not None:
                for inp in bc_el.find("inputs").findall("input"):
                    in_addrs.append(inp.get("address"))
                    in_amts.append(float(inp.get("amount", "0.0")))
                    
            out_addrs, out_amts = [], []
            if bc_el is not None and bc_el.find("outputs") is not None:
                for outp in bc_el.find("outputs").findall("output"):
                    out_addrs.append(outp.get("address"))
                    out_amts.append(float(outp.get("amount", "0.0")))
                    
            records.append({
                "timestamp": ts,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": src_port,
                "dst_port": dst_port,
                "geo_country": geo_country,
                "asn": asn,
                "txid": txid,
                "fee": fee,
                "script_type": script_type,
                "input_addresses": in_addrs,
                "input_amounts": in_amts,
                "output_addresses": out_addrs,
                "output_amounts": out_amts,
                "tag": rec_el.get("tag", "")
            })
        return records

    def ingest_file(self, file_path: Path) -> Dict[str, Any]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_format = self.detect_format(file_path)
        batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        # 1. Parse raw records
        if file_format == "CSV":
            raw_records = self.parse_csv(file_path)
        elif file_format == "JSON":
            raw_records = self.parse_json(file_path)
        elif file_format == "XML":
            raw_records = self.parse_xml(file_path)
        else:
            raw_records = []

        total_count = len(raw_records)
        valid_count = 0
        invalid_count = 0

        conn = self._get_conn()
        try:
            # Register batch
            conn.execute(
                """
                INSERT INTO ingestion_batches (batch_id, filename, file_format, total_records, status)
                VALUES (?, ?, ?, ?, 'PROCESSING')
                """,
                [batch_id, file_path.name, file_format, total_count]
            )

            for record_idx, rec in enumerate(raw_records, start=1):
                raw_payload_str = json.dumps(rec, default=str)
                val_result = validate_record(rec)
                val_status = "VALID" if val_result.is_valid else "INVALID"
                val_err = val_result.error_summary() if not val_result.is_valid else None

                # Store raw record verbatim
                conn.execute(
                    """
                    INSERT INTO raw_records (
                        source_file, source_format, source_record_number,
                        raw_payload, ingestion_batch_id, validation_status, validation_error
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [file_path.name, file_format, record_idx, raw_payload_str, batch_id, val_status, val_err]
                )
                raw_id = conn.execute("SELECT currval('seq_raw_records');").fetchone()[0]

                if not val_result.is_valid:
                    invalid_count += 1
                    continue

                valid_count += 1

                # Normalize valid record
                txid = rec["txid"].strip()
                _, _, ts_dt = validate_timestamp(rec["timestamp"])
                src_ip = rec["src_ip"].strip()
                dst_ip = rec.get("dst_ip", "0.0.0.0").strip()
                src_port = int(rec.get("src_port", 0))
                dst_port = int(rec.get("dst_port", 8333))
                fee = float(rec.get("fee", 0.0))
                script_type = rec.get("script_type", "p2pkh")
                geo_country = rec.get("geo_country", "") or ""
                asn = rec.get("asn", "") or ""

                # SIH26146 spec: Offline GeoIP resolution (Section iii)
                # Enriches geo_country and asn from src_ip whenever fields are
                # empty in the dataset (e.g., raw captures with no pre-labelling).
                if not geo_country or not asn:
                    resolved_country, resolved_asn = resolve_ip(src_ip)
                    if not geo_country:
                        geo_country = resolved_country
                    if not asn:
                        asn = resolved_asn

                in_addrs = rec["input_addresses"]
                in_amts = rec.get("input_amounts", [])
                out_addrs = rec["output_addresses"]
                out_amts = rec.get("output_amounts", [])

                total_in = sum(in_amts) if in_amts else 0.0
                total_out = sum(out_amts) if out_amts else 0.0

                # 1. Insert Transaction (deduplicated by txid)
                existing_tx = conn.execute("SELECT transaction_id FROM transactions WHERE txid = ?", [txid]).fetchone()
                if not existing_tx:
                    conn.execute(
                        """
                        INSERT INTO transactions (txid, timestamp, fee, total_input_amount, total_output_amount, script_type, source_record_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        [txid, ts_dt, fee, total_in, total_out, script_type, raw_id]
                    )

                    # 2. Insert Inputs
                    for i_idx, (addr, amt) in enumerate(zip(in_addrs, in_amts)):
                        conn.execute(
                            """
                            INSERT INTO transaction_inputs (txid, wallet_address, amount, input_index)
                            VALUES (?, ?, ?, ?)
                            """,
                            [txid, addr, amt, i_idx]
                        )
                        # Register Entity
                        conn.execute(
                            """
                            INSERT INTO entities (entity_type, entity_value, first_seen, last_seen)
                            VALUES ('WALLET', ?, ?, ?)
                            ON CONFLICT (entity_value) DO UPDATE SET last_seen = GREATEST(entities.last_seen, excluded.last_seen)
                            """,
                            [addr, ts_dt, ts_dt]
                        )

                    # 3. Insert Outputs
                    for o_idx, (addr, amt) in enumerate(zip(out_addrs, out_amts)):
                        conn.execute(
                            """
                            INSERT INTO transaction_outputs (txid, wallet_address, amount, output_index)
                            VALUES (?, ?, ?, ?)
                            """,
                            [txid, addr, amt, o_idx]
                        )
                        # Register Entity
                        conn.execute(
                            """
                            INSERT INTO entities (entity_type, entity_value, first_seen, last_seen)
                            VALUES ('WALLET', ?, ?, ?)
                            ON CONFLICT (entity_value) DO UPDATE SET last_seen = GREATEST(entities.last_seen, excluded.last_seen)
                            """,
                            [addr, ts_dt, ts_dt]
                        )

                    # Register TXID Entity
                    conn.execute(
                        """
                        INSERT INTO entities (entity_type, entity_value, first_seen, last_seen)
                        VALUES ('TXID', ?, ?, ?)
                        ON CONFLICT (entity_value) DO UPDATE SET last_seen = GREATEST(entities.last_seen, excluded.last_seen)
                        """,
                        [txid, ts_dt, ts_dt]
                    )

                # 4. Insert Network Observation
                conn.execute(
                    """
                    INSERT INTO network_observations (timestamp, src_ip, dst_ip, src_port, dst_port, txid, source_record_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [ts_dt, src_ip, dst_ip, src_port, dst_port, txid, raw_id]
                )

                # Register IP Entity & table
                conn.execute(
                    """
                    INSERT INTO ip_addresses (ip_address, country, asn, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (ip_address) DO UPDATE SET last_seen = GREATEST(ip_addresses.last_seen, excluded.last_seen)
                    """,
                    [src_ip, geo_country, asn, ts_dt, ts_dt]
                )
                conn.execute(
                    """
                    INSERT INTO entities (entity_type, entity_value, first_seen, last_seen)
                    VALUES ('IP', ?, ?, ?)
                    ON CONFLICT (entity_value) DO UPDATE SET last_seen = GREATEST(entities.last_seen, excluded.last_seen)
                    """,
                    [src_ip, ts_dt, ts_dt]
                )

            # Update batch completion
            conn.execute(
                """
                UPDATE ingestion_batches
                SET valid_records = ?, invalid_records = ?, status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP
                WHERE batch_id = ?
                """,
                [valid_count, invalid_count, batch_id]
            )

            return {
                "batch_id": batch_id,
                "filename": file_path.name,
                "file_format": file_format,
                "total_records": total_count,
                "valid_records": valid_count,
                "invalid_records": invalid_count,
                "status": "COMPLETED"
            }
        finally:
            if not self._external_conn:
                conn.close()
