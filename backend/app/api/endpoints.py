"""
backend/app/api/endpoints.py
SIH26146 - FastAPI Endpoints
Implements all required REST API routes for:
- Health and statistics
- Data ingestion (CSV, JSON, XML file upload)
- Transactions, Wallets, and IPs exploration
- Entities and NetworkX graph topology
- Investigation alerts, evidence dossiers, and status updates
- Automated ML pipeline execution (/analyze)
- Local AI / Nemotron explanation generation (/explain/{alert_id})
"""

import os
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.database.connection import DatabaseManager
from app.database.schema import reset_schema
from app.ingestion.pipeline import IngestionPipeline
from app.correlation.engine import CorrelationEngine
from app.ml.isolation_forest import AnomalyDetectionPipeline
from app.graph.network import EntityGraphManager
from app.services.alerts import AlertService
from app.llm.provider import OllamaProvider

router = APIRouter()

# Dependency helpers
def get_db():
    return DatabaseManager.get_instance().get_connection()

# Schemas
class StatusUpdateRequest(BaseModel):
    status: str # 'NEW', 'INVESTIGATING', 'REVIEWED', 'DISMISSED'

class QueryExplanationRequest(BaseModel):
    query: str

# 1. GET /health
@router.get("/health")
def health_check():
    conn = get_db()
    try:
        tables_cnt = conn.execute("SELECT count(*) FROM (SHOW TABLES);").fetchone()[0]
        llm = OllamaProvider()
        llm_health = llm.health_check()
        return {
            "status": "HEALTHY",
            "service": "SIH26146 Bitcoin Traffic Monitoring & Analysis",
            "database": {
                "engine": "DuckDB",
                "tables_count": tables_cnt,
                "status": "CONNECTED"
            },
            "ollama_ai": llm_health
        }
    finally:
        conn.close()

# 2. GET /statistics
@router.get("/statistics")
def get_statistics():
    conn = get_db()
    try:
        stats = {}
        stats["total_transactions"] = conn.execute("SELECT count(*) FROM transactions;").fetchone()[0]
        stats["total_wallets"] = conn.execute("SELECT count(*) FROM wallets;").fetchone()[0]
        stats["total_ips"] = conn.execute("SELECT count(*) FROM ip_addresses;").fetchone()[0]
        stats["total_network_observations"] = conn.execute("SELECT count(*) FROM network_observations;").fetchone()[0]
        stats["total_alerts"] = conn.execute("SELECT count(*) FROM investigation_alerts;").fetchone()[0]
        stats["critical_alerts"] = conn.execute("SELECT count(*) FROM investigation_alerts WHERE severity = 'CRITICAL';").fetchone()[0]
        stats["high_alerts"] = conn.execute("SELECT count(*) FROM investigation_alerts WHERE severity = 'HIGH';").fetchone()[0]
        stats["medium_alerts"] = conn.execute("SELECT count(*) FROM investigation_alerts WHERE severity = 'MEDIUM';").fetchone()[0]

        # Anomaly score distribution
        score_dist = conn.execute("""
            SELECT severity, count(*) as cnt
            FROM anomaly_scores
            GROUP BY severity;
        """).fetchall()
        stats["anomaly_distribution"] = {s[0]: s[1] for s in score_dist}

        # Activity timeline by hour
        activity = conn.execute("""
            SELECT strftime(timestamp, '%Y-%m-%d %H:00') as hr, count(*) as tx_count, sum(total_input_amount) as vol
            FROM transactions
            GROUP BY hr
            ORDER BY hr ASC
            LIMIT 24;
        """).fetchall()
        stats["hourly_activity"] = [{"time": a[0], "transactions": a[1], "volume": round(a[2] or 0.0, 4)} for a in activity]

        return stats
    finally:
        conn.close()

# 3. POST /ingest
@router.post("/ingest")
async def ingest_dataset(
    file: UploadFile = File(...),
    mode: str = Form("REPLACE"),
    dataset_id: str = Form("USER_UPLOAD")
):
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    upload_dir = project_root / "data" / "raw" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Archive raw upload permanently with timestamp
    from datetime import datetime, timezone
    ts_prefix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archived_filename = f"{ts_prefix}_{dataset_id}_{file.filename}"
    temp_path = upload_dir / archived_filename

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Also keep latest copy at data/raw/{filename}
    latest_raw = project_root / "data" / "raw" / file.filename
    try:
        shutil.copyfile(temp_path, latest_raw)
    except Exception:
        pass

    try:
        conn = get_db()
        # If REPLACE mode, cleanly reset existing schema tables
        if mode.upper() == "REPLACE":
            reset_schema(conn)
            conn.close()

        # Ingest the uploaded file
        pipeline = IngestionPipeline()
        result = pipeline.ingest_file(temp_path)

        # Automatically trigger end-to-end analytics pipeline
        print("[AUTO-PIPELINE] 1/3 Running Metadata Correlation...")
        corr = CorrelationEngine()
        corr_res = corr.run_correlation()
        result["correlation"] = corr_res

        print("[AUTO-PIPELINE] 2/3 Running Feature Extraction & Isolation Forest...")
        ml_pipeline = AnomalyDetectionPipeline()
        ml_res = ml_pipeline.run_pipeline()
        result["ml_results"] = ml_res

        print("[AUTO-PIPELINE] 3/3 Generating Prioritized Investigation Alerts...")
        alert_svc = AlertService()
        alerts_created = alert_svc.generate_alerts(min_risk_score=40.0)
        result["alerts_generated"] = len(alerts_created)

        # Query fresh database counts
        conn = get_db()
        try:
            tx_cnt = conn.execute("SELECT count(*) FROM transactions;").fetchone()[0]
            wallet_cnt = conn.execute("SELECT count(*) FROM wallets;").fetchone()[0]
            ip_cnt = conn.execute("SELECT count(*) FROM ip_addresses;").fetchone()[0]
            obs_cnt = conn.execute("SELECT count(*) FROM network_observations;").fetchone()[0]
            alt_cnt = conn.execute("SELECT count(*) FROM investigation_alerts;").fetchone()[0]
            
            result["dataset_id"] = dataset_id
            result["mode"] = mode.upper()
            result["transactions_inserted"] = tx_cnt
            result["wallets_count"] = wallet_cnt
            result["ips_count"] = ip_cnt
            result["observations_count"] = obs_cnt
            result["total_alerts"] = alt_cnt
        finally:
            conn.close()

        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

# 4. POST /analyze
@router.post("/analyze")
def trigger_analysis(min_risk: float = 40.0):
    """Runs Feature Extraction, Isolation Forest Anomaly Detection, and Alert Generation."""
    corr = CorrelationEngine()
    corr.run_correlation()

    ml_pipeline = AnomalyDetectionPipeline()
    ml_res = ml_pipeline.run_pipeline()

    alert_svc = AlertService()
    alerts_created = alert_svc.generate_alerts(min_risk_score=min_risk)

    return {
        "status": "COMPLETED",
        "ml_results": ml_res,
        "alerts_generated": len(alerts_created),
        "top_alerts": alerts_created[:5]
    }


# 5. GET /transactions
@router.get("/transactions")
def list_transactions(limit: int = 50, offset: int = 0):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT txid, timestamp, fee, total_input_amount, total_output_amount, script_type
            FROM transactions
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?;
        """, [limit, offset]).fetchall()
        total = conn.execute("SELECT count(*) FROM transactions;").fetchone()[0]
        return {
            "total": total,
            "transactions": [
                {
                    "txid": r[0],
                    "timestamp": str(r[1]),
                    "fee": r[2],
                    "input_amount": r[3],
                    "output_amount": r[4],
                    "script_type": r[5]
                }
                for r in rows
            ]
        }
    finally:
        conn.close()

# 6. GET /transaction/{txid}
@router.get("/transaction/{txid}")
def get_transaction(txid: str):
    conn = get_db()
    try:
        tx = conn.execute("""
            SELECT txid, timestamp, fee, total_input_amount, total_output_amount, script_type
            FROM transactions WHERE txid = ?;
        """, [txid]).fetchone()
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")

        inputs = conn.execute("SELECT wallet_address, amount, input_index FROM transaction_inputs WHERE txid = ?;", [txid]).fetchall()
        outputs = conn.execute("SELECT wallet_address, amount, output_index FROM transaction_outputs WHERE txid = ?;", [txid]).fetchall()
        net_obs = conn.execute("SELECT src_ip, dst_ip, src_port, dst_port, timestamp FROM network_observations WHERE txid = ?;", [txid]).fetchall()

        return {
            "txid": tx[0],
            "timestamp": str(tx[1]),
            "fee": tx[2],
            "total_input": tx[3],
            "total_output": tx[4],
            "script_type": tx[5],
            "inputs": [{"address": r[0], "amount": r[1], "index": r[2]} for r in inputs],
            "outputs": [{"address": r[0], "amount": r[1], "index": r[2]} for r in outputs],
            "network_observations": [{"src_ip": r[0], "dst_ip": r[1], "src_port": r[2], "dst_port": r[3], "timestamp": str(r[4])} for r in net_obs]
        }
    finally:
        conn.close()

# 7. GET /wallets
@router.get("/wallets")
def list_wallets(limit: int = 50, offset: int = 0):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT w.wallet_address, w.first_seen, w.last_seen, w.total_transactions,
                   w.total_inbound_amount, w.total_outbound_amount, w.unique_counterparties,
                   w.unique_ips, s.normalized_risk_score, s.severity
            FROM wallets w
            LEFT JOIN entities e ON w.wallet_address = e.entity_value
            LEFT JOIN anomaly_scores s ON e.entity_id = s.entity_id
            ORDER BY COALESCE(s.normalized_risk_score, 0) DESC, w.total_transactions DESC
            LIMIT ? OFFSET ?;
        """, [limit, offset]).fetchall()
        total = conn.execute("SELECT count(*) FROM wallets;").fetchone()[0]
        return {
            "total": total,
            "wallets": [
                {
                    "wallet_address": r[0],
                    "first_seen": str(r[1]) if r[1] else None,
                    "last_seen": str(r[2]) if r[2] else None,
                    "total_transactions": r[3],
                    "total_inbound": r[4],
                    "total_outbound": r[5],
                    "unique_counterparties": r[6],
                    "unique_ips": r[7],
                    "risk_score": r[8] if r[8] is not None else 0.0,
                    "severity": r[9] or "LOW"
                }
                for r in rows
            ]
        }
    finally:
        conn.close()

# 8. GET /wallet/{wallet_address}
@router.get("/wallet/{wallet_address}")
def get_wallet(wallet_address: str):
    conn = get_db()
    try:
        w = conn.execute("""
            SELECT wallet_address, first_seen, last_seen, total_transactions,
                   total_inbound_amount, total_outbound_amount, unique_counterparties,
                   unique_ips, unique_countries, unique_asns
            FROM wallets WHERE wallet_address = ?;
        """, [wallet_address]).fetchone()
        if not w:
            raise HTTPException(status_code=404, detail="Wallet address not found")

        # Entity ID & Risk
        ent = conn.execute("""
            SELECT e.entity_id, s.normalized_risk_score, s.severity, a.alert_id
            FROM entities e
            LEFT JOIN anomaly_scores s ON e.entity_id = s.entity_id
            LEFT JOIN investigation_alerts a ON e.entity_id = a.entity_id
            WHERE e.entity_value = ?;
        """, [wallet_address]).fetchone()

        features = conn.execute("SELECT * FROM entity_features WHERE entity_id = ?;", [ent[0] if ent else -1]).fetchdf()
        feat_dict = features.to_dict(orient="records")[0] if not features.empty else {}

        return {
            "wallet_address": w[0],
            "first_seen": str(w[1]),
            "last_seen": str(w[2]),
            "total_transactions": w[3],
            "total_inbound": w[4],
            "total_outbound": w[5],
            "unique_counterparties": w[6],
            "unique_ips": w[7],
            "unique_countries": w[8],
            "unique_asns": w[9],
            "risk_score": ent[1] if ent and ent[1] is not None else 0.0,
            "severity": ent[2] if ent and ent[2] else "LOW",
            "linked_alert_id": ent[3] if ent else None,
            "features": feat_dict
        }
    finally:
        conn.close()

# 9. GET /ips
@router.get("/ips")
def list_ips(limit: int = 50, offset: int = 0):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT ip.ip_address, ip.country, ip.asn, ip.first_seen, ip.last_seen,
                   count(DISTINCT no.txid) as broadcast_tx_count
            FROM ip_addresses ip
            LEFT JOIN network_observations no ON ip.ip_address = no.src_ip
            GROUP BY ip.ip_address, ip.country, ip.asn, ip.first_seen, ip.last_seen
            ORDER BY broadcast_tx_count DESC
            LIMIT ? OFFSET ?;
        """, [limit, offset]).fetchall()
        total = conn.execute("SELECT count(*) FROM ip_addresses;").fetchone()[0]
        return {
            "total": total,
            "ips": [
                {
                    "ip_address": r[0],
                    "country": r[1],
                    "asn": r[2],
                    "first_seen": str(r[3]),
                    "last_seen": str(r[4]),
                    "broadcast_tx_count": r[5]
                }
                for r in rows
            ]
        }
    finally:
        conn.close()

# 10. GET /ip/{ip_address}
@router.get("/ip/{ip_address}")
def get_ip(ip_address: str):
    conn = get_db()
    try:
        ip_row = conn.execute("SELECT ip_address, country, asn, first_seen, last_seen FROM ip_addresses WHERE ip_address = ?;", [ip_address]).fetchone()
        if not ip_row:
            raise HTTPException(status_code=404, detail="IP address not found")

        txs = conn.execute("""
            SELECT DISTINCT txid, timestamp, src_port, dst_port
            FROM network_observations WHERE src_ip = ?
            ORDER BY timestamp DESC LIMIT 20;
        """, [ip_address]).fetchall()

        return {
            "ip_address": ip_row[0],
            "country": ip_row[1],
            "asn": ip_row[2],
            "first_seen": str(ip_row[3]),
            "last_seen": str(ip_row[4]),
            "associated_transactions": [{"txid": r[0], "timestamp": str(r[1]), "src_port": r[2], "dst_port": r[3]} for r in txs]
        }
    finally:
        conn.close()

# 11. GET /entities
@router.get("/entities")
def list_entities(entity_type: Optional[str] = None, limit: int = 50, offset: int = 0):
    conn = get_db()
    try:
        query = "SELECT entity_id, entity_type, entity_value, first_seen, last_seen FROM entities"
        params = []
        if entity_type:
            query += " WHERE entity_type = ?"
            params.append(entity_type.upper())
        query += " ORDER BY entity_id ASC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [
            {"entity_id": r[0], "entity_type": r[1], "entity_value": r[2], "first_seen": str(r[3]), "last_seen": str(r[4])}
            for r in rows
        ]
    finally:
        conn.close()

# 12. GET /entity/{entity_id}
@router.get("/entity/{entity_id}")
def get_entity(entity_id: int):
    conn = get_db()
    try:
        ent = conn.execute("SELECT entity_id, entity_type, entity_value, first_seen, last_seen FROM entities WHERE entity_id = ?;", [entity_id]).fetchone()
        if not ent:
            raise HTTPException(status_code=404, detail="Entity not found")

        eid, etype, evalue, fs, ls = ent

        # Check risk and alert status
        risk_row = conn.execute("""
            SELECT coalesce(s.normalized_risk_score, 0.0), coalesce(s.severity, 'LOW'), a.alert_id, a.confidence, a.ai_explanation
            FROM entities e
            LEFT JOIN anomaly_scores s ON e.entity_id = s.entity_id
            LEFT JOIN investigation_alerts a ON e.entity_id = a.entity_id
            WHERE e.entity_id = ?;
        """, [eid]).fetchone()

        risk_score = float(risk_row[0]) if risk_row else 0.0
        severity = str(risk_row[1]) if risk_row else "LOW"
        alert_id = risk_row[2] if risk_row else None
        confidence = float(risk_row[3]) if (risk_row and risk_row[3] is not None) else 0.0
        ai_explanation = risk_row[4] if risk_row else None

        # Fetch evidence factors if an alert exists or compute from entity_features
        evidence_factors = []
        if alert_id:
            ev_rows = conn.execute("""
                SELECT feature_name, feature_value, baseline_value, deviation_ratio, evidence_description
                FROM alert_evidence WHERE alert_id = ?;
            """, [alert_id]).fetchall()
            evidence_factors = [
                {
                    "feature_name": r[0],
                    "feature_value": r[1],
                    "baseline_value": r[2],
                    "deviation_ratio": r[3],
                    "description": r[4]
                }
                for r in ev_rows
            ]

        # Fetch feature metrics
        feat_row = conn.execute("SELECT * FROM entity_features WHERE entity_id = ?;", [eid]).fetchdf()
        features = feat_row.to_dict(orient="records")[0] if not feat_row.empty else {}

        # Related source IPs
        related_ips = []
        if etype == "WALLET":
            ip_rows = conn.execute("""
                SELECT DISTINCT no.src_ip, ip.country, ip.asn, count(*) as count
                FROM network_observations no
                JOIN transaction_inputs ti ON no.txid = ti.txid
                LEFT JOIN ip_addresses ip ON no.src_ip = ip.ip_address
                WHERE ti.wallet_address = ?
                GROUP BY no.src_ip, ip.country, ip.asn
                ORDER BY count DESC LIMIT 8;
            """, [evalue]).fetchall()
            related_ips = [{"ip": r[0], "country": r[1] or "Unknown", "asn": r[2] or "Unknown", "count": r[3]} for r in ip_rows]
        elif etype == "IP":
            related_ips = [{"ip": evalue, "country": "Self", "asn": "Observed"}]

        # Recent transactions and stats
        recent_txs = []
        tx_stats = {"total_txs": 0, "total_inbound": 0.0, "total_outbound": 0.0}
        if etype == "WALLET":
            w_row = conn.execute("SELECT total_transactions, total_inbound_amount, total_outbound_amount FROM wallets WHERE wallet_address = ?;", [evalue]).fetchone()
            if w_row:
                tx_stats = {"total_txs": w_row[0], "total_inbound": w_row[1], "total_outbound": w_row[2]}
            tx_rows = conn.execute("""
                SELECT DISTINCT t.txid, t.timestamp, t.total_input_amount, t.fee
                FROM transactions t
                JOIN transaction_inputs ti ON t.txid = ti.txid
                WHERE ti.wallet_address = ?
                ORDER BY t.timestamp DESC LIMIT 8;
            """, [evalue]).fetchall()
            recent_txs = [{"txid": r[0], "timestamp": str(r[1]), "amount": r[2], "fee": r[3]} for r in tx_rows]
        elif etype == "TXID":
            t_row = conn.execute("SELECT txid, timestamp, total_input_amount, total_output_amount, fee FROM transactions WHERE txid = ?;", [evalue]).fetchone()
            if t_row:
                tx_stats = {"total_txs": 1, "total_inbound": t_row[2], "total_outbound": t_row[3]}
                recent_txs = [{"txid": t_row[0], "timestamp": str(t_row[1]), "amount": t_row[2], "fee": t_row[4]}]

        # Outgoing relationships
        rels = conn.execute("""
            SELECT r.relationship_type, r.weight, r.transaction_count,
                   e_tgt.entity_id, e_tgt.entity_type, e_tgt.entity_value
            FROM entity_relationships r
            JOIN entities e_tgt ON r.target_entity_id = e_tgt.entity_id
            WHERE r.source_entity_id = ?
            LIMIT 30;
        """, [entity_id]).fetchall()

        return {
            "entity_id": eid,
            "entity_type": etype,
            "entity_value": evalue,
            "first_seen": str(fs) if fs else "",
            "last_seen": str(ls) if ls else "",
            "risk_score": risk_score,
            "severity": severity,
            "alert_id": alert_id,
            "confidence": confidence,
            "ai_explanation": ai_explanation,
            "evidence_factors": evidence_factors,
            "features": features,
            "related_ips": related_ips,
            "tx_stats": tx_stats,
            "recent_transactions": recent_txs,
            "outgoing_relationships": [
                {
                    "relationship_type": r[0],
                    "weight": r[1],
                    "transaction_count": r[2],
                    "target_entity": {"id": r[3], "type": r[4], "value": r[5]}
                }
                for r in rels
            ]
        }
    finally:
        conn.close()

# 13. GET /graph/{entity_id}
@router.get("/graph/{entity_id}")
def get_entity_graph(entity_id: int, hops: int = 2, max_nodes: int = 60):
    gm = EntityGraphManager()
    subgraph = gm.get_neighborhood_subgraph(entity_id, max_hops=hops, max_nodes=max_nodes)
    return subgraph

# 13b. GET /clusters
@router.get("/clusters")
def get_common_input_clusters():
    """Returns Common-Input Ownership clusters (Heuristic 1 multi-input entities)."""
    gm = EntityGraphManager()
    return gm.compute_common_input_clusters()

# 13c. GET /patterns
@router.get("/patterns")
def get_laundering_patterns():
    """Returns detected Peeling Chains and CoinJoin/Mixing Rounds."""
    conn = get_db()
    try:
        corr = CorrelationEngine(conn)
        peeling = corr.detect_peeling_chains(conn)
        mixing = corr.detect_mixing_patterns(conn)
        return {
            "peeling_chains": peeling,
            "peeling_chain_count": len(peeling),
            "mixing_rounds": mixing,
            "mixing_round_count": len(mixing)
        }
    finally:
        conn.close()

# 14. GET /alerts
@router.get("/alerts")
def list_alerts(severity: Optional[str] = None, status: Optional[str] = None):
    conn = get_db()
    try:
        query = """
            SELECT a.alert_id, a.entity_id, a.severity, a.confidence, a.status,
                   a.title, a.created_at, e.entity_value, e.entity_type,
                   s.normalized_risk_score,
                   (SELECT count(*) FROM alert_evidence ev WHERE ev.alert_id = a.alert_id) as evidence_count
            FROM investigation_alerts a
            JOIN entities e ON a.entity_id = e.entity_id
            LEFT JOIN anomaly_scores s ON a.anomaly_score_id = s.score_id
            WHERE 1=1
        """
        params = []
        if severity:
            query += " AND a.severity = ?"
            params.append(severity.upper())
        if status:
            query += " AND a.status = ?"
            params.append(status.upper())
        query += " ORDER BY s.normalized_risk_score DESC, a.created_at DESC;"

        rows = conn.execute(query, params).fetchall()
        return [
            {
                "alert_id": r[0],
                "entity_id": r[1],
                "severity": r[2],
                "confidence": r[3],
                "status": r[4],
                "title": r[5],
                "created_at": str(r[6]),
                "entity_value": r[7],
                "entity_type": r[8],
                "risk_score": r[9] or 0.0,
                "evidence_count": r[10]
            }
            for r in rows
        ]
    finally:
        conn.close()

# 15. GET /alerts/{alert_id}
@router.get("/alerts/{alert_id}")
def get_alert_dossier(alert_id: str):
    svc = AlertService()
    dossier = svc.get_alert_dossier(alert_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Alert not found")
    return dossier

# 16. PATCH /alerts/{alert_id}/status
@router.patch("/alerts/{alert_id}/status")
def update_alert_status(alert_id: str, req: StatusUpdateRequest):
    valid_statuses = ["NEW", "INVESTIGATING", "REVIEWED", "DISMISSED"]
    if req.status.upper() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    conn = get_db()
    try:
        conn.execute("""
            UPDATE investigation_alerts
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE alert_id = ?;
        """, [req.status.upper(), alert_id])
        return {"alert_id": alert_id, "status": req.status.upper()}
    finally:
        conn.close()

# 17. POST /explain/{alert_id}
@router.post("/explain/{alert_id}")
def generate_ai_explanation(alert_id: str):
    svc = AlertService()
    dossier = svc.get_alert_dossier(alert_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Alert not found")

    llm = OllamaProvider()
    res = llm.explain_alert(dossier)
    explanation_text = res.get("explanation", "")

    # Save to database
    conn = get_db()
    try:
        conn.execute("""
            UPDATE investigation_alerts
            SET ai_explanation = ?, updated_at = CURRENT_TIMESTAMP
            WHERE alert_id = ?;
        """, [explanation_text, alert_id])
    finally:
        conn.close()

    return {
        "alert_id": alert_id,
        "provider": res.get("provider"),
        "model": res.get("model"),
        "ai_explanation": explanation_text
    }

# 18. POST /alerts/{alert_id}/ask
@router.post("/alerts/{alert_id}/ask")
def ask_ai_about_alert(alert_id: str, req: QueryExplanationRequest):
    svc = AlertService()
    dossier = svc.get_alert_dossier(alert_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Alert not found")

    llm = OllamaProvider()
    answer = llm.answer_investigator_query(dossier, req.query)
    return {
        "alert_id": alert_id,
        "query": req.query,
        "response": answer
    }
