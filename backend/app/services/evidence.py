"""
backend/app/services/evidence.py
SIH26146 - Deterministic Evidence Engine
Computes population baselines and feature deviation ratios for flagged entities.
Generates granular, explainable evidence records without fabrication.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
from app.database.connection import DatabaseManager

class EvidenceEngine:
    def __init__(self, db_conn=None):
        self.db_mgr = DatabaseManager.get_instance()
        self._external_conn = db_conn

    def _get_conn(self):
        return self._external_conn if self._external_conn else self.db_mgr.get_connection()

    def get_population_baselines(self) -> Dict[str, float]:
        """Calculates median baseline for all behavioral features across the entity population."""
        conn = self._get_conn()
        try:
            df = conn.execute("""
                SELECT transaction_count, transaction_frequency, transaction_volume,
                       average_transaction_amount, unique_counterparties, unique_ips,
                       burst_frequency, graph_degree, graph_centrality
                FROM entity_features;
            """).fetchdf()

            if df.empty:
                return {}

            baselines = {}
            for col in df.columns:
                # Use median as a robust non-parametric population baseline
                med_val = float(df[col].median())
                baselines[col] = max(0.001, med_val) # Avoid divide by zero
            return baselines
        finally:
            if not self._external_conn:
                conn.close()

    def generate_evidence_for_entity(self, entity_id: int, alert_id: str, baselines: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generates factual, mathematical evidence items for an alerted entity."""
        conn = self._get_conn()
        try:
            feat_row = conn.execute("""
                SELECT ef.*, e.entity_value
                FROM entity_features ef
                JOIN entities e ON ef.entity_id = e.entity_id
                WHERE ef.entity_id = ?;
            """, [entity_id]).fetchone()

            if not feat_row:
                return []

            # Column names from schema
            cols = [
                "feature_id", "entity_id", "calculated_at", "transaction_count", "transaction_frequency",
                "transaction_volume", "average_transaction_amount", "transaction_amount_variance",
                "unique_counterparties", "unique_ips", "unique_countries", "unique_asns",
                "inbound_volume", "outbound_volume", "inbound_outbound_ratio",
                "fee_average", "fee_variance", "burst_frequency",
                "graph_degree", "graph_weighted_degree", "graph_centrality", "cluster_size", "entity_value"
            ]
            f_dict = dict(zip(cols, feat_row))
            evidence_items = []

            # 1. Transaction Burst Evidence
            burst_val = float(f_dict.get("burst_frequency", 1.0))
            burst_base = baselines.get("burst_frequency", 1.0)
            burst_ratio = burst_val / burst_base
            if burst_ratio >= 1.5 or burst_val >= 5:
                evidence_items.append({
                    "alert_id": alert_id,
                    "feature_name": "burst_frequency",
                    "feature_value": burst_val,
                    "baseline_value": round(burst_base, 2),
                    "deviation_ratio": round(burst_ratio, 2),
                    "evidence_description": f"Short-duration transaction burst of {int(burst_val)} transactions within a 15-minute window ({burst_ratio:.1f}x population median)."
                })

            # 2. Transaction Frequency Evidence
            freq_val = float(f_dict.get("transaction_frequency", 0.0))
            freq_base = baselines.get("transaction_frequency", 1.0)
            freq_ratio = freq_val / freq_base
            if freq_ratio >= 2.0 or freq_val >= 10:
                evidence_items.append({
                    "alert_id": alert_id,
                    "feature_name": "transaction_frequency",
                    "feature_value": freq_val,
                    "baseline_value": round(freq_base, 2),
                    "deviation_ratio": round(freq_ratio, 2),
                    "evidence_description": f"Elevated velocity of {freq_val:.1f} transactions/hour compared to baseline median of {freq_base:.1f} tx/hr ({freq_ratio:.1f}x deviation)."
                })

            # 3. Associated IPs Evidence
            ips_val = float(f_dict.get("unique_ips", 0))
            ips_base = baselines.get("unique_ips", 1.0)
            ips_ratio = ips_val / ips_base
            if ips_ratio >= 2.0 or ips_val >= 4:
                evidence_items.append({
                    "alert_id": alert_id,
                    "feature_name": "unique_ips",
                    "feature_value": ips_val,
                    "baseline_value": round(ips_base, 2),
                    "deviation_ratio": round(ips_ratio, 2),
                    "evidence_description": f"Correlated with {int(ips_val)} distinct source IP addresses across multiple network Autonomous Systems ({ips_ratio:.1f}x baseline)."
                })

            # 4. Counterparty Pool Evidence
            cp_val = float(f_dict.get("unique_counterparties", 0))
            cp_base = baselines.get("unique_counterparties", 1.0)
            cp_ratio = cp_val / cp_base
            if cp_ratio >= 2.0 or cp_val >= 8:
                evidence_items.append({
                    "alert_id": alert_id,
                    "feature_name": "unique_counterparties",
                    "feature_value": cp_val,
                    "baseline_value": round(cp_base, 2),
                    "deviation_ratio": round(cp_ratio, 2),
                    "evidence_description": f"Interacted with {int(cp_val)} distinct counterparty wallets ({cp_ratio:.1f}x above baseline median of {cp_base:.1f})."
                })

            # 5. Graph Degree / Topology Evidence
            deg_val = float(f_dict.get("graph_degree", 0))
            deg_base = baselines.get("graph_degree", 1.0)
            deg_ratio = deg_val / deg_base
            if deg_ratio >= 1.5 or deg_val >= 6:
                evidence_items.append({
                    "alert_id": alert_id,
                    "feature_name": "graph_degree",
                    "feature_value": deg_val,
                    "baseline_value": round(deg_base, 2),
                    "deviation_ratio": round(deg_ratio, 2),
                    "evidence_description": f"High graph connectivity degree of {int(deg_val)} links across the transaction topology."
                })

            # 6. Transaction Volume Evidence
            vol_val = float(f_dict.get("transaction_volume", 0.0))
            vol_base = baselines.get("transaction_volume", 1.0)
            vol_ratio = vol_val / vol_base
            if vol_ratio >= 2.5:
                evidence_items.append({
                    "alert_id": alert_id,
                    "feature_name": "transaction_volume",
                    "feature_value": vol_val,
                    "baseline_value": round(vol_base, 2),
                    "deviation_ratio": round(vol_ratio, 2),
                    "evidence_description": f"High total transaction throughput of {vol_val:.2f} BTC ({vol_ratio:.1f}x baseline median)."
                })

            return evidence_items
        finally:
            if not self._external_conn:
                conn.close()
