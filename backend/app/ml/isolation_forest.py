"""
backend/app/ml/isolation_forest.py
SIH26146 - Unsupervised Anomaly Detection & Clustering Engine
Uses:
- scikit-learn IsolationForest for detecting anomalous entity behavior
- scikit-learn DBSCAN for clustering structurally/behaviorally related entities
- Robust feature scaling and deterministic 0-100 normalized risk score mapping
- Transparent severity assignment: LOW, MEDIUM, HIGH, CRITICAL
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import RobustScaler

from app.database.connection import DatabaseManager
from app.features.extractor import FeatureExtractor

FEATURE_COLUMNS = [
    "transaction_count", "transaction_frequency", "transaction_volume",
    "average_transaction_amount", "transaction_amount_variance",
    "unique_counterparties", "unique_ips", "unique_countries", "unique_asns",
    "inbound_volume", "outbound_volume", "inbound_outbound_ratio",
    "fee_average", "fee_variance", "burst_frequency",
    "graph_degree", "graph_weighted_degree", "graph_centrality", "cluster_size"
]

class AnomalyDetectionPipeline:
    def __init__(self, contamination: float = 0.08, random_state: int = 42, db_conn=None):
        self.contamination = contamination
        self.random_state = random_state
        self.db_mgr = DatabaseManager.get_instance()
        self._external_conn = db_conn
        self.feature_extractor = FeatureExtractor(db_conn)
        self.scaler = RobustScaler()
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100
        )
        self.model_name = "IsolationForest"
        self.model_version = "1.0.0"

    def _get_conn(self):
        return self._external_conn if self._external_conn else self.db_mgr.get_connection()

    def run_pipeline(self) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            print("[INFO] Step 1: Extracting behavioral features...")
            features_df = self.feature_extractor.extract_features()
            if features_df.empty:
                return {"error": "No features found to train Isolation Forest"}

            X = features_df[FEATURE_COLUMNS].copy()
            # Replace NaNs/Infs with 0
            X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)

            print("[INFO] Step 2: Preprocessing features with RobustScaler...")
            X_scaled = self.scaler.fit_transform(X)

            print("[INFO] Step 3: Fitting Isolation Forest anomaly model...")
            self.model.fit(X_scaled)
            # IsolationForest score_samples: more negative = more abnormal
            raw_scores = self.model.score_samples(X_scaled)

            # Step 4: Deterministic 0-100 Risk Score Normalization
            # Invert so higher score = higher risk
            # raw_scores typically range from -0.8 (most anomalous) to -0.3 (normal)
            min_score = np.min(raw_scores)
            max_score = np.max(raw_scores)
            score_range = max_score - min_score if (max_score - min_score) > 1e-6 else 1.0

            normalized_risk = (max_score - raw_scores) / score_range * 100.0
            normalized_risk = np.clip(np.round(normalized_risk, 1), 0.0, 100.0)

            # Step 5: Entity Clustering (DBSCAN + Common-Input Heuristic)
            print("[INFO] Step 4: Clustering entities with DBSCAN & Common-Input Heuristic...")
            dbscan = DBSCAN(eps=1.8, min_samples=3)
            cluster_labels = dbscan.fit_predict(X_scaled)

            # Step 5b: Graph Risk Diffusion via Personalized PageRank
            print("[INFO] Step 5: Propagating risk scores from seed illicit entities across transaction graph...")
            from app.graph.network import EntityGraphManager
            graph_mgr = EntityGraphManager(conn)
            
            raw_risk_map = {int(features_df.iloc[i]["entity_id"]): float(normalized_risk[i]) for i in range(len(features_df))}
            diffused_risk_map = graph_mgr.propagate_risk_scores(raw_risk_map, alpha=0.85)

            # Common-Input clusters
            common_input_res = graph_mgr.compute_common_input_clusters()

            # Step 6: Assign Final Severity Levels from Blended & Propagated Scores
            final_risk_scores = []
            severities = []
            for i in range(len(features_df)):
                eid = int(features_df.iloc[i]["entity_id"])
                final_score = diffused_risk_map.get(eid, float(normalized_risk[i]))
                final_risk_scores.append(final_score)
                if final_score >= 85.0:
                    severities.append("CRITICAL")
                elif final_score >= 70.0:
                    severities.append("HIGH")
                elif final_score >= 45.0:
                    severities.append("MEDIUM")
                else:
                    severities.append("LOW")

            # Step 7: Persist results into DuckDB `anomaly_scores`
            print("[INFO] Step 6: Storing diffused anomaly scores into database...")
            conn.execute("DELETE FROM anomaly_scores;")

            stored_scores = []
            for idx, row in features_df.iterrows():
                eid = int(row["entity_id"])
                r_score = float(raw_scores[idx])
                n_risk = float(final_risk_scores[idx])
                sev = severities[idx]

                conn.execute("""
                    INSERT INTO anomaly_scores (
                        entity_id, model_name, model_version,
                        anomaly_score, normalized_risk_score, severity
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [eid, self.model_name, self.model_version, r_score, n_risk, sev])

                stored_scores.append({
                    "entity_id": eid,
                    "anomaly_score": r_score,
                    "normalized_risk_score": n_risk,
                    "severity": sev,
                    "cluster_label": int(cluster_labels[idx])
                })

            # Summary statistics
            crit_count = sum(1 for s in severities if s == "CRITICAL")
            high_count = sum(1 for s in severities if s == "HIGH")
            med_count = sum(1 for s in severities if s == "MEDIUM")
            low_count = sum(1 for s in severities if s == "LOW")

            print(f"[SUCCESS] Anomaly Detection & Graph Diffusion Complete:")
            print(f"  - CRITICAL: {crit_count} | HIGH: {high_count} | MEDIUM: {med_count} | LOW: {low_count}")
            print(f"  - Multi-Input Entity Clusters: {common_input_res.get('total_clusters', 0)}")
            print(f"  - Distinct DBSCAN clusters found: {len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)}")

            return {
                "total_entities_evaluated": len(features_df),
                "critical": crit_count,
                "high": high_count,
                "medium": med_count,
                "low": low_count,
                "model_name": self.model_name,
                "model_version": self.model_version
            }
        finally:
            if not self._external_conn:
                conn.close()
