"""
backend/app/correlation/engine.py
SIH26146 - Correlation Engine
Correlates Network Layer Observations with Blockchain Ledger Records:
- IP <-> TXID (Broadcast observations)
- TXID <-> Wallet (Input debit & Output credit flows)
- Wallet <-> Wallet (Inferred counterparty transfer flows)
- IP <-> Wallet (Correlated network associations)
Updates wallet aggregate states and populates entity_relationships.
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple
from app.database.connection import DatabaseManager

class CorrelationEngine:
    def __init__(self, db_conn=None):
        self.db_mgr = DatabaseManager.get_instance()
        self._external_conn = db_conn

    def _get_conn(self):
        return self._external_conn if self._external_conn else self.db_mgr.get_connection()

    def run_correlation(self) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            print("[INFO] Starting metadata correlation...")

            # 1. Ensure entity mapping dictionary in memory for fast ID lookups
            entities_df = conn.execute("SELECT entity_id, entity_type, entity_value FROM entities;").fetchdf()
            entity_map = {row["entity_value"]: row["entity_id"] for _, row in entities_df.iterrows()}

            # 2. Correlate IP_TO_TXID
            # From network_observations: src_ip -> txid
            net_obs = conn.execute("""
                SELECT src_ip, txid, count(*) as obs_count, min(timestamp) as min_ts, max(timestamp) as max_ts
                FROM network_observations
                GROUP BY src_ip, txid
            """).fetchall()

            # 3. Correlate TXID_TO_WALLET (Inputs and Outputs)
            in_links = conn.execute("""
                SELECT t.txid, ti.wallet_address, count(*) as cnt, min(t.timestamp) as min_ts, max(t.timestamp) as max_ts
                FROM transactions t
                JOIN transaction_inputs ti ON t.txid = ti.txid
                GROUP BY t.txid, ti.wallet_address
            """).fetchall()

            out_links = conn.execute("""
                SELECT t.txid, to_tbl.wallet_address, count(*) as cnt, min(t.timestamp) as min_ts, max(t.timestamp) as max_ts
                FROM transactions t
                JOIN transaction_outputs to_tbl ON t.txid = to_tbl.txid
                GROUP BY t.txid, to_tbl.wallet_address
            """).fetchall()

            # 4. Correlate WALLET_TO_WALLET (Flow between inputs and outputs within same TXID)
            w2w_links = conn.execute("""
                SELECT ti.wallet_address as src_wallet, to_tbl.wallet_address as dst_wallet,
                       count(DISTINCT t.txid) as tx_cnt, sum(to_tbl.amount) as total_flow,
                       min(t.timestamp) as min_ts, max(t.timestamp) as max_ts
                FROM transactions t
                JOIN transaction_inputs ti ON t.txid = ti.txid
                JOIN transaction_outputs to_tbl ON t.txid = to_tbl.txid
                WHERE ti.wallet_address != to_tbl.wallet_address
                GROUP BY ti.wallet_address, to_tbl.wallet_address
            """).fetchall()

            # 5. Correlate IP_TO_WALLET (Correlated network association through observed broadcast)
            ip2w_links = conn.execute("""
                SELECT no.src_ip, ti.wallet_address,
                       count(DISTINCT no.txid) as tx_cnt, min(no.timestamp) as min_ts, max(no.timestamp) as max_ts
                FROM network_observations no
                JOIN transaction_inputs ti ON no.txid = ti.txid
                GROUP BY no.src_ip, ti.wallet_address
            """).fetchall()

            # Clear previous relationships to avoid duplicates during re-correlation
            conn.execute("DELETE FROM entity_relationships;")

            inserted_rels = 0

            # Insert IP_TO_TXID
            for src_ip, txid, cnt, min_ts, max_ts in net_obs:
                src_id = entity_map.get(src_ip)
                tgt_id = entity_map.get(txid)
                if src_id and tgt_id:
                    conn.execute("""
                        INSERT INTO entity_relationships (source_entity_id, target_entity_id, relationship_type, weight, transaction_count, first_seen, last_seen)
                        VALUES (?, ?, 'IP_TO_TXID', ?, ?, ?, ?)
                    """, [src_id, tgt_id, float(cnt), int(cnt), min_ts, max_ts])
                    inserted_rels += 1

            # Insert TXID_TO_WALLET (Inputs and Outputs)
            for txid, w_addr, cnt, min_ts, max_ts in (in_links + out_links):
                src_id = entity_map.get(txid)
                tgt_id = entity_map.get(w_addr)
                if src_id and tgt_id:
                    conn.execute("""
                        INSERT INTO entity_relationships (source_entity_id, target_entity_id, relationship_type, weight, transaction_count, first_seen, last_seen)
                        VALUES (?, ?, 'TXID_TO_WALLET', ?, ?, ?, ?)
                    """, [src_id, tgt_id, 1.0, int(cnt), min_ts, max_ts])
                    inserted_rels += 1

            # Insert WALLET_TO_WALLET
            for src_w, dst_w, tx_cnt, total_flow, min_ts, max_ts in w2w_links:
                src_id = entity_map.get(src_w)
                tgt_id = entity_map.get(dst_w)
                if src_id and tgt_id:
                    conn.execute("""
                        INSERT INTO entity_relationships (source_entity_id, target_entity_id, relationship_type, weight, transaction_count, first_seen, last_seen)
                        VALUES (?, ?, 'WALLET_TO_WALLET', ?, ?, ?, ?)
                    """, [src_id, tgt_id, float(total_flow or 1.0), int(tx_cnt), min_ts, max_ts])
                    inserted_rels += 1

            # Insert IP_TO_WALLET
            for src_ip, w_addr, tx_cnt, min_ts, max_ts in ip2w_links:
                src_id = entity_map.get(src_ip)
                tgt_id = entity_map.get(w_addr)
                if src_id and tgt_id:
                    conn.execute("""
                        INSERT INTO entity_relationships (source_entity_id, target_entity_id, relationship_type, weight, transaction_count, first_seen, last_seen)
                        VALUES (?, ?, 'IP_TO_WALLET', ?, ?, ?, ?)
                    """, [src_id, tgt_id, float(tx_cnt), int(tx_cnt), min_ts, max_ts])
                    inserted_rels += 1

            # 6. Update Wallets Aggregate Table
            conn.execute("""
                DELETE FROM wallets;
                INSERT INTO wallets (
                    wallet_address, first_seen, last_seen, total_transactions,
                    total_inbound_amount, total_outbound_amount,
                    unique_counterparties, unique_ips, unique_countries, unique_asns
                )
                SELECT 
                    w.wallet_address,
                    w.first_seen,
                    w.last_seen,
                    COALESCE(tx_counts.cnt, 0) as total_transactions,
                    COALESCE(in_sum.val, 0.0) as total_inbound_amount,
                    COALESCE(out_sum.val, 0.0) as total_outbound_amount,
                    COALESCE(cp.cnt, 0) as unique_counterparties,
                    COALESCE(ips.cnt, 0) as unique_ips,
                    COALESCE(geo.cnt, 0) as unique_countries,
                    COALESCE(asns.cnt, 0) as unique_asns
                FROM (
                    SELECT entity_value as wallet_address, first_seen, last_seen
                    FROM entities WHERE entity_type = 'WALLET'
                ) w
                LEFT JOIN (
                    SELECT wallet_address, count(DISTINCT txid) as cnt
                    FROM (
                        SELECT wallet_address, txid FROM transaction_inputs
                        UNION
                        SELECT wallet_address, txid FROM transaction_outputs
                    )
                    GROUP BY wallet_address
                ) tx_counts ON w.wallet_address = tx_counts.wallet_address
                LEFT JOIN (
                    SELECT wallet_address, sum(amount) as val
                    FROM transaction_outputs GROUP BY wallet_address
                ) in_sum ON w.wallet_address = in_sum.wallet_address
                LEFT JOIN (
                    SELECT wallet_address, sum(amount) as val
                    FROM transaction_inputs GROUP BY wallet_address
                ) out_sum ON w.wallet_address = out_sum.wallet_address
                LEFT JOIN (
                    SELECT src_wallet as wallet_address, count(DISTINCT dst_wallet) as cnt
                    FROM (
                        SELECT ti.wallet_address as src_wallet, to_tbl.wallet_address as dst_wallet
                        FROM transaction_inputs ti
                        JOIN transaction_outputs to_tbl ON ti.txid = to_tbl.txid
                        WHERE ti.wallet_address != to_tbl.wallet_address
                    ) GROUP BY src_wallet
                ) cp ON w.wallet_address = cp.wallet_address
                LEFT JOIN (
                    SELECT ti.wallet_address, count(DISTINCT no.src_ip) as cnt
                    FROM transaction_inputs ti
                    JOIN network_observations no ON ti.txid = no.txid
                    GROUP BY ti.wallet_address
                ) ips ON w.wallet_address = ips.wallet_address
                LEFT JOIN (
                    SELECT ti.wallet_address, count(DISTINCT ip.country) as cnt
                    FROM transaction_inputs ti
                    JOIN network_observations no ON ti.txid = no.txid
                    JOIN ip_addresses ip ON no.src_ip = ip.ip_address
                    WHERE ip.country != ''
                    GROUP BY ti.wallet_address
                ) geo ON w.wallet_address = geo.wallet_address
                LEFT JOIN (
                    SELECT ti.wallet_address, count(DISTINCT ip.asn) as cnt
                    FROM transaction_inputs ti
                    JOIN network_observations no ON ti.txid = no.txid
                    JOIN ip_addresses ip ON no.src_ip = ip.ip_address
                    WHERE ip.asn != ''
                    GROUP BY ti.wallet_address
                ) asns ON w.wallet_address = asns.wallet_address;
            """)

            wallets_cnt = conn.execute("SELECT count(*) FROM wallets;").fetchone()[0]

            # 7. Run Peeling-Chain and Mixing Pattern Detection
            peeling_chains = self.detect_peeling_chains(conn)
            mixing_rounds = self.detect_mixing_patterns(conn)

            print(f"[SUCCESS] Correlation complete: {inserted_rels} entity relationships created across {wallets_cnt} wallets.")
            return {
                "relationships_created": inserted_rels,
                "wallets_updated": wallets_cnt,
                "peeling_chains_detected": len(peeling_chains),
                "mixing_rounds_detected": len(mixing_rounds)
            }
        finally:
            if not self._external_conn:
                conn.close()

    def detect_peeling_chains(self, conn) -> List[Dict[str, Any]]:
        """
        Detects Bitcoin Peeling Chains:
        A characteristic laundering topology where an address repeatedly spends funds
        through transactions with 1 input and 2 outputs (1 small 'peeled' payment +
        1 large change output), creating a long linear peeling sequence.
        """
        try:
            # Query candidate transactions: exactly 1 distinct input and 2 distinct outputs
            cand_txs = conn.execute("""
                SELECT t.txid, t.timestamp,
                       (SELECT wallet_address FROM transaction_inputs WHERE txid = t.txid LIMIT 1) as input_wallet,
                       (SELECT count(*) FROM transaction_inputs WHERE txid = t.txid) as in_cnt,
                       (SELECT count(*) FROM transaction_outputs WHERE txid = t.txid) as out_cnt
                FROM transactions t
                WHERE in_cnt = 1 AND out_cnt = 2
                ORDER BY t.timestamp ASC;
            """).fetchall()

            if not cand_txs:
                return []

            # Inspect amounts to check for classic peeling structure (1 large change + 1 smaller payment)
            peeling_matches = []
            for txid, ts, in_wallet, _, _ in cand_txs:
                outputs = conn.execute("""
                    SELECT wallet_address, amount FROM transaction_outputs WHERE txid = ? ORDER BY amount ASC;
                """, [txid]).fetchall()
                if len(outputs) == 2:
                    small_out, large_out = outputs[0], outputs[1]
                    # Check ratio: large output is at least 3x the small peeled amount
                    if large_out[1] >= 2.5 * small_out[1] and small_out[1] > 0:
                        peeling_matches.append({
                            "txid": txid,
                            "timestamp": str(ts),
                            "input_wallet": in_wallet,
                            "peeled_recipient": small_out[0],
                            "peeled_amount": float(small_out[1]),
                            "change_wallet": large_out[0],
                            "change_amount": float(large_out[1]),
                            "pattern": "PEELING_CHAIN"
                        })

            print(f"[PATTERN] Peeling-Chain Detector: Identified {len(peeling_matches)} peeling sequence steps.")
            return peeling_matches
        except Exception as e:
            print(f"[WARN] Peeling chain detection error: {e}")
            return []

    def detect_mixing_patterns(self, conn) -> List[Dict[str, Any]]:
        """
        Detects CoinJoin and Tumbler/Mixing Patterns:
        Identifies collaborative transactions with multiple inputs (>= 3)
        and multiple outputs of identical or nearly-identical standard denominations,
        a definitive signature of Wasabi / Whirlpool / JoinMarket mixing rounds.
        """
        try:
            # Find transactions with >= 3 inputs and >= 3 outputs
            mix_cands = conn.execute("""
                SELECT t.txid, t.timestamp,
                       (SELECT count(*) FROM transaction_inputs WHERE txid = t.txid) as in_cnt,
                       (SELECT count(*) FROM transaction_outputs WHERE txid = t.txid) as out_cnt
                FROM transactions t
                WHERE in_cnt >= 2 AND out_cnt >= 2;
            """).fetchall()

            mixing_rounds = []
            for txid, ts, in_cnt, out_cnt in mix_cands:
                amounts = conn.execute("""
                    SELECT round(amount, 4) as rounded_amt, count(*) as freq
                    FROM transaction_outputs
                    WHERE txid = ?
                    GROUP BY rounded_amt
                    HAVING freq >= 2;
                """, [txid]).fetchall()

                if amounts:
                    # Found repeated output denominations
                    denom, freq = amounts[0]
                    mixing_rounds.append({
                        "txid": txid,
                        "timestamp": str(ts),
                        "input_count": in_cnt,
                        "output_count": out_cnt,
                        "equal_denomination": float(denom),
                        "participant_count": freq,
                        "pattern": "COINJOIN_MIXING_ROUND"
                    })

            print(f"[PATTERN] Mixing Detector: Identified {len(mixing_rounds)} CoinJoin/tumbler mixing rounds.")
            return mixing_rounds
        except Exception as e:
            print(f"[WARN] Mixing detection error: {e}")
            return []
