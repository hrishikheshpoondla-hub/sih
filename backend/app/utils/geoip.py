"""
backend/app/utils/geoip.py
SIH26146 - Offline GeoIP and ASN Resolver
Complies with SIH26146 spec Section iii:
  "integrate open source downloadable Geo IP database"

Resolution Strategy (cascading, never crashes):
  1. MaxMind GeoLite2 / DB-IP MMDB files (data/geoip/city.mmdb + asn.mmdb)
  2. Built-in offline IP-range-to-country table (IANA/RIR public data)
  3. Private/Reserved RFC 1918 detection
  4. Returns ("", "") on unknown IPs
"""

import ipaddress
import os
from pathlib import Path
from typing import Tuple, Optional
from functools import lru_cache

# MMDB search paths
_GEOIP_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "geoip"
_CITY_DB_CANDIDATES = [
    _GEOIP_DIR / "city.mmdb",
    _GEOIP_DIR / "GeoLite2-City.mmdb",
    _GEOIP_DIR / "dbip-city.mmdb",
]
_ASN_DB_CANDIDATES = [
    _GEOIP_DIR / "asn.mmdb",
    _GEOIP_DIR / "GeoLite2-ASN.mmdb",
    _GEOIP_DIR / "dbip-asn.mmdb",
]

# Built-in fallback: IANA/RIR major allocations (public domain data)
_BUILTIN_RANGES = [
    ("1.0.0.0/8",    "AU", "APNIC-AU"),
    ("2.0.0.0/8",    "EU", "RIPE-NCC"),
    ("5.0.0.0/8",    "EU", "RIPE-NCC"),
    ("8.8.8.0/24",   "US", "AS15169-GOOGLE"),
    ("1.1.1.0/24",   "AU", "AS13335-CLOUDFLARE"),
    ("10.0.0.0/8",   "--", "PRIVATE-RFC1918"),
    ("14.0.0.0/8",   "IN", "APNIC-IN"),
    ("27.0.0.0/8",   "CN", "APNIC-CN"),
    ("31.0.0.0/8",   "EU", "RIPE-NCC"),
    ("36.0.0.0/8",   "CN", "APNIC-CN"),
    ("37.0.0.0/8",   "EU", "RIPE-NCC"),
    ("41.0.0.0/8",   "AF", "AFRINIC"),
    ("42.0.0.0/8",   "CN", "APNIC-CN"),
    ("43.0.0.0/8",   "JP", "APNIC-JP"),
    ("45.0.0.0/8",   "US", "ARIN"),
    ("46.0.0.0/8",   "EU", "RIPE-NCC"),
    ("49.0.0.0/8",   "IN", "APNIC-IN"),
    ("54.0.0.0/8",   "US", "AS16509-AMAZON-AWS"),
    ("58.0.0.0/8",   "CN", "APNIC-CN"),
    ("59.0.0.0/8",   "CN", "APNIC-CN"),
    ("60.0.0.0/8",   "CN", "APNIC-CN"),
    ("61.0.0.0/8",   "CN", "APNIC-CN"),
    ("62.0.0.0/8",   "EU", "RIPE-NCC"),
    ("64.0.0.0/8",   "US", "ARIN"),
    ("65.0.0.0/8",   "US", "ARIN"),
    ("66.0.0.0/8",   "US", "ARIN"),
    ("67.0.0.0/8",   "US", "ARIN"),
    ("68.0.0.0/8",   "US", "ARIN"),
    ("69.0.0.0/8",   "US", "ARIN"),
    ("70.0.0.0/8",   "US", "ARIN"),
    ("71.0.0.0/8",   "US", "ARIN"),
    ("72.0.0.0/8",   "US", "ARIN"),
    ("74.0.0.0/8",   "US", "ARIN"),
    ("78.0.0.0/8",   "EU", "RIPE-NCC"),
    ("79.0.0.0/8",   "EU", "RIPE-NCC"),
    ("80.0.0.0/8",   "EU", "RIPE-NCC"),
    ("81.0.0.0/8",   "EU", "RIPE-NCC"),
    ("82.0.0.0/8",   "EU", "RIPE-NCC"),
    ("83.0.0.0/8",   "EU", "RIPE-NCC"),
    ("84.0.0.0/8",   "EU", "RIPE-NCC"),
    ("85.0.0.0/8",   "EU", "RIPE-NCC"),
    ("86.0.0.0/8",   "EU", "RIPE-NCC"),
    ("87.0.0.0/8",   "EU", "RIPE-NCC"),
    ("88.0.0.0/8",   "EU", "RIPE-NCC"),
    ("89.0.0.0/8",   "EU", "RIPE-NCC"),
    ("90.0.0.0/8",   "EU", "RIPE-NCC"),
    ("91.0.0.0/8",   "RU", "RIPE-RU"),
    ("92.0.0.0/8",   "EU", "RIPE-NCC"),
    ("93.0.0.0/8",   "EU", "RIPE-NCC"),
    ("94.0.0.0/8",   "EU", "RIPE-NCC"),
    ("95.0.0.0/8",   "EU", "RIPE-NCC"),
    ("96.0.0.0/8",   "US", "ARIN"),
    ("97.0.0.0/8",   "US", "ARIN"),
    ("98.0.0.0/8",   "US", "ARIN"),
    ("99.0.0.0/8",   "US", "ARIN"),
    ("100.0.0.0/8",  "US", "ARIN"),
    ("101.0.0.0/8",  "CN", "APNIC-CN"),
    ("103.0.0.0/8",  "IN", "APNIC-IN"),
    ("104.0.0.0/8",  "US", "AS13335-CLOUDFLARE"),
    ("106.0.0.0/8",  "CN", "APNIC-CN"),
    ("110.0.0.0/8",  "CN", "APNIC-CN"),
    ("111.0.0.0/8",  "CN", "APNIC-CN"),
    ("112.0.0.0/8",  "CN", "APNIC-CN"),
    ("113.0.0.0/8",  "CN", "APNIC-CN"),
    ("114.0.0.0/8",  "CN", "APNIC-CN"),
    ("115.0.0.0/8",  "CN", "APNIC-CN"),
    ("116.0.0.0/8",  "CN", "APNIC-CN"),
    ("117.0.0.0/8",  "CN", "APNIC-CN"),
    ("118.0.0.0/8",  "CN", "APNIC-CN"),
    ("119.0.0.0/8",  "CN", "APNIC-CN"),
    ("120.0.0.0/8",  "CN", "APNIC-CN"),
    ("121.0.0.0/8",  "CN", "APNIC-CN"),
    ("122.0.0.0/8",  "CN", "APNIC-CN"),
    ("123.0.0.0/8",  "CN", "APNIC-CN"),
    ("124.0.0.0/8",  "CN", "APNIC-CN"),
    ("125.0.0.0/8",  "CN", "APNIC-CN"),
    ("126.0.0.0/8",  "JP", "APNIC-JP"),
    ("139.0.0.0/8",  "US", "ARIN"),
    ("140.0.0.0/8",  "US", "ARIN"),
    ("141.0.0.0/8",  "EU", "RIPE-NCC"),
    ("143.0.0.0/8",  "BR", "LACNIC-BR"),
    ("144.0.0.0/8",  "US", "ARIN"),
    ("146.0.0.0/8",  "US", "ARIN"),
    ("147.0.0.0/8",  "US", "ARIN"),
    ("148.0.0.0/8",  "MX", "LACNIC-MX"),
    ("149.0.0.0/8",  "US", "ARIN"),
    ("150.0.0.0/8",  "BR", "LACNIC-BR"),
    ("151.0.0.0/8",  "EU", "RIPE-NCC"),
    ("154.0.0.0/8",  "AF", "AFRINIC"),
    ("156.0.0.0/8",  "CN", "APNIC-CN"),
    ("157.0.0.0/8",  "US", "ARIN"),
    ("162.0.0.0/8",  "US", "ARIN"),
    ("163.0.0.0/8",  "TW", "APNIC-TW"),
    ("165.0.0.0/8",  "US", "ARIN"),
    ("168.0.0.0/8",  "US", "ARIN"),
    ("171.0.0.0/8",  "CN", "APNIC-CN"),
    ("172.16.0.0/12","--", "PRIVATE-RFC1918"),
    ("173.0.0.0/8",  "US", "ARIN"),
    ("175.0.0.0/8",  "CN", "APNIC-CN"),
    ("176.0.0.0/8",  "EU", "RIPE-NCC"),
    ("177.0.0.0/8",  "BR", "LACNIC-BR"),
    ("178.0.0.0/8",  "EU", "RIPE-NCC"),
    ("179.0.0.0/8",  "BR", "LACNIC-BR"),
    ("180.0.0.0/8",  "CN", "APNIC-CN"),
    ("182.0.0.0/8",  "CN", "APNIC-CN"),
    ("183.0.0.0/8",  "CN", "APNIC-CN"),
    ("185.0.0.0/8",  "EU", "RIPE-NCC"),
    ("186.0.0.0/8",  "BR", "LACNIC-BR"),
    ("187.0.0.0/8",  "BR", "LACNIC-BR"),
    ("188.0.0.0/8",  "EU", "RIPE-NCC"),
    ("189.0.0.0/8",  "MX", "LACNIC-MX"),
    ("190.0.0.0/8",  "AR", "LACNIC-AR"),
    ("191.0.0.0/8",  "BR", "LACNIC-BR"),
    ("192.168.0.0/16","--","PRIVATE-RFC1918"),
    ("193.0.0.0/8",  "EU", "RIPE-NCC"),
    ("194.0.0.0/8",  "EU", "RIPE-NCC"),
    ("195.0.0.0/8",  "EU", "RIPE-NCC"),
    ("196.0.0.0/8",  "AF", "AFRINIC"),
    ("197.0.0.0/8",  "AF", "AFRINIC"),
    ("198.0.0.0/8",  "US", "ARIN"),
    ("199.0.0.0/8",  "US", "ARIN"),
    ("200.0.0.0/8",  "BR", "LACNIC-BR"),
    ("201.0.0.0/8",  "BR", "LACNIC-BR"),
    ("202.0.0.0/8",  "CN", "APNIC-CN"),
    ("203.0.0.0/8",  "IN", "APNIC-IN"),
    ("204.0.0.0/8",  "US", "ARIN"),
    ("205.0.0.0/8",  "US", "ARIN"),
    ("206.0.0.0/8",  "US", "ARIN"),
    ("207.0.0.0/8",  "US", "ARIN"),
    ("208.0.0.0/8",  "US", "ARIN"),
    ("209.0.0.0/8",  "US", "ARIN"),
    ("210.0.0.0/8",  "JP", "APNIC-JP"),
    ("211.0.0.0/8",  "CN", "APNIC-CN"),
    ("212.0.0.0/8",  "EU", "RIPE-NCC"),
    ("213.0.0.0/8",  "EU", "RIPE-NCC"),
    ("216.0.0.0/8",  "US", "ARIN"),
    ("217.0.0.0/8",  "EU", "RIPE-NCC"),
    ("218.0.0.0/8",  "CN", "APNIC-CN"),
    ("219.0.0.0/8",  "CN", "APNIC-CN"),
    ("220.0.0.0/8",  "CN", "APNIC-CN"),
    ("221.0.0.0/8",  "CN", "APNIC-CN"),
    ("222.0.0.0/8",  "CN", "APNIC-CN"),
    ("223.0.0.0/8",  "CN", "APNIC-CN"),
]

# Precompile at import time for O(n) lookup speed
_COMPILED_RANGES = [
    (ipaddress.ip_network(cidr, strict=False), cc, asn_lbl)
    for cidr, cc, asn_lbl in _BUILTIN_RANGES
]


class GeoIPResolver:
    """Offline GeoIP resolver with MMDB + built-in fallback."""
    _instance: Optional["GeoIPResolver"] = None

    def __init__(self):
        self._city_reader = None
        self._asn_reader = None
        self._mmdb_available = False
        self._load_mmdb()

    @classmethod
    def get_instance(cls) -> "GeoIPResolver":
        if cls._instance is None:
            cls._instance = GeoIPResolver()
        return cls._instance

    def _load_mmdb(self):
        try:
            import geoip2.database
            city_path = next((p for p in _CITY_DB_CANDIDATES if p.exists()), None)
            asn_path  = next((p for p in _ASN_DB_CANDIDATES  if p.exists()), None)
            if city_path:
                self._city_reader = geoip2.database.Reader(str(city_path))
                print(f"[GEOIP] City MMDB loaded: {city_path.name}")
            if asn_path:
                self._asn_reader = geoip2.database.Reader(str(asn_path))
                print(f"[GEOIP] ASN MMDB loaded: {asn_path.name}")
            self._mmdb_available = bool(city_path or asn_path)
            if not self._mmdb_available:
                print(f"[GEOIP] No MMDB found in {_GEOIP_DIR} — using built-in fallback table.")
                print("[GEOIP] Run: python scripts/download_geoip.py  to download GeoLite2 databases.")
        except ImportError:
            print("[GEOIP] geoip2 not installed — using built-in fallback table.")

    @lru_cache(maxsize=16384)
    def lookup(self, ip_str: str) -> Tuple[str, str]:
        """Returns (country_code, asn_label). Never raises."""
        if not ip_str or ip_str in ("0.0.0.0", "::", ""):
            return ("", "")
        try:
            ip_obj = ipaddress.ip_address(ip_str.strip())
        except ValueError:
            return ("", "")

        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local:
            return ("--", "PRIVATE")

        country, asn_label = "", ""

        # 1. Try MMDB City
        if self._city_reader:
            try:
                resp = self._city_reader.city(ip_str)
                country = resp.country.iso_code or ""
            except Exception:
                pass

        # 2. Try MMDB ASN
        if self._asn_reader:
            try:
                resp = self._asn_reader.asn(ip_str)
                if resp.autonomous_system_number:
                    asn_label = f"AS{resp.autonomous_system_number}-{resp.autonomous_system_organization}"
            except Exception:
                pass

        # 3. Fallback to built-in range table
        if not country or not asn_label:
            for network, cc, asn_lbl in _COMPILED_RANGES:
                if ip_obj in network:
                    country = country or cc
                    asn_label = asn_label or asn_lbl
                    break

        return (country or "", asn_label or "")


# Module-level singleton
_resolver: Optional[GeoIPResolver] = None


def resolve_ip(ip_str: str) -> Tuple[str, str]:
    """
    Convenience wrapper. Returns (country_code, asn_label).
    Thread-safe and cached via lru_cache.
    """
    global _resolver
    if _resolver is None:
        _resolver = GeoIPResolver.get_instance()
    return _resolver.lookup(ip_str)
