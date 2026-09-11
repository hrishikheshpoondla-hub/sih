import pytest
from app.correlation.engine import CorrelationEngine
from app.graph.network import EntityGraphManager
from app.features.extractor import FeatureExtractor
from app.ml.isolation_forest import AnomalyDetectionPipeline
from app.services.alerts import AlertService

def test_correlation_and_graph():
    corr = CorrelationEngine()
    corr_res = corr.run_correlation()
    assert corr_res["relationships_created"] > 0

    gm = EntityGraphManager()
    G = gm.load_graph()
    assert len(G.nodes) > 0
    assert len(G.edges) > 0

    metrics = gm.compute_graph_metrics()
    assert len(metrics) > 0

def test_ml_and_alerts():
    pipeline = AnomalyDetectionPipeline()
    ml_res = pipeline.run_pipeline()
    assert ml_res["total_entities_evaluated"] > 0

    svc = AlertService()
    alerts = svc.generate_alerts(min_risk_score=40.0)
    assert len(alerts) > 0
    top_dossier = svc.get_alert_dossier(alerts[0]["alert_id"])
    assert top_dossier is not None
    assert len(top_dossier["evidence"]) > 0
