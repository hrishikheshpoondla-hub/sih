"""
backend/app/services/alerts.py
SIH26146 - Investigation Alerts Service
Generates ranked, explainable investigation leads from ML anomaly detection scores.
Associates each alert with granular mathematical evidence and maintains workflow status:
- NEW, INVESTIGATING, REVIEWED, DISMISSED
"""

import uuid
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.database.connection import DatabaseManager
from app.services.evidence import EvidenceEngine

class AlertService:
    def __init__(self, db_conn=None):
        self.db_mgr = DatabaseManager.get_instance()
        self._external_conn = db_conn
        self.evidence_engine = EvidenceEngine(db_conn)

    def _get_conn(self):
        return self._external_conn if self._external_conn else self.db_mgr.get_connection()

    def generate_alerts(self, min_risk_score: float = 40.0) -> List[Dict[str, Any]]:
        """Generates investigation alerts for entities exceeding the risk threshold."""
        conn = self._get_conn()
        try:
            # 1. Fetch flagged entities from anomaly_scores
            flagged = conn.execute("""
                SELECT s.score_id, s.entity_id, s.model_name, s.anomaly_score,
                       s.normalized_risk_score, s.severity, e.entity_value, e.entity_type
                FROM anomaly_scores s
                JOIN entities e ON s.entity_id = e.entity_id
                WHERE s.normalized_risk_score >= ?
                ORDER BY s.normalized_risk_score DESC;
            """, [min_risk_score]).fetchall()

            if not flagged:
                print(f"[INFO] No entities exceeded risk score threshold of {min_risk_score}.")
                return []

            # Clear existing alerts and evidence to allow fresh recalculation
            conn.execute("DELETE FROM alert_evidence;")
            conn.execute("DELETE FROM investigation_alerts;")

            baselines = self.evidence_engine.get_population_baselines()
            created_alerts = []

            for rank_idx, (score_id, eid, model, raw_score, risk_score, severity, evalue, etype) in enumerate(flagged, start=1):
                alert_id = f"ALT-{rank_idx:03d}"
                
                # Fetch multi-signal evidence to determine true epistemic confidence
                evidence_items = self.evidence_engine.generate_evidence_for_entity(eid, alert_id, baselines)
                
                # Rigorous Statistical Confidence derivation:
                # 1. Base certainty from sample size / transaction depth (min 40%)
                feat_sample = conn.execute("SELECT transaction_count, unique_ips, burst_frequency FROM entity_features WHERE entity_id = ?;", [eid]).fetchone()
                tx_cnt = feat_sample[0] if feat_sample else 1
                ip_cnt = feat_sample[1] if feat_sample else 1
                burst_cnt = feat_sample[2] if feat_sample else 1

                # Sample size factor: More historical observations = higher confidence in anomaly stability
                sample_certainty = min(25.0, np.log1p(tx_cnt) * 6.0) # Up to 25%
                
                # Multi-Signal Convergence factor:
                # Convergence of independent signals (burst timing + network IP spread + volume)
                num_evidence = len(evidence_items)
                signal_convergence = min(35.0, num_evidence * 8.5) # Up to 35%
                
                # Signal strength factor:
                max_dev = max([ev.get("deviation_ratio", 1.0) for ev in evidence_items], default=1.0)
                strength_factor = min(35.0, np.log1p(max_dev) * 10.0) # Up to 35%

                # Base floor of 40%
                raw_confidence = 40.0 + sample_certainty + signal_convergence + strength_factor
                confidence = round(float(np.clip(raw_confidence, 45.0, 99.2)), 1)
                
                # Title formulation based on severity and entity
                title = f"Investigative Lead: {severity} Behavioral Anomaly Detected on {etype} {evalue[:16]}..."

                # 2. Insert Alert
                conn.execute("""
                    INSERT INTO investigation_alerts (
                        alert_id, entity_id, anomaly_score_id, severity,
                        confidence, status, title, ai_explanation
                    )
                    VALUES (?, ?, ?, ?, ?, 'NEW', ?, NULL);
                """, [alert_id, eid, score_id, severity, confidence, title])

                # 3. Insert Evidence Items (already generated above)
                for ev in evidence_items:
                    conn.execute("""
                        INSERT INTO alert_evidence (
                            alert_id, feature_name, feature_value,
                            baseline_value, deviation_ratio, evidence_description
                        )
                        VALUES (?, ?, ?, ?, ?, ?);
                    """, [
                        alert_id, ev["feature_name"], ev["feature_value"],
                        ev["baseline_value"], ev["deviation_ratio"], ev["evidence_description"]
                    ])

                created_alerts.append({
                    "alert_id": alert_id,
                    "entity_id": eid,
                    "entity_value": evalue,
                    "severity": severity,
                    "risk_score": risk_score,
                    "confidence": confidence,
                    "evidence_count": len(evidence_items)
                })

            print(f"[SUCCESS] Generated {len(created_alerts)} investigation alerts with linked evidence.")
            return created_alerts
        finally:
            if not self._external_conn:
                conn.close()

    def get_alert_dossier(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves complete investigation dossier for an alert: entity, ML score, evidence, and topology."""
        conn = self._get_conn()
        try:
            alert_row = conn.execute("""
                SELECT a.alert_id, a.entity_id, a.severity, a.confidence, a.status,
                       a.title, a.ai_explanation, a.created_at,
                       e.entity_value, e.entity_type,
                       s.normalized_risk_score, s.anomaly_score
                FROM investigation_alerts a
                JOIN entities e ON a.entity_id = e.entity_id
                JOIN anomaly_scores s ON a.anomaly_score_id = s.score_id
                WHERE a.alert_id = ?;
            """, [alert_id]).fetchone()

            if not alert_row:
                return None

            aid, eid, sev, conf, status, title, ai_exp, created_at, evalue, etype, risk_score, raw_score = alert_row

            # Fetch linked evidence items
            evidence_rows = conn.execute("""
                SELECT feature_name, feature_value, baseline_value, deviation_ratio, evidence_description
                FROM alert_evidence
                WHERE alert_id = ?;
            """, [alert_id]).fetchall()

            evidence_list = [
                {
                    "feature_name": r[0],
                    "feature_value": r[1],
                    "baseline_value": r[2],
                    "deviation_ratio": r[3],
                    "description": r[4]
                }
                for r in evidence_rows
            ]

            # Fetch related IPs, Wallets, and TXIDs
            related_ips = conn.execute("""
                SELECT DISTINCT no.src_ip, no.timestamp, ip.country, ip.asn
                FROM network_observations no
                JOIN transaction_inputs ti ON no.txid = ti.txid
                LEFT JOIN ip_addresses ip ON no.src_ip = ip.ip_address
                WHERE ti.wallet_address = ?
                ORDER BY no.timestamp DESC LIMIT 15;
            """, [evalue]).fetchall()

            related_txs = conn.execute("""
                SELECT DISTINCT t.txid, t.timestamp, t.total_input_amount, t.fee
                FROM transactions t
                JOIN transaction_inputs ti ON t.txid = ti.txid
                WHERE ti.wallet_address = ?
                ORDER BY t.timestamp DESC LIMIT 15;
            """, [evalue]).fetchall()

            return {
                "alert_id": aid,
                "entity_id": eid,
                "entity_value": evalue,
                "entity_type": etype,
                "severity": sev,
                "risk_score": risk_score,
                "confidence": conf,
                "status": status,
                "title": title,
                "ai_explanation": ai_exp,
                "created_at": str(created_at),
                "evidence": evidence_list,
                "related_ips": [{"ip": r[0], "timestamp": str(r[1]), "country": r[2], "asn": r[3]} for r in related_ips],
                "related_txs": [{"txid": r[0], "timestamp": str(r[1]), "amount": r[2], "fee": r[3]} for r in related_txs]
            }
        finally:
            if not self._external_conn:
                conn.close()
