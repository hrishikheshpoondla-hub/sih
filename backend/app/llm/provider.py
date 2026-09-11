"""
backend/app/llm/provider.py
SIH26146 - Local AI Explanation Engine
Uses Ollama with NVIDIA Nemotron 3.5 Lightning (30B MoE, 3B active) locally.
Strict Zero-Hallucination Guardrails:
- Injects ONLY verified evidence, topological relationships, and ML anomaly scores from DuckDB.
- Enforces strict investigative disclaimers (e.g. 'anomalous', 'suspicious lead' - NEVER 'criminal').
- Returns structured investigation notes (summary, evidence highlights, behavioral pattern, leads, limitations).
- Gracefully handles local Ollama connectivity status without crashing or calling external APIs.
"""

import os
import json
import httpx
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.database.connection import DatabaseManager

SYSTEM_INVESTIGATION_PROMPT = """You are an expert Cyber & Blockchain Intelligence Analyst assisting the National Technical Research Organisation (NTRO) for SIH26146.
Your task is to provide an objective, factual, explainable investigative summary for a flagged entity based STRICTLY AND ONLY upon the supplied cryptographic and network evidence.

CRITICAL OPERATIONAL RULES:
1. You must use ONLY the supplied evidence, metrics, and relationships. NEVER invent or hallucinate transactions, wallet addresses, IP addresses, timestamps, or risk scores.
2. This is an investigative decision-support tool. An anomaly does NOT automatically imply criminal activity. Use terms like 'anomalous', 'priority for investigation', 'suspicious lead', 'evidence', and 'confidence'. NEVER declare an entity 'criminal' or 'guilty'.
3. Do not modify or alter any mathematical anomaly scores or baseline figures.
4. Structure your response in clear, concise markdown with these exact sections:
   - **What's Happening? (Plain Language Summary)**: 2-3 sentences in simple, non-technical words explaining what unusual behavior was detected.
   - **Why Is This Unusual?**: 3 bullet points explaining the unusual pattern without confusing ML jargon.
   - **Connected Evidence Summary**: Count of connected transactions, observed network sources, and counterparties.
   - **Recommended Next Step**: Specific, practical action for an investigator to look at next.
   - **Technical Forensic Details (Analyst Mode)**: Precise metrics, deviation ratios, and topological indicators.
   - **Analytical Limitations & Disclaimers**: Clarify that anomalous activity can result from automated operations or legitimate batching.
"""

class LLMProvider(ABC):
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def explain_alert(self, alert_dossier: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def answer_investigator_query(self, alert_dossier: Dict[str, Any], query: str) -> str:
        pass

class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 120.0
    ):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.preferred_model = model_name or os.getenv("OLLAMA_MODEL", "")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", str(timeout)))
        self.model_name = self._resolve_model()

    def _resolve_model(self) -> str:
        """Resolves preferred model or automatically chooses first available model from Ollama."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name", "") for m in res.json().get("models", [])]
                    if self.preferred_model:
                        for m in models:
                            if self.preferred_model in m:
                                return m
                    # Priority check for common local models: llama3.1:8b, llama3.2, nemotron
                    for candidate in ["llama3.1:8b", "llama3.1", "nemotron", "llama3", "llama2", "mistral", "qwen"]:
                        for m in models:
                            if candidate in m.lower():
                                return m
                    if models:
                        return models[0]
        except Exception:
            pass
        return self.preferred_model or "llama3.1:8b"

    def health_check(self) -> Dict[str, Any]:
        """Checks local Ollama service and available models."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name", "") for m in res.json().get("models", [])]
                    active_model = self._resolve_model()
                    self.model_name = active_model
                    model_found = any(active_model in m or m in active_model for m in models)
                    return {
                        "status": "ONLINE",
                        "endpoint": self.base_url,
                        "preferred_model": self.model_name,
                        "model_ready": model_found,
                        "available_models": models
                    }
        except Exception as e:
            return {
                "status": "OFFLINE",
                "endpoint": self.base_url,
                "preferred_model": self.model_name,
                "model_ready": False,
                "error": str(e)
            }

    def _build_context_prompt(self, dossier: Dict[str, Any]) -> str:
        evidence_lines = "\n".join([
            f"- {ev['feature_name']}: {ev['feature_value']} vs population baseline {ev['baseline_value']} ({ev['deviation_ratio']}x deviation). Rationale: {ev['description']}"
            for ev in dossier.get("evidence", [])
        ])

        recent_ips = ", ".join([f"{ip['ip']} ({ip['country']}/{ip['asn']})" for ip in dossier.get("related_ips", [])[:8]])
        recent_txs = ", ".join([f"{tx['txid'][:12]}... ({tx['amount']} BTC)" for tx in dossier.get("related_txs", [])[:6]])

        return f"""
INVESTIGATION CONTEXT:
- Alert ID: {dossier['alert_id']}
- Target Entity Type: {dossier['entity_type']}
- Target Entity Value: {dossier['entity_value']}
- Anomaly Severity: {dossier['severity']}
- Machine Learning Risk Score: {dossier['risk_score']}/100
- Statistical Confidence: {dossier['confidence']}%

VERIFIED FORENSIC EVIDENCE:
{evidence_lines if evidence_lines else 'No discrete feature deviations recorded.'}

NETWORK LAYER METADATA:
- Associated Source IPs: {recent_ips if recent_ips else 'None detected.'}

BLOCKCHAIN LAYER ACTIVITY:
- Recent Transaction Samples: {recent_txs if recent_txs else 'None recorded.'}

Provide your structured analytical assessment using ONLY the verified facts above.
"""

    def explain_alert(self, dossier: Dict[str, Any]) -> Dict[str, Any]:
        """Generates structured explanation via local Ollama Nemotron or deterministic forensic template."""
        user_prompt = self._build_context_prompt(dossier)
        health = self.health_check()

        if health["status"] == "ONLINE" and health["model_ready"]:
            try:
                payload = {
                    "model": self.model_name,
                    "prompt": f"{SYSTEM_INVESTIGATION_PROMPT}\n\n{user_prompt}",
                    "stream": False,
                    "options": {
                        "temperature": 0.1, # Low temperature to prevent hallucinations
                        "num_predict": 350
                    }
                }
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(f"{self.base_url}/api/generate", json=payload)
                    if resp.status_code == 200:
                        explanation_text = resp.json().get("response", "").strip()
                        return {
                            "provider": "Ollama",
                            "model": self.model_name,
                            "explanation": explanation_text,
                            "is_local_inference": True
                        }
            except Exception as e:
                print(f"[WARN] Local Ollama request failed: {e}. Falling back to deterministic narrative.")

        # Deterministic Forensic Narrative Fallback (Strictly Grounded, 100% Offline)
        explanation_text = self._generate_deterministic_narrative(dossier)
        return {
            "provider": "LocalForensicEngine (Ollama standby)",
            "model": self.model_name,
            "explanation": explanation_text,
            "is_local_inference": True
        }

    def _generate_deterministic_narrative(self, dossier: Dict[str, Any]) -> str:
        ev_items = dossier.get("evidence", [])
        
        # Build plain language reasons
        reasons = []
        for ev in ev_items:
            feat = ev.get("feature_name", "")
            desc = ev.get("description", "")
            if "burst" in feat or "frequency" in feat:
                reasons.append("• **Very unusual transaction speed**: Transactions occurred at a rate significantly higher than typical wallets.")
            elif "counterparties" in feat or "degree" in feat:
                reasons.append(f"• **Many counterparties**: The wallet interacted with {int(ev.get('feature_value', 0))} different destinations or sources.")
            elif "unique_ips" in feat:
                reasons.append(f"• **Multiple network sources**: Activity was broadcast from {int(ev.get('feature_value', 0))} distinct network IP addresses.")
            elif "volume" in feat:
                reasons.append(f"• **High throughput**: Moved {ev.get('feature_value', 0):.2f} BTC, significantly exceeding the median baseline.")
            else:
                reasons.append(f"• **Behavioral outlier**: {desc}")
        
        if not reasons:
            reasons.append("• **Statistical outlier**: Multi-dimensional deviation across network topology metrics.")

        reasons_text = "\n".join(reasons[:4])
        num_ips = len(dossier.get('related_ips', []))
        num_txs = len(dossier.get('related_txs', []))
        
        evidence_bullets = "\n".join([f"- **{ev['feature_name']}**: {ev['description']} (Deviation: {ev.get('deviation_ratio', 'N/A')}x)" for ev in ev_items])
        ips_str = ", ".join([f"`{ip['ip']}`" for ip in dossier.get("related_ips", [])[:5]])
        
        return f"""### What's Happening?
This entity (`{dossier['entity_value'][:20]}...`) exhibits an unusual pattern of activity in the monitored Bitcoin network. It displays coordinated behavior and transaction velocity that sharply deviates from the vast majority of observed entities in this dataset.

### Why Is This Unusual?
{reasons_text}

### Connected Evidence Summary
- **Observed Transactions**: {num_txs} transactions recorded in the correlation window
- **Associated Network Sources**: {num_ips} distinct source IP addresses observed ({ips_str if ips_str else 'N/A'})
- **Investigation Priority Level**: **{dossier['severity']}** ({dossier['risk_score']}/100 priority index, {dossier['confidence']}% confidence)

### Recommended Next Step
Review the highlighted incoming and outgoing transactions to identify immediate counterparties and check whether associated source IPs correlate with shared hosting, VPN relays, or automated script infrastructure.

---

### Technical Forensic Details (Analyst Mode)
{evidence_bullets}

### Analytical Limitations & Disclaimers
*This finding is an automated investigative decision-support output and does NOT independently prove illicit or criminal conduct. High velocity or burst frequency can also occur during automated batch operations, exchange hot-wallet rebalancing, or legitimate mining pool payouts. Further human verification against external intelligence records is required.*
"""

    def answer_investigator_query(self, dossier: Dict[str, Any], query: str) -> str:
        """Answers analyst questions grounded strictly on dossier evidence."""
        user_prompt = f"""{self._build_context_prompt(dossier)}

INVESTIGATOR QUESTION:
{query}

Answer the question factually based ONLY on the evidence above.
"""
        health = self.health_check()
        if health["status"] == "ONLINE" and health["model_ready"]:
            try:
                payload = {
                    "model": self.model_name,
                    "prompt": f"{SYSTEM_INVESTIGATION_PROMPT}\n\n{user_prompt}",
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 400}
                }
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(f"{self.base_url}/api/generate", json=payload)
                    if resp.status_code == 200:
                        return resp.json().get("response", "").strip()
            except Exception:
                pass

        # Offline grounded response
        return f"Based on the stored evidence for {dossier['alert_id']}, the entity exhibits a normalized risk score of {dossier['risk_score']}/100. Recorded evidence demonstrates: " + "; ".join([ev["description"] for ev in dossier.get("evidence", [])[:2]])
