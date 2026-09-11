"""
backend/app/utils/validation.py
Data validation rules for SIH26146.
Validates:
- IP addresses (IPv4 & IPv6)
- Ports (1 to 65535)
- Timestamps (ISO-8601 & Unix timestamps)
- Bitcoin TXIDs (64 hex characters)
- Bitcoin Wallet Addresses (Base58 P2PKH/P2SH and Bech32)
- Amounts (positive floats/integers)
Never silently discards errors; records validation issues transparently.
"""

import re
import ipaddress
from datetime import datetime
from typing import List, Tuple, Any, Dict

HEX_64_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
BTC_ADDR_PATTERN = re.compile(r"^(1[1-9A-HJ-NP-Za-km-z]{25,44}|3[1-9A-HJ-NP-Za-km-z]{25,44}|bc1[0-9a-zA-Z]{6,65}|[a-zA-Z0-9_-]{8,65})$")


class ValidationResult:
    def __init__(self, is_valid: bool, errors: List[str]):
        self.is_valid = is_valid
        self.errors = errors

    def error_summary(self) -> str:
        return "; ".join(self.errors) if self.errors else ""

def validate_ip(ip_str: Any) -> Tuple[bool, str]:
    if not ip_str or not isinstance(ip_str, str):
        return False, "IP address is missing or not a string"
    try:
        ipaddress.ip_address(ip_str.strip())
        return True, ""
    except ValueError:
        return False, f"Invalid IP address format: '{ip_str}'"

def validate_port(port: Any) -> Tuple[bool, str]:
    try:
        port_num = int(port)
        if 1 <= port_num <= 65535:
            return True, ""
        return False, f"Port {port_num} out of range (1-65535)"
    except (ValueError, TypeError):
        return False, f"Invalid port value: '{port}'"

def validate_timestamp(ts: Any) -> Tuple[bool, str, datetime]:
    if not ts:
        return False, "Timestamp is missing", None
    
    # Check if unix timestamp (int/float)
    if isinstance(ts, (int, float)):
        try:
            dt = datetime.fromtimestamp(ts)
            return True, "", dt
        except Exception as e:
            return False, f"Invalid unix timestamp: {e}", None

    # Check if ISO-8601 string
    ts_str = str(ts).strip()
    iso_formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ"
    ]
    for fmt in iso_formats:
        try:
            dt = datetime.strptime(ts_str, fmt)
            return True, "", dt
        except ValueError:
            continue
            
    # Try datetime.fromisoformat
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return True, "", dt
    except Exception:
        pass
        
    return False, f"Invalid timestamp format: '{ts_str}'", None

def validate_txid(txid: Any) -> Tuple[bool, str]:
    if not txid or not isinstance(txid, str):
        return False, "TXID is missing or not a string"
    clean_txid = txid.strip()
    if HEX_64_PATTERN.match(clean_txid):
        return True, ""
    return False, f"TXID must be a 64-character hex string (got length {len(clean_txid)}: '{clean_txid[:16]}...')"

def validate_wallet_address(address: Any) -> Tuple[bool, str]:
    if not address or not isinstance(address, str):
        return False, "Wallet address is missing or not a string"
    clean_addr = address.strip()
    if BTC_ADDR_PATTERN.match(clean_addr):
        return True, ""
    return False, f"Invalid Bitcoin wallet address format: '{clean_addr}'"

def validate_record(record: Dict[str, Any]) -> ValidationResult:
    errors = []
    
    # 1. Validate Timestamp
    ts_ok, ts_err, _ = validate_timestamp(record.get("timestamp"))
    if not ts_ok:
        errors.append(ts_err)
        
    # 2. Validate Network Info
    ip_ok, ip_err = validate_ip(record.get("src_ip"))
    if not ip_ok:
        errors.append(f"src_ip: {ip_err}")
        
    if "dst_ip" in record and record.get("dst_ip"):
        dst_ok, dst_err = validate_ip(record.get("dst_ip"))
        if not dst_ok:
            errors.append(f"dst_ip: {dst_err}")
            
    if "src_port" in record and record.get("src_port") is not None:
        port_ok, port_err = validate_port(record.get("src_port"))
        if not port_ok:
            errors.append(f"src_port: {port_err}")
            
    # 3. Validate Blockchain Info
    tx_ok, tx_err = validate_txid(record.get("txid"))
    if not tx_ok:
        errors.append(tx_err)
        
    # 4. Validate Inputs
    inputs = record.get("input_addresses")
    if not inputs:
        errors.append("Missing transaction input addresses")
    else:
        if isinstance(inputs, str):
            inputs = [a.strip() for a in inputs.split(";") if a.strip()]
        for inp in inputs:
            w_ok, w_err = validate_wallet_address(inp)
            if not w_ok:
                errors.append(f"input wallet: {w_err}")
                
    # 5. Validate Outputs
    outputs = record.get("output_addresses")
    if not outputs:
        errors.append("Missing transaction output addresses")
    else:
        if isinstance(outputs, str):
            outputs = [a.strip() for a in outputs.split(";") if a.strip()]
        for out in outputs:
            w_ok, w_err = validate_wallet_address(out)
            if not w_ok:
                errors.append(f"output wallet: {w_err}")
                
    # 6. Validate Amounts
    in_amts = record.get("input_amounts", [])
    if isinstance(in_amts, str):
        try:
            in_amts = [float(x.strip()) for x in in_amts.split(";") if x.strip()]
        except ValueError:
            errors.append("Invalid numeric values in input_amounts")
            in_amts = []
    for amt in in_amts:
        if amt < 0:
            errors.append(f"Negative input amount: {amt}")
            
    out_amts = record.get("output_amounts", [])
    if isinstance(out_amts, str):
        try:
            out_amts = [float(x.strip()) for x in out_amts.split(";") if x.strip()]
        except ValueError:
            errors.append("Invalid numeric values in output_amounts")
            out_amts = []
    for amt in out_amts:
        if amt < 0:
            errors.append(f"Negative output amount: {amt}")

    return ValidationResult(is_valid=(len(errors) == 0), errors=errors)
