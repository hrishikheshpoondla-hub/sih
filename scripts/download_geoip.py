"""
scripts/download_geoip.py
SIH26146 - GeoLite2 Database Downloader
Downloads free MaxMind GeoLite2 MMDB files for offline Geo IP resolution.
Requires a free MaxMind account license key (set as env var MAXMIND_LICENSE_KEY).
Alternatively downloads DB-IP Lite MMDB (no signup, CC BY 4.0).
"""

import os
import sys
import gzip
import shutil
import urllib.request
from pathlib import Path

GEOIP_DIR = Path(__file__).resolve().parent.parent / "data" / "geoip"
GEOIP_DIR.mkdir(parents=True, exist_ok=True)

LICENSE_KEY = os.environ.get("MAXMIND_LICENSE_KEY", "")

MAXMIND_URLS = {
    "city.mmdb": f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={LICENSE_KEY}&suffix=tar.gz",
    "asn.mmdb":  f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-ASN&license_key={LICENSE_KEY}&suffix=tar.gz",
}

DBIP_URLS = {
    "city.mmdb": "https://download.db-ip.com/free/dbip-city-lite-2026-09.mmdb.gz",
    "asn.mmdb":  "https://download.db-ip.com/free/dbip-asn-lite-2026-09.mmdb.gz",
}

def download_with_progress(url: str, dest: Path):
    headers = {"User-Agent": "SIH26146-GeoIP-Downloader/1.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            while chunk := resp.read(65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  {pct}% ({downloaded // 1024} KB / {total // 1024} KB)", end="", flush=True)
        print()

def try_dbip(fname: str, dest: Path):
    url = DBIP_URLS[fname]
    gz_path = dest.with_suffix(".mmdb.gz")
    print(f"  Downloading DB-IP Lite: {url}")
    download_with_progress(url, gz_path)
    with gzip.open(gz_path, "rb") as f_in, open(dest, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    gz_path.unlink()
    print(f"  Saved: {dest} ({dest.stat().st_size // 1024} KB)")

def try_maxmind(fname: str, dest: Path):
    import tarfile
    url = MAXMIND_URLS[fname]
    tar_path = dest.with_suffix(".tar.gz")
    print(f"  Downloading MaxMind GeoLite2: {url}")
    download_with_progress(url, tar_path)
    with tarfile.open(tar_path) as tar:
        for member in tar.getmembers():
            if member.name.endswith(".mmdb"):
                with tar.extractfile(member) as f_in, open(dest, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
                break
    tar_path.unlink()
    print(f"  Saved: {dest} ({dest.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    print("=== SIH26146 GeoLite2 MMDB Downloader ===\n")
    for fname, dest in [("city.mmdb", GEOIP_DIR / "city.mmdb"), ("asn.mmdb", GEOIP_DIR / "asn.mmdb")]:
        if dest.exists():
            print(f"[SKIP] {fname} already exists ({dest.stat().st_size // 1024} KB)")
            continue
        print(f"[{fname}]")
        if LICENSE_KEY:
            try:
                try_maxmind(fname, dest)
                continue
            except Exception as e:
                print(f"  MaxMind failed: {e}")
        try:
            try_dbip(fname, dest)
        except Exception as e:
            print(f"  DB-IP failed: {e}")
            print(f"  Manual download: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data")
    print("\nDone. Place any GeoLite2-City.mmdb or GeoLite2-ASN.mmdb in:", GEOIP_DIR)
