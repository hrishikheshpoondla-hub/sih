"""
backend/app/features/extractor.py
SIH26146 - Behavioral Feature Engineering Engine
Extracts 19 deterministic behavioral metrics per wallet entity:
1. transaction_count
2. transaction_frequency
3. transaction_volume
4. average_transaction_amount
5. transaction_amount_variance
6. unique_counterparties
7. unique_ips
8. unique_countries
9. unique_asns
10. inbound_volume
11. outbound_volume
12. inbound_outbound_ratio
13. fee_average
14. fee_variance
15. burst_frequency (max tx in 15-min window)
16. graph_degree
17. graph_weighted_degree
18. graph_centrality
19. cluster_size
Stores metrics deterministically in DuckDB `entity_features`.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from app.database.connection import DatabaseManager
from app.graph.network import EntityGraphManager

class FeatureExtractor:
    def __init__(self, db_conn=None):
        self.db_mgr = DatabaseManager.get_instance()
        self._external_conn = db_conn
        self.graph_mgr = EntityGraphManager(db_conn)

    def _get_conn(self):
        return self._external_conn if self._external_conn else self.db_mgr.get_connection()

    def extract_features(self) -> pd.DataFrame:
        """Extracts and persists entity behavioral features into `entity_features`."""
        conn = self._get_conn()
        try:
            print("[INFO] Loading entity graph topological metrics...")
            self.graph_mgr.load_graph()
            graph_metrics = self.graph_mgr.compute_graph_metrics()

            # Connected component cluster sizes
            undirected_G = self.graph_mgr.undirected_G
            comp_sizes = {}
            import networkx as nx
            for c in nx.connected_components(undirected_G):
                c_size = len(c)
                for node_id in c:
                    comp_sizes[node_id] = c_size

            # Get all wallet entities
            wallets_df = conn.execute("""
                SELECT e.entity_id, e.entity_value as wallet_address,
                       w.first_seen, w.last_seen,
                       COALESCE(w.total_transactions, 0) as total_transactions,
                       COALESCE(w.total_inbound_amount, 0.0) as total_inbound_amount,
                       COALESCE(w.total_outbound_amount, 0.0) as total_outbound_amount,
                       COALESCE(w.unique_counterparties, 0) as unique_counterparties,
                       COALESCE(w.unique_ips, 0) as unique_ips,
                       COALESCE(w.unique_countries, 0) as unique_countries,
                       COALESCE(w.unique_asns, 0) as unique_asns
                FROM entities e
                LEFT JOIN wallets w ON e.entity_value = w.wallet_address
                WHERE e.entity_type = 'WALLET';
            """).fetchdf()

            if wallets_df.empty:
                print("[WARN] No wallet entities found for feature extraction.")
                return pd.DataFrame()

            # Fetch transaction amounts and timestamps per wallet for variance & burst calculation
            tx_data_df = conn.execute("""
                SELECT ti.wallet_address, t.timestamp, ti.amount, t.fee
                FROM transaction_inputs ti
                JOIN transactions t ON ti.txid = t.txid
                UNION ALL
                SELECT to_tbl.wallet_address, t.timestamp, to_tbl.amount, t.fee
                FROM transaction_outputs to_tbl
                JOIN transactions t ON to_tbl.txid = t.txid
            """).fetchdf()

            tx_data_df["timestamp"] = pd.to_datetime(tx_data_df["timestamp"])

            # Group transaction history by wallet
            wallet_groups = tx_data_df.groupby("wallet_address")

            features_rows = []
            for _, row in wallets_df.iterrows():
                eid = int(row["entity_id"])
                w_addr = row["wallet_address"]
                tx_count = int(row["total_transactions"])
                in_vol = float(row["total_inbound_amount"])
                out_vol = float(row["total_outbound_amount"])
                total_vol = in_vol + out_vol

                # Timespan in hours
                fs = row["first_seen"]
                ls = row["last_seen"]
                hours_span = 1.0
                if pd.notnull(fs) and pd.notnull(ls):
                    delta = (pd.to_datetime(ls) - pd.to_datetime(fs)).total_seconds() / 3600.0
                    hours_span = max(0.25, delta) # Min 15 mins floor

                tx_frequency = round(float(tx_count / hours_span), 4)
                in_out_ratio = round(float(in_vol / (out_vol + 1e-6)), 4)

                # Amount & fee variance, burst frequency
                avg_tx_amt = 0.0
                tx_amt_var = 0.0
                fee_avg = 0.0
                fee_var = 0.0
                burst_freq = 1.0

                if w_addr in wallet_groups.groups:
                    w_txs = wallet_groups.get_group(w_addr).sort_values("timestamp")
                    amounts = w_txs["amount"].values
                    fees = w_txs["fee"].values

                    if len(amounts) > 0:
                        avg_tx_amt = float(np.mean(amounts))
                        tx_amt_var = float(np.var(amounts)) if len(amounts) > 1 else 0.0

                    if len(fees) > 0:
                        fee_avg = float(np.mean(fees))
                        fee_var = float(np.var(fees)) if len(fees) > 1 else 0.0

                    # 15-minute sliding window burst count
                    if len(w_txs) > 1:
                        w_times = w_txs["timestamp"]
                        rolling_counts = [
                            ((w_times >= t) & (w_times <= t + pd.Timedelta(minutes=15))).sum()
                            for t in w_times
                        ]
                        burst_freq = float(max(rolling_counts))
                    else:
                        burst_freq = float(len(w_txs))

                # Graph metrics
                g_metrics = graph_metrics.get(eid, {"degree": 0, "weighted_degree": 0.0, "centrality": 0.0})
                cluster_sz = comp_sizes.get(eid, 1)

                features_rows.append({
                    "entity_id": eid,
                    "transaction_count": tx_count,
                    "transaction_frequency": tx_frequency,
                    "transaction_volume": round(total_vol, 6),
                    "average_transaction_amount": round(avg_tx_amt, 6),
                    "transaction_amount_variance": round(tx_amt_var, 6),
                    "unique_counterparties": int(row["unique_counterparties"]),
                    "unique_ips": int(row["unique_ips"]),
                    "unique_countries": int(row["unique_countries"]),
                    "unique_asns": int(row["unique_asns"]),
                    "inbound_volume": round(in_vol, 6),
                    "outbound_volume": round(out_vol, 6),
                    "inbound_outbound_ratio": in_out_ratio,
                    "fee_average": round(fee_avg, 6),
                    "fee_variance": round(fee_var, 6),
                    "burst_frequency": burst_freq,
                    "graph_degree": int(g_metrics["degree"]),
                    "graph_weighted_degree": float(g_metrics["weighted_degree"]),
                    "graph_centrality": float(g_metrics["centrality"]),
                    "cluster_size": int(cluster_sz)
                })

            features_df = pd.DataFrame(features_rows)

            # Persist to DuckDB entity_features
            conn.execute("DELETE FROM entity_features;")
            for _, f in features_df.iterrows():
                conn.execute("""
                    INSERT INTO entity_features (
                        entity_id, transaction_count, transaction_frequency,
                        transaction_volume, average_transaction_amount, transaction_amount_variance,
                        unique_counterparties, unique_ips, unique_countries, unique_asns,
                        inbound_volume, outbound_volume, inbound_outbound_ratio,
                        fee_average, fee_variance, burst_frequency,
                        graph_degree, graph_weighted_degree, graph_centrality, cluster_size
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    int(f["entity_id"]), int(f["transaction_count"]), float(f["transaction_frequency"]),
                    float(f["transaction_volume"]), float(f["average_transaction_amount"]), float(f["transaction_amount_variance"]),
                    int(f["unique_counterparties"]), int(f["unique_ips"]), int(f["unique_countries"]), int(f["unique_asns"]),
                    float(f["inbound_volume"]), float(f["outbound_volume"]), float(f["inbound_outbound_ratio"]),
                    float(f["fee_average"]), float(f["fee_variance"]), float(f["burst_frequency"]),
                    int(f["graph_degree"]), float(f["graph_weighted_degree"]), float(f["graph_centrality"]), int(f["cluster_size"])
                ])

            print(f"[SUCCESS] Extracted and stored behavioral features for {len(features_df)} wallet entities.")
            return features_df
        finally:
            if not self._external_conn:
                conn.close()
