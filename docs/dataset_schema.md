# SIH26146 Dataset Schema Specification

**Organization**: National Technical Research Organisation (NTRO)  
**Problem Statement**: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic  
**Dataset Source**: Synthetic benchmark modeled on real Bitcoin P2P and blockchain transactions (*Dataset Link: Nil per official PS*).

---

## 1. Network Layer Metadata
Observations recorded by network monitoring probes or peer listener nodes during transaction propagation.

| Field Name | Type | Format / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `timestamp` | ISO-8601 String / Epoch Float | `YYYY-MM-DDTHH:MM:SSZ` or epoch seconds | Time the transaction broadcast was observed at the network layer. |
| `src_ip` | String | Valid IPv4 or IPv6 address | IP address of the node propagating/broadcasting the transaction. |
| `dst_ip` | String | Valid IPv4 or IPv6 address | IP address of the receiving node / monitoring sensor. |
| `src_port` | Integer | `1 <= port <= 65535` | Source TCP port (e.g. 8333 default Bitcoin P2P or ephemeral port). |
| `dst_port` | Integer | `1 <= port <= 65535` | Destination TCP port (e.g. 8333). |
| `geo_country` | String (2-letter ISO) | e.g., `'US'`, `'IN'`, `'DE'`, `'CH'` | Originating country derived from local GeoIP database. |
| `asn` | String / Integer | e.g., `'AS15169'`, `'AS13335'` | Autonomous System Number for network infrastructure tracking. |

---

## 2. Blockchain Ledger Layer Metadata
Cryptographic ledger transaction parameters parsed from the Bitcoin payload.

| Field Name | Type | Format / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `txid` | Hex String | Exactly 64 hex characters `[0-9a-fA-F]{64}` | Unique double-SHA256 transaction hash. |
| `input_addresses` | Array / Delimited String | List of Bitcoin addresses (Base58 `1...`, `3...` or Bech32 `bc1...`) | Wallets funding the transaction (inputs). |
| `input_amounts` | Array / Delimited String | Float (BTC) or Int (Satoshis), `> 0` | Respective amounts debited from each input address. |
| `output_addresses` | Array / Delimited String | List of Bitcoin addresses | Wallets receiving funds (outputs). |
| `output_amounts` | Array / Delimited String | Float (BTC) or Int (Satoshis), `>= 0` | Respective amounts credited to each recipient address. |
| `fee` | Float / Integer | `>= 0` | Miner fee in BTC or Satoshis (`sum(inputs) - sum(outputs)`). |
| `script_type` | String | `p2pkh`, `p2sh`, `p2wpkh`, `p2wsh`, `multisig` | Script validation type utilized by the transaction. |

---

## 3. Data Representation Formats

### CSV Format (Delimited array fields)
```csv
timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,input_amounts,output_addresses,output_amounts,fee,script_type,geo_country,asn
2026-09-10T12:00:00Z,198.51.100.23,10.0.0.1,49210,8333,a1b2c3d4e5f6...,1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa;1Counterparty...,1.25;0.75,3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy;bc1qxy...,1.99;0.009,0.001,p2pkh,DE,AS24940
```

### JSON Format (Structured objects)
```json
{
  "timestamp": "2026-09-10T12:00:00Z",
  "src_ip": "198.51.100.23",
  "dst_ip": "10.0.0.1",
  "src_port": 49210,
  "dst_port": 8333,
  "txid": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
  "input_addresses": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
  "input_amounts": [2.00],
  "output_addresses": ["3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"],
  "output_amounts": [1.999],
  "fee": 0.001,
  "script_type": "p2pkh",
  "geo_country": "DE",
  "asn": "AS24940"
}
```

### XML Format (Standardized tree)
```xml
<transaction_record>
  <timestamp>2026-09-10T12:00:00Z</timestamp>
  <network>
    <src_ip>198.51.100.23</src_ip>
    <dst_ip>10.0.0.1</dst_ip>
    <src_port>49210</src_port>
    <dst_port>8333</dst_port>
    <geo_country>DE</geo_country>
    <asn>AS24940</asn>
  </network>
  <blockchain>
    <txid>a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2</txid>
    <script_type>p2pkh</script_type>
    <fee>0.001</fee>
    <inputs>
      <input address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa" amount="2.00" />
    </inputs>
    <outputs>
      <output address="3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy" amount="1.999" />
    </outputs>
  </blockchain>
</transaction_record>
```

---

## 4. Normalization Rules
1. **Raw Preservation**: The original file row/record is written verbatim to `raw_records` with an `ingestion_batch_id` and validation state.
2. **First-Class Relational Entities**:
   - `transactions` store 1 row per unique `txid`.
   - `transaction_inputs` store 1 row per input address per TXID with index.
   - `transaction_outputs` store 1 row per output address per TXID with index.
   - `network_observations` record each observed network propagation event linking `src_ip`, `dst_ip`, `port`, `timestamp`, and `txid`.
   - `wallets` and `ip_addresses` are maintained with lifetime aggregates (`first_seen`, `last_seen`, volumes).
