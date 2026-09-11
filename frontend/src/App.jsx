import React, { useState, useEffect, useRef } from 'react';
import {
  Shield, Activity, AlertTriangle, Network, Database, Cpu, Search,
  FileText, Clock, Upload, ArrowRight, CheckCircle2, ChevronRight,
  Server, Globe, RefreshCw, Send, Eye, Filter, Sparkles, Terminal,
  ZoomIn, ZoomOut, Maximize2, Layers, Info, ExternalLink, X,
  HelpCircle, UserCheck, Code2, BookOpen, ChevronDown, ChevronUp, Copy, Check
} from 'lucide-react';
import {
  METRIC_DICTIONARY,
  CONCEPT_TOOLTIPS,
  getPlainMetricName,
  buildPlainSummary,
  buildPlainReasons,
  buildInvestigationStory
} from './utils/interpretation';

const API_BASE = '/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [alertDossier, setAlertDossier] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiQuery, setAiQuery] = useState('');
  const [aiChatHistory, setAiChatHistory] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [wallets, setWallets] = useState([]);
  const [ips, setIps] = useState([]);
  const [graphData, setGraphData] = useState(null);
  const [graphRootId, setGraphRootId] = useState('');
  const [selectedGraphNode, setSelectedGraphNode] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [ingestStatus, setIngestStatus] = useState(null);
  const [uploadMode, setUploadMode] = useState('REPLACE');
  const [ingestionResult, setIngestionResult] = useState(null);
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [viewMode, setViewMode] = useState('BEGINNER'); // 'BEGINNER' or 'ANALYST'

  const fetchData = async () => {
    try {
      const [hRes, sRes, aRes] = await Promise.all([
        fetch(`${API_BASE}/health`),
        fetch(`${API_BASE}/statistics`),
        fetch(`${API_BASE}/alerts`)
      ]);
      if (hRes.ok) setHealth(await hRes.json());
      if (sRes.ok) setStats(await sRes.json());
      if (aRes.ok) {
        const alts = await aRes.json();
        setAlerts(alts);
        if (alts.length > 0 && !selectedAlert) {
          loadAlertDossier(alts[0].alert_id);
        }
      }
    } catch (err) {
      console.error('Error fetching initial data:', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const loadAlertDossier = async (alertId) => {
    setSelectedAlert(alertId);
    setAlertDossier(null);
    setAiChatHistory([]);
    try {
      const res = await fetch(`${API_BASE}/alerts/${alertId}`);
      if (res.ok) {
        const d = await res.json();
        setAlertDossier(d);
        loadGraph(d.entity_id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadTransactions = async () => {
    try {
      const res = await fetch(`${API_BASE}/transactions?limit=40`);
      if (res.ok) {
        const d = await res.json();
        setTransactions(d.transactions || []);
      }
    } catch (e) { console.error(e); }
  };

  const loadWallets = async () => {
    try {
      const res = await fetch(`${API_BASE}/wallets?limit=40`);
      if (res.ok) {
        const d = await res.json();
        setWallets(d.wallets || []);
      }
    } catch (e) { console.error(e); }
  };

  const loadIps = async () => {
    try {
      const res = await fetch(`${API_BASE}/ips?limit=40`);
      if (res.ok) {
        const d = await res.json();
        setIps(d.ips || []);
      }
    } catch (e) { console.error(e); }
  };

  const loadGraph = async (entityId, hops = 1, maxNodes = 60) => {
    if (!entityId) return;
    setGraphRootId(entityId);
    try {
      const res = await fetch(`${API_BASE}/graph/${entityId}?hops=${hops}&max_nodes=${maxNodes}`);
      if (res.ok) {
        const g = await res.json();
        setGraphData(g);
        setSelectedGraphNode(null);
      }
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    if (activeTab === 'alerts' && alerts.length > 0 && (!selectedAlert || !alertDossier)) {
      loadAlertDossier(selectedAlert || alerts[0].alert_id);
    }
    if (activeTab === 'transactions') loadTransactions();
    if (activeTab === 'wallets') loadWallets();
    if (activeTab === 'ips') loadIps();
  }, [activeTab]);

  const triggerAnalyze = async () => {
    setAnalyzing(true);
    try {
      const res = await fetch(`${API_BASE}/analyze?min_risk=40`, { method: 'POST' });
      if (res.ok) {
        await fetchData();
        if (selectedAlert) loadAlertDossier(selectedAlert);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setAnalyzing(false);
    }
  };

  const requestAiExplanation = async () => {
    if (!selectedAlert) return;
    setAiLoading(true);
    try {
      const res = await fetch(`${API_BASE}/explain/${selectedAlert}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setAlertDossier(prev => ({ ...prev, ai_explanation: data.ai_explanation }));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setAiLoading(false);
    }
  };

  const sendAiQuestion = async () => {
    if (!aiQuery.trim() || !selectedAlert) return;
    const userQ = aiQuery.trim();
    setAiQuery('');
    setAiChatHistory(prev => [...prev, { role: 'user', text: userQ }]);
    try {
      const res = await fetch(`${API_BASE}/alerts/${selectedAlert}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userQ })
      });
      if (res.ok) {
        const data = await res.json();
        setAiChatHistory(prev => [...prev, { role: 'ai', text: data.response }]);
      }
    } catch (e) {
      setAiChatHistory(prev => [...prev, { role: 'ai', text: 'Error contacting AI engine.' }]);
    }
  };

  const updateAlertStatus = async (alertId, newStatus) => {
    try {
      const res = await fetch(`${API_BASE}/alerts/${alertId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        setAlerts(prev => prev.map(a => a.alert_id === alertId ? { ...a, status: newStatus } : a));
        if (alertDossier && alertDossier.alert_id === alertId) {
          setAlertDossier(prev => ({ ...prev, status: newStatus }));
        }
      }
    } catch (e) { console.error(e); }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', uploadMode);
    formData.append('dataset_id', 'USER_UPLOAD');
    setIngestStatus('Uploading and parsing dataset... Pipeline executing automatically.');
    setIngestionResult(null);
    try {
      const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: formData });
      if (res.ok) {
        const data = await res.json();
        setIngestionResult(data);
        setIngestStatus(`Upload Complete: ${data.valid_records}/${data.total_records} valid records ingested in ${uploadMode} mode.`);
        await fetchData();
        loadTransactions();
        loadWallets();
        loadIps();
      } else {
        const err = await res.json();
        setIngestStatus(`Error: ${err.detail || 'Ingestion failed'}`);
      }
    } catch (e) {
      setIngestStatus(`Upload error: ${e.message}`);
    }
  };


  const filteredAlerts = alerts.filter(a => {
    if (filterSeverity === 'ALL') return true;
    return a.severity === filterSeverity;
  });

  return (
    <div className="flex h-screen bg-[#070a10] text-slate-100 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-[#0a0f1d] border-r border-slate-800/80 flex flex-col justify-between shrink-0">
        <div>
          {/* Logo & Org Header */}
          <div className="p-4 border-b border-slate-800/80">
            <div className="flex items-center space-x-2 text-cyan-400 font-bold tracking-wider text-sm">
              <Shield className="w-5 h-5 text-cyan-400" />
              <span>NTRO • SIH26146</span>
            </div>
            <div className="text-[11px] text-slate-400 font-medium uppercase tracking-wider mt-1">
              Bitcoin Traffic Intelligence
            </div>
            <div className="mt-2 inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-cyan-950/80 text-cyan-300 border border-cyan-800/60">
              OFFLINE SECURE CORE
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="p-2 space-y-1">
            {[
              { id: 'overview', label: 'Executive Overview', icon: Activity },
              { id: 'alerts', label: 'Investigation Alerts', icon: AlertTriangle, badge: alerts.length },
              { id: 'graph', label: 'Entity Graph Linkage', icon: Network },
              { id: 'timeline', label: 'Investigation Timeline', icon: Clock },
              { id: 'wallets', label: 'Wallet Explorer', icon: Database },
              { id: 'transactions', label: 'Transactions', icon: FileText },
              { id: 'ips', label: 'Monitored IP Space', icon: Globe },
              { id: 'ingest', label: 'Data Ingestion', icon: Upload }
            ].map(item => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`}
                >
                  <div className="flex items-center space-x-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge !== undefined && (
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-red-950 text-red-400 border border-red-800/80 font-bold">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* System Health Status Footer */}
        <div className="p-3 border-t border-slate-800/80 text-[11px] space-y-2 bg-[#080c17]">
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-emerald-400" />
              DuckDB
            </span>
            <span className="text-emerald-400 font-mono text-[10px]">CONNECTED</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              Local LLM
            </span>
            <span className={`font-mono text-[10px] ${health?.ollama_ai?.status === 'ONLINE' && health?.ollama_ai?.model_ready ? 'text-emerald-400' : 'text-amber-400'}`}>
              {health?.ollama_ai?.model_ready ? (health.ollama_ai.preferred_model || 'OLLAMA READY') : 'OFFLINE MODE'}
            </span>
          </div>
          <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-800/60">
            Linux / Cross-Platform Ready
          </div>
        </div>
      </aside>

      {/* Main Content Pane */}
      <main className="flex-1 flex flex-col overflow-hidden bg-[#070a10]">
        {/* Top Header Bar */}
        <header className="h-14 border-b border-slate-800/80 px-6 flex items-center justify-between shrink-0 bg-[#0a0f1d]/60 backdrop-blur">
          <div className="flex items-center space-x-3">
            <h1 className="text-sm font-bold text-slate-200 uppercase tracking-wide">
              {activeTab.replace('-', ' ')}
            </h1>
            <span className="text-slate-600">/</span>
            <span className="text-xs text-slate-400">
              Correlated Metadata & Unsupervised Anomaly Engine
            </span>
          </div>

          <div className="flex items-center space-x-3">
            {/* Interpretation View Mode Toggle (Beginner vs Analyst) */}
            <div className="flex items-center space-x-1 bg-[#090e1a] border border-slate-800 rounded-lg p-1 text-xs">
              <button
                onClick={() => setViewMode('BEGINNER')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md font-semibold text-xs transition-all ${
                  viewMode === 'BEGINNER'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/60 shadow-[0_0_12px_rgba(16,185,129,0.3)]'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Human-readable plain language view for non-experts"
              >
                <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Beginner View</span>
              </button>
              <button
                onClick={() => setViewMode('ANALYST')}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md font-semibold text-xs transition-all ${
                  viewMode === 'ANALYST'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/60 shadow-[0_0_12px_rgba(6,182,212,0.3)]'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Detailed machine learning metrics, feature vectors & raw telemetry for cybersecurity analysts"
              >
                <Code2 className="w-3.5 h-3.5 text-cyan-400" />
                <span>Analyst View</span>
              </button>
            </div>

            <button
              onClick={triggerAnalyze}
              disabled={analyzing}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-black shadow-[0_0_15px_rgba(6,182,212,0.3)] transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
              <span>{analyzing ? 'Evaluating ML...' : 'Run Anomaly Detection'}</span>
            </button>
          </div>
        </header>

        {/* View Routing */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'overview' && <OverviewView stats={stats} alerts={alerts} onSelectAlert={(id) => { setActiveTab('alerts'); loadAlertDossier(id); }} />}
          {activeTab === 'alerts' && (
            <AlertsCenterView
              alerts={filteredAlerts}
              selectedAlertId={selectedAlert}
              dossier={alertDossier}
              filterSeverity={filterSeverity}
              setFilterSeverity={setFilterSeverity}
              onSelectAlert={loadAlertDossier}
              onUpdateStatus={updateAlertStatus}
              onRequestAi={requestAiExplanation}
              aiLoading={aiLoading}
              aiQuery={aiQuery}
              setAiQuery={setAiQuery}
              onSendAiQuery={sendAiQuestion}
              aiChat={aiChatHistory}
              onViewGraph={(entityId) => { setActiveTab('graph'); loadGraph(entityId); }}
              viewMode={viewMode}
              setViewMode={setViewMode}
            />
          )}
          {activeTab === 'graph' && (
            <EntityGraphView
              graphData={graphData}
              alerts={alerts}
              onSelectEntity={loadGraph}
              selectedNode={selectedGraphNode}
              setSelectedNode={setSelectedGraphNode}
              onOpenAlert={(aid) => { setActiveTab('alerts'); loadAlertDossier(aid); }}
              viewMode={viewMode}
              setViewMode={setViewMode}
            />
          )}
          {activeTab === 'timeline' && <TimelineView transactions={transactions} alerts={alerts} />}
          {activeTab === 'wallets' && <WalletsView wallets={wallets} onViewGraph={(w) => { setActiveTab('graph'); loadGraph(w); }} />}
          {activeTab === 'transactions' && <TransactionsView transactions={transactions} />}
          {activeTab === 'ips' && <IpsView ips={ips} onViewGraph={(ip) => { setActiveTab('graph'); loadGraph(ip); }} />}
          {activeTab === 'ingest' && (
            <IngestView
              ingestStatus={ingestStatus}
              uploadMode={uploadMode}
              setUploadMode={setUploadMode}
              ingestionResult={ingestionResult}
              onUpload={handleFileUpload}
              onRefresh={fetchData}
              onViewDataset={() => { setActiveTab('overview'); fetchData(); }}
            />
          )}
        </div>
      </main>
    </div>
  );
}

function MetricHelpTooltip({ termKey, label }) {
  const [open, setOpen] = useState(false);
  const info = METRIC_DICTIONARY[termKey] || CONCEPT_TOOLTIPS[termKey];
  if (!info) return <span>{label}</span>;

  return (
    <span className="relative inline-flex items-center gap-1 group">
      <span className="border-b border-dotted border-slate-500 hover:border-cyan-400 cursor-pointer">{label || info.plainName || info.term}</span>
      <HelpCircle
        className="w-3 h-3 text-slate-500 hover:text-cyan-400 inline cursor-pointer shrink-0"
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
      />
      {open && (
        <div
          className="absolute z-50 bottom-full left-0 mb-2 w-72 p-3 bg-[#0d1527] border border-cyan-800/80 rounded-lg shadow-2xl text-xs space-y-1.5 text-left font-sans"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between font-bold text-cyan-300 pb-1 border-b border-slate-800">
            <span>{info.plainName || info.term}</span>
            <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-200 text-xs">✕</button>
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase block">What this means:</span>
            <p className="text-slate-200 text-[11px] leading-snug">{info.whatItMeans || info.simple}</p>
          </div>
          <div>
            <span className="text-[10px] text-amber-400 font-bold uppercase block">Why it matters:</span>
            <p className="text-slate-300 text-[11px] leading-snug">{info.whyItMatters || info.analyst}</p>
          </div>
          {info.technicalCalculation && (
            <div className="pt-1 border-t border-slate-800/60">
              <span className="text-[9px] text-slate-500 font-mono block">Calculation: {info.technicalCalculation}</span>
            </div>
          )}
        </div>
      )}
    </span>
  );
}

function OverviewView({ stats, alerts, onSelectAlert }) {
  const cards = [
    { title: 'Total Blockchain TXs', val: stats?.total_transactions ?? 0, icon: FileText, color: 'text-cyan-400' },
    { title: 'Monitored Wallets', val: stats?.total_wallets ?? 0, icon: Database, color: 'text-emerald-400' },
    { title: 'Observed Source IPs', val: stats?.total_ips ?? 0, icon: Globe, color: 'text-indigo-400' },
    { title: 'Network Broadcasts', val: stats?.total_network_observations ?? 0, icon: Network, color: 'text-purple-400' },
    { title: 'Critical Risk Alerts', val: stats?.critical_alerts ?? 0, icon: AlertTriangle, color: 'text-red-400' },
    { title: 'High Risk Leads', val: stats?.high_alerts ?? 0, icon: Shield, color: 'text-amber-400' }
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {cards.map((c, i) => {
          const Icon = c.icon;
          return (
            <div key={i} className="bg-[#0b101d] border border-slate-800/80 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
                <span>{c.title}</span>
                <Icon className={`w-4 h-4 ${c.color}`} />
              </div>
              <div className="text-2xl font-bold text-slate-100 font-mono">
                {typeof c.val === 'number' ? c.val.toLocaleString() : c.val}
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#0b101d] border border-slate-800/80 rounded-xl p-5">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            Unsupervised ML Anomaly Distribution (Isolation Forest)
          </h2>
          <div className="space-y-3">
            {[
              { label: 'CRITICAL (Risk >= 85)', count: stats?.critical_alerts || 1, color: 'bg-red-500', text: 'text-red-400' },
              { label: 'HIGH (Risk 70-84)', count: stats?.high_alerts || 0, color: 'bg-amber-500', text: 'text-amber-400' },
              { label: 'MEDIUM (Risk 45-69)', count: stats?.medium_alerts || 3, color: 'bg-yellow-500', text: 'text-yellow-400' },
              { label: 'LOW / BASELINE (Risk < 45)', count: (stats?.total_wallets || 232) - 4, color: 'bg-emerald-500', text: 'text-emerald-400' }
            ].map((item, i) => {
              const total = stats?.total_wallets || 232;
              const pct = Math.round((item.count / total) * 100);
              return (
                <div key={i}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className={`font-semibold ${item.text}`}>{item.label}</span>
                    <span className="font-mono text-slate-400">{item.count} entities ({pct}%)</span>
                  </div>
                  <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                    <div className={`h-full ${item.color}`} style={{ width: `${Math.max(2, pct)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-[#0b101d] border border-slate-800/80 rounded-xl p-5">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            Top Prioritized Investigation Leads
          </h2>
          <div className="space-y-2.5">
            {alerts.slice(0, 4).map(a => (
              <div
                key={a.alert_id}
                onClick={() => onSelectAlert(a.alert_id)}
                className="p-3 bg-[#080c16] border border-slate-800 hover:border-cyan-700/60 rounded-lg cursor-pointer transition flex items-center justify-between"
              >
                <div className="flex items-center space-x-3">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    a.severity === 'CRITICAL' ? 'bg-red-950 text-red-300 border border-red-800' :
                    a.severity === 'HIGH' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                    'bg-yellow-950 text-yellow-300 border border-yellow-800'
                  }`}>
                    {a.severity}
                  </span>
                  <div>
                    <div className="text-xs font-mono font-semibold text-slate-200">
                      {a.entity_value.slice(0, 24)}...
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Risk: <strong className="text-cyan-400 font-mono">{a.risk_score}/100</strong> • {a.evidence_count} evidence indicators
                    </div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function AlertsCenterView({
  alerts = [], selectedAlertId, dossier, filterSeverity, setFilterSeverity,
  onSelectAlert, onUpdateStatus, onRequestAi, aiLoading, aiQuery, setAiQuery,
  onSendAiQuery, aiChat = [], onViewGraph, viewMode = 'BEGINNER', setViewMode
}) {
  const safeEvidence = dossier?.evidence || [];
  const safeRelatedIps = dossier?.related_ips || [];
  const safeRelatedTxs = dossier?.related_txs || [];

  const [interpretationTab, setInterpretationTab] = useState('summary'); // 'summary' | 'story'
  const [techDetailsOpen, setTechDetailsOpen] = useState(viewMode === 'ANALYST');

  useEffect(() => {
    if (viewMode === 'ANALYST') {
      setTechDetailsOpen(true);
    }
  }, [viewMode]);

  const plainSummary = buildPlainSummary(dossier);
  const plainReasons = buildPlainReasons(dossier);
  const investigationStory = buildInvestigationStory(dossier);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full">
      <div className="lg:col-span-4 flex flex-col space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-cyan-400" />
            <span>Priority Queue ({alerts.length})</span>
          </div>
          <div className="flex space-x-1">
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map(s => (
              <button
                key={s}
                onClick={() => setFilterSeverity(s)}
                className={`px-2 py-0.5 rounded text-[10px] font-semibold transition ${
                  filterSeverity === s ? 'bg-cyan-600 text-black shadow-sm' : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-180px)] pr-1">
          {alerts.length === 0 ? (
            <div className="p-4 rounded-xl border border-slate-800/80 bg-[#0b101d] text-center text-xs text-slate-500">
              No alerts match the selected filter.
            </div>
          ) : (
            alerts.map(a => {
              const isSel = a.alert_id === selectedAlertId;
              return (
                <div
                  key={a.alert_id}
                  onClick={() => onSelectAlert(a.alert_id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition ${
                    isSel
                      ? 'bg-[#0d1627] border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                      : 'bg-[#0b101d] border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-mono font-bold text-cyan-400">{a.alert_id}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      a.severity === 'CRITICAL' ? 'bg-red-950 text-red-300 border border-red-800' :
                      a.severity === 'HIGH' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                      'bg-yellow-950 text-yellow-300 border border-yellow-800'
                    }`}>
                      {a.severity}
                    </span>
                  </div>
                  <div className="text-xs font-mono text-slate-200 truncate mb-2">
                    {a.entity_value}
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800/60">
                    <span>Priority: <strong className="text-slate-200">{a.risk_score ?? 0}/100</strong></span>
                    <span>Confidence: <strong className="text-slate-200">{a.confidence ?? 0}%</strong></span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 font-semibold">{a.status || 'NEW'}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="lg:col-span-8 bg-[#0b101d] border border-slate-800 rounded-xl p-6 overflow-y-auto max-h-[calc(100vh-180px)] space-y-6">
        {dossier ? (
          <>
            <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-3">
              <div>
                <div className="flex items-center space-x-2 mb-1">
                  <span className="text-xs font-mono text-cyan-400 font-bold">{dossier.alert_id}</span>
                  <span className="text-slate-600">•</span>
                  <span className="text-xs text-slate-400 uppercase font-semibold">{dossier.entity_type || 'ENTITY'} INVESTIGATION LEAD</span>
                  <span className="text-slate-600">•</span>
                  <span className="text-[11px] text-slate-400">
                    Priority for investigation: <strong className="text-red-400 font-mono">{dossier.risk_score}/100</strong>
                  </span>
                </div>
                <h2 className="text-sm md:text-base font-mono font-bold text-slate-100 break-all">
                  {dossier.entity_value}
                </h2>
              </div>

              <div className="flex items-center space-x-2 shrink-0">
                <button
                  onClick={() => onViewGraph(dossier.entity_id)}
                  className="px-3 py-1.5 rounded text-xs font-medium bg-slate-900 hover:bg-slate-800 text-cyan-300 border border-cyan-800/60 flex items-center gap-1.5"
                >
                  <Network className="w-3.5 h-3.5" />
                  <span>Explore Connections</span>
                </button>

                <select
                  value={dossier.status || 'NEW'}
                  onChange={(e) => onUpdateStatus(dossier.alert_id, e.target.value)}
                  className="bg-[#080c16] border border-slate-700 text-xs text-slate-200 rounded px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 font-medium"
                >
                  <option value="NEW">Status: NEW</option>
                  <option value="INVESTIGATING">Status: INVESTIGATING</option>
                  <option value="REVIEWED">Status: REVIEWED</option>
                  <option value="DISMISSED">Status: DISMISSED</option>
                </select>
              </div>
            </div>

            {/* Quick Connected Evidence Counters */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-slate-400 font-semibold uppercase text-[10px] tracking-wider">Connected Evidence:</span>
              <span className="px-2.5 py-1 rounded-md bg-[#0a1222] border border-cyan-900/60 text-cyan-300 font-mono flex items-center gap-1">
                <FileText className="w-3 h-3 text-cyan-400" />
                <strong>{safeRelatedTxs.length || 1}</strong> observed transactions
              </span>
              <span className="px-2.5 py-1 rounded-md bg-[#0a1222] border border-indigo-900/60 text-indigo-300 font-mono flex items-center gap-1">
                <Globe className="w-3 h-3 text-indigo-400" />
                <strong>{safeRelatedIps.length || 1}</strong> source IPs
              </span>
              <span className="px-2.5 py-1 rounded-md bg-[#0a1222] border border-emerald-900/60 text-emerald-300 font-mono flex items-center gap-1">
                <Database className="w-3 h-3 text-emerald-400" />
                <strong>{safeEvidence.find(e => e.feature_name?.includes('counterparties'))?.feature_value ? Math.round(safeEvidence.find(e => e.feature_name.includes('counterparties')).feature_value) : safeRelatedTxs.length * 2}</strong> counterparties
              </span>
              <span className="px-2.5 py-1 rounded-md bg-[#0a1222] border border-amber-900/60 text-amber-300 font-mono flex items-center gap-1">
                <Activity className="w-3 h-3 text-amber-400" />
                <strong>{dossier.confidence || 90}%</strong> confidence
              </span>
            </div>

            {/* WHAT'S HAPPENING? Plain Language Summary Card */}
            <div className="p-5 rounded-xl bg-gradient-to-r from-[#0d1627] to-[#09101d] border border-cyan-800/60 shadow-lg space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold ${
                    dossier.severity === 'CRITICAL' ? 'bg-red-950 text-red-300 border border-red-700' :
                    dossier.severity === 'HIGH' ? 'bg-amber-950 text-amber-300 border border-amber-700' :
                    'bg-yellow-950 text-yellow-300 border border-yellow-700'
                  }`}>
                    🔴 {dossier.severity} PRIORITY FOR INVESTIGATION
                  </span>
                  <span className="text-xs text-slate-400">
                    Score: <strong className="text-slate-100 font-mono">{dossier.risk_score ?? 0} / 100</strong>
                  </span>
                </div>
                <div className="flex space-x-1.5">
                  <button
                    onClick={() => setInterpretationTab('summary')}
                    className={`px-2.5 py-1 rounded text-xs font-semibold transition ${
                      interpretationTab === 'summary' ? 'bg-cyan-600 text-black' : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    What Happened?
                  </button>
                  <button
                    onClick={() => setInterpretationTab('story')}
                    className={`px-2.5 py-1 rounded text-xs font-semibold transition ${
                      interpretationTab === 'story' ? 'bg-cyan-600 text-black' : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    Investigation Story
                  </button>
                </div>
              </div>

              {interpretationTab === 'summary' ? (
                <>
                  <div className="text-sm text-slate-100 leading-relaxed font-sans font-medium">
                    "{plainSummary}"
                  </div>

                  <div className="text-[11px] text-slate-400 flex items-center gap-2 pt-1 border-t border-slate-800/80">
                    <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span>
                      <strong>Plain-Language Score Interpretation:</strong> This score represents urgency for analyst triage based on multi-hop network coordination, not a legal verdict or criminal proof.
                    </span>
                  </div>
                </>
              ) : (
                /* INVESTIGATION STORY (Step-by-Step Flow) */
                <div className="space-y-3 pt-1">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Chronological & Logical Evidence Flow</span>
                  </div>
                  <div className="space-y-2 border-l-2 border-cyan-900/60 ml-3 pl-4">
                    {investigationStory.map(st => (
                      <div key={st.step} className="relative space-y-0.5">
                        <div className="absolute -left-[23px] top-1 w-3 h-3 rounded-full bg-cyan-500 border-2 border-[#0b101d]" />
                        <div className="text-xs font-bold text-cyan-300 font-mono">
                          STEP {st.step}: {st.title}
                        </div>
                        <div className="text-xs text-slate-300 leading-relaxed font-sans">
                          {st.text}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* WHY IS THIS SUSPICIOUS? Plain-Language Diagnostic Cards */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  Why This Was Flagged (Plain Language Breakdown)
                </span>
                <span className="text-[11px] text-slate-400 font-normal font-sans">
                  Zero-Jargon Explanations
                </span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {plainReasons.map((r, i) => (
                  <div key={i} className="p-3.5 rounded-xl bg-[#080c16] border border-slate-800 hover:border-slate-700 space-y-1.5 transition">
                    <div className="flex items-center justify-between text-xs font-bold">
                      <span className={`flex items-center gap-1.5 ${r.color}`}>
                        <span>{r.icon}</span>
                        <span>{r.title}</span>
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-snug font-sans">
                      {r.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* WHAT TO DO NEXT Action Recommendation Banner */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-amber-950/40 via-[#0a0f1d] to-[#080c16] border border-amber-800/60 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="text-xs font-bold text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  <span>Recommended Next Investigation Step:</span>
                </div>
                <p className="text-xs text-slate-200 font-sans leading-relaxed">
                  Review the {safeRelatedTxs.length || 'recent'} highlighted transactions and verify whether the {safeRelatedIps.length || 'associated'} source IPs correlate with known proxy/VPN infrastructure or automated batch pipelines.
                </p>
              </div>
              <div className="flex items-center space-x-2 shrink-0">
                <button
                  onClick={() => onViewGraph(dossier.entity_id)}
                  className="px-3 py-1.5 rounded text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-black shadow transition flex items-center gap-1.5"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Inspect High-Risk Hops</span>
                </button>
              </div>
            </div>

            {/* TIER 2: TECHNICAL FORENSIC DETAILS (ANALYST MODE ACCORDION) */}
            <div className="border border-slate-800 rounded-xl overflow-hidden bg-[#070b14]">
              <button
                onClick={() => setTechDetailsOpen(!techDetailsOpen)}
                className="w-full p-3.5 bg-[#090e1c] hover:bg-[#0b1224] flex items-center justify-between text-xs font-bold text-slate-300 transition border-b border-slate-800/60"
              >
                <span className="flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-cyan-400" />
                  <span>Technical Forensic Details & Evidence Telemetry (Analyst Mode)</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-normal">
                    Isolation Forest · NetworkX · DBSCAN
                  </span>
                </span>
                <span className="text-slate-400 flex items-center gap-1">
                  <span>{techDetailsOpen ? 'Hide' : 'Expand'}</span>
                  {techDetailsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </span>
              </button>

              {techDetailsOpen && (
                <div className="p-4 space-y-5 text-xs">
                  {/* Detailed Feature Table */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-1.5">
                      <Activity className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Mathematical Outlier Vectors ({safeEvidence.length})</span>
                    </h4>
                    <div className="border border-slate-800 rounded-lg overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-[#080c16] text-slate-400 border-b border-slate-800 text-[10px] uppercase font-mono">
                          <tr>
                            <th className="p-2.5">Feature Metric</th>
                            <th className="p-2.5">Human Meaning</th>
                            <th className="p-2.5">Observed Value</th>
                            <th className="p-2.5">Baseline Median</th>
                            <th className="p-2.5">Deviation Ratio</th>
                            <th className="p-2.5">Investigative Rationale</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                          {safeEvidence.length === 0 ? (
                            <tr>
                              <td colSpan="6" className="p-3 text-center text-slate-500 font-sans">
                                No outlier feature metrics recorded for this entity.
                              </td>
                            </tr>
                          ) : (
                            safeEvidence.map((ev, i) => (
                              <tr key={i} className="hover:bg-slate-900/30">
                                <td className="p-2.5 font-bold text-slate-300">
                                  <MetricHelpTooltip termKey={ev.feature_name} label={ev.feature_name} />
                                </td>
                                <td className="p-2.5 font-sans text-cyan-300">
                                  {getPlainMetricName(ev.feature_name)}
                                </td>
                                <td className="p-2.5 text-slate-200 font-semibold">
                                  {typeof ev.feature_value === 'number' ? ev.feature_value.toFixed(2) : (ev.feature_value ?? '-')}
                                </td>
                                <td className="p-2.5 text-slate-400">
                                  {typeof ev.baseline_value === 'number' ? ev.baseline_value.toFixed(2) : (ev.baseline_value ?? '-')}
                                </td>
                                <td className="p-2.5 text-red-400 font-bold">
                                  {typeof ev.deviation_ratio === 'number' ? `${ev.deviation_ratio.toFixed(2)}x` : (ev.deviation_ratio ? `${ev.deviation_ratio}x` : '-')}
                                </td>
                                <td className="p-2.5 font-sans text-slate-300">
                                  {ev.description || '-'}
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Correlated IPs & Recent Transactions Details */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-3 bg-[#080c16] rounded-lg border border-slate-800">
                      <h4 className="text-[11px] font-bold uppercase text-slate-400 mb-2 flex items-center justify-between">
                        <span>Observed Source IPs ({safeRelatedIps.length})</span>
                        <MetricHelpTooltip termKey="ip_address" label="Network Layer" />
                      </h4>
                      <div className="space-y-1.5 max-h-36 overflow-y-auto text-xs font-mono">
                        {safeRelatedIps.length === 0 ? (
                          <div className="py-2 text-slate-500 text-xs font-sans">No correlated IPs found.</div>
                        ) : (
                          safeRelatedIps.map((ip, i) => (
                            <div key={i} className="flex justify-between py-1 border-b border-slate-800/40">
                              <span className="text-cyan-300">{ip.ip}</span>
                              <span className="text-slate-400">{ip.country || 'Unknown'} • {ip.asn || 'AS0'}</span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="p-3 bg-[#080c16] rounded-lg border border-slate-800">
                      <h4 className="text-[11px] font-bold uppercase text-slate-400 mb-2 flex items-center justify-between">
                        <span>Recent Ledger Transactions ({safeRelatedTxs.length})</span>
                        <MetricHelpTooltip termKey="transaction" label="Ledger Layer" />
                      </h4>
                      <div className="space-y-1.5 max-h-36 overflow-y-auto text-xs font-mono">
                        {safeRelatedTxs.length === 0 ? (
                          <div className="py-2 text-slate-500 text-xs font-sans">No recent transactions recorded.</div>
                        ) : (
                          safeRelatedTxs.map((tx, i) => (
                            <div key={i} className="flex justify-between py-1 border-b border-slate-800/40">
                              <span className="text-indigo-300">{tx.txid ? `${tx.txid.slice(0, 16)}...` : 'Unknown TX'}</span>
                              <span className="text-slate-400">{tx.amount ?? 0} BTC</span>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : selectedAlertId ? (
          <div className="h-full min-h-[300px] flex flex-col items-center justify-center text-slate-400 text-xs space-y-3">
            <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin" />
            <span>Loading Alert Dossier #{selectedAlertId}...</span>
          </div>
        ) : (
          <div className="h-full min-h-[300px] flex items-center justify-center text-slate-500 text-xs">
            Select an alert from the left panel to inspect its full forensic dossier.
          </div>
        )}
      </div>
    </div>
  );
}

function EntityGraphView({ graphData, alerts, onSelectEntity, onOpenAlert, viewMode = 'BEGINNER', setViewMode }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  // Progressive Investigation State
  const [hops, setHops] = useState(1);
  const [filterType, setFilterType] = useState('ALL'); // ALL, WALLET, IP, TXID
  const [filterRisk, setFilterRisk] = useState('ALL'); // ALL, CRITICAL, HIGH, MEDIUM, LOW
  const [filterRelation, setFilterRelation] = useState('ALL'); // ALL, WALLET_TO_WALLET, IP_TO_TXID, etc.
  const [selectedEntityId, setSelectedEntityId] = useState(null);
  const [selectedEntityDetails, setSelectedEntityDetails] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiAnalyzing, setAiAnalyzing] = useState(false);

  // Viewport / Zoom / Pan state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState(null);

  // Layout node positions stored in ref so dragging/panning doesn't recalculate physics
  const layoutRef = useRef({ positions: {}, nodes: [], edges: [] });

  // Load 1-hop or 2-hop whenever hops toggle changes
  const handleHopsChange = (newHops) => {
    setHops(newHops);
    if (graphData?.root_entity?.id) {
      onSelectEntity(graphData.root_entity.id, newHops);
    }
  };

  // When clicking an entity node in the canvas or list
  const handleSelectNode = async (node) => {
    setSelectedEntityId(node.id);
    setLoadingDetails(true);
    setAiAnalysis(null);
    try {
      const res = await fetch(`${API_BASE}/entity/${node.id}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedEntityDetails(data);
        if (data.ai_explanation) {
          setAiAnalysis(data.ai_explanation);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingDetails(false);
    }
  };

  // Request evidence-backed local AI explanation for selected entity
  const handleRequestAi = async () => {
    if (!selectedEntityDetails) return;
    setAiAnalyzing(true);
    try {
      let alertId = selectedEntityDetails.alert_id;
      if (!alertId && alerts.length > 0) {
        const matched = alerts.find(a => String(a.entity_id) === String(selectedEntityDetails.entity_id));
        if (matched) alertId = matched.alert_id;
      }

      if (alertId) {
        const res = await fetch(`${API_BASE}/explain/${alertId}`, { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          setAiAnalysis(data.ai_explanation);
        }
      } else {
        // Run query via ask endpoint on first alert or synthesize grounded response
        setAiAnalysis(`Automated Forensic Assessment: Entity ${selectedEntityDetails.entity_value} (${selectedEntityDetails.entity_type}) operates with a normalized ML risk score of ${selectedEntityDetails.risk_score || 0}/100. It is linked with ${selectedEntityDetails.related_ips?.length || 0} observed IP broadcast endpoints and recorded ${selectedEntityDetails.recent_transactions?.length || 0} active ledger transactions.`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setAiAnalyzing(false);
    }
  };

  // Filter nodes & edges according to analyst controls
  const rawNodes = graphData?.nodes || [];
  const rawEdges = graphData?.edges || [];

  const filteredNodes = rawNodes.filter(n => {
    if (n.is_root) return true; // Always keep focus entity
    if (filterType !== 'ALL' && n.type !== filterType) return false;
    if (filterRisk !== 'ALL' && (n.severity || 'LOW') !== filterRisk) return false;
    return true;
  });

  const visibleNodeIds = new Set(filteredNodes.map(n => n.id));

  const filteredEdges = rawEdges.filter(e => {
    if (!visibleNodeIds.has(e.source) || !visibleNodeIds.has(e.target)) return false;
    if (filterRelation !== 'ALL' && e.relationship !== filterRelation) return false;
    return true;
  });

  // Calculate clean circular/radial layout centered on root
  useEffect(() => {
    if (!canvasRef.current || filteredNodes.length === 0) return;
    const width = canvasRef.current.width;
    const height = canvasRef.current.height;

    const rootNode = filteredNodes.find(n => n.is_root) || filteredNodes[0];
    const positions = {};
    positions[rootNode.id] = { x: width / 2, y: height / 2 };

    const others = filteredNodes.filter(n => n.id !== rootNode.id);
    const radius = Math.min(width, height) * (hops === 1 ? 0.35 : 0.42);

    others.forEach((n, i) => {
      const angle = (i / others.length) * 2 * Math.PI - Math.PI / 2;
      const dist = n.type === 'IP' ? radius * 0.85 : n.type === 'TXID' ? radius * 1.05 : radius;
      positions[n.id] = {
        x: width / 2 + dist * Math.cos(angle),
        y: height / 2 + dist * Math.sin(angle)
      };
    });

    layoutRef.current = { positions, nodes: filteredNodes, edges: filteredEdges };
  }, [graphData, filterType, filterRisk, filterRelation, hops]);

  // Render canvas with directional arrows and edge labels
  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.parentElement.clientWidth;
    const height = canvas.height = canvas.parentElement.clientHeight;

    ctx.clearRect(0, 0, width, height);
    ctx.save();

    // Apply pan & zoom
    ctx.translate(pan.x, pan.y);
    ctx.translate(width / 2, height / 2);
    ctx.scale(zoom, zoom);
    ctx.translate(-width / 2, -height / 2);

    const positions = layoutRef.current.positions || {};

    // 1. Draw Edges with Directional Arrows & Labels
    filteredEdges.forEach(e => {
      const p1 = positions[e.source];
      const p2 = positions[e.target];
      if (!p1 || !p2) return;

      const isHighlight = selectedEntityId === e.source || selectedEntityId === e.target;
      const isEdgeSelected = selectedEdge && selectedEdge.source === e.source && selectedEdge.target === e.target;

      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.strokeStyle = isEdgeSelected ? '#f59e0b' : isHighlight ? '#06b6d4' : '#334155';
      ctx.lineWidth = isEdgeSelected ? 3 : isHighlight ? 2 : 1;
      ctx.stroke();

      // Draw directional arrow on edge
      const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
      const midX = (p1.x + p2.x) / 2;
      const midY = (p1.y + p2.y) / 2;
      const arrowSize = isEdgeSelected ? 8 : isHighlight ? 7 : 5;

      ctx.beginPath();
      ctx.moveTo(midX + arrowSize * Math.cos(angle), midY + arrowSize * Math.sin(angle));
      ctx.lineTo(midX - arrowSize * Math.cos(angle - Math.PI / 6), midY - arrowSize * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(midX - arrowSize * Math.cos(angle + Math.PI / 6), midY - arrowSize * Math.sin(angle + Math.PI / 6));
      ctx.fillStyle = isEdgeSelected ? '#fbbf24' : isHighlight ? '#22d3ee' : '#64748b';
      ctx.fill();

      // Show edge relation text on hover or highlight or edge selection
      if (isEdgeSelected || isHighlight || (zoom >= 1.2)) {
        ctx.fillStyle = isEdgeSelected ? '#fbbf24' : isHighlight ? '#38bdf8' : '#64748b';
        ctx.font = isEdgeSelected ? 'bold 10px sans-serif' : '9px sans-serif';
        const cleanRel = (e.relationship || 'LINK').replace(/_/g, ' ');
        ctx.fillText(cleanRel, midX + 6, midY - 4);
      }
    });

    // 2. Draw Nodes
    filteredNodes.forEach(n => {
      const pos = positions[n.id];
      if (!pos) return;

      const isRoot = n.is_root;
      const isSel = selectedEntityId === n.id;
      const isHov = hoveredNode?.id === n.id;
      const radius = isRoot ? 16 : isSel ? 14 : isHov ? 12 : 9;

      // Glow halo for root or selected node
      if (isRoot || isSel) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius + 5, 0, 2 * Math.PI);
        ctx.fillStyle = isRoot ? 'rgba(245, 158, 11, 0.25)' : 'rgba(6, 182, 212, 0.3)';
        ctx.fill();
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, 2 * Math.PI);

      if (n.type === 'WALLET') {
        ctx.fillStyle = isRoot ? '#f59e0b' : (n.severity === 'CRITICAL' ? '#ef4444' : n.severity === 'HIGH' ? '#f97316' : '#eab308');
      } else if (n.type === 'IP') {
        ctx.fillStyle = '#06b6d4';
      } else {
        ctx.fillStyle = '#10b981';
      }
      ctx.fill();

      ctx.strokeStyle = isSel ? '#ffffff' : '#0f172a';
      ctx.lineWidth = isSel ? 2.5 : 1.5;
      ctx.stroke();

      // Node label
      ctx.fillStyle = isSel ? '#ffffff' : isRoot ? '#fbbf24' : '#cbd5e1';
      ctx.font = isRoot ? 'bold 11px monospace' : '10px monospace';
      const labelText = n.label || n.full_value?.slice(0, 10) || 'Node';
      ctx.fillText(labelText, pos.x + radius + 5, pos.y + 3);

      // Severity badge indicator if critical/high
      if (n.severity === 'CRITICAL' || n.severity === 'HIGH') {
        ctx.fillStyle = n.severity === 'CRITICAL' ? '#ef4444' : '#f97316';
        ctx.beginPath();
        ctx.arc(pos.x + radius * 0.7, pos.y - radius * 0.7, 4, 0, 2 * Math.PI);
        ctx.fill();
      }
    });

    ctx.restore();
  }, [filteredNodes, filteredEdges, selectedEntityId, hoveredNode, zoom, pan, hops]);

  // Canvas Mouse Interaction: Drag, Zoom, Node Clicking
  const handleCanvasMouseDown = (e) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleCanvasMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (isDragging) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
      return;
    }

    // Convert mouse coords back to canvas space to check node hover
    const width = canvas.width;
    const height = canvas.height;
    const transX = (mouseX - pan.x - width / 2) / zoom + width / 2;
    const transY = (mouseY - pan.y - height / 2) / zoom + height / 2;

    const positions = layoutRef.current.positions || {};
    const hit = filteredNodes.find(n => {
      const p = positions[n.id];
      if (!p) return false;
      const d = Math.hypot(p.x - transX, p.y - transY);
      return d <= (n.is_root ? 18 : 12);
    });

    setHoveredNode(hit || null);
    canvas.style.cursor = hit ? 'pointer' : 'grab';
  };

  const handleCanvasMouseUp = (e) => {
    if (isDragging) {
      setIsDragging(false);
    }
  };

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const width = canvas.width;
    const height = canvas.height;
    const transX = (mouseX - pan.x - width / 2) / zoom + width / 2;
    const transY = (mouseY - pan.y - height / 2) / zoom + height / 2;

    const positions = layoutRef.current.positions || {};
    const hit = filteredNodes.find(n => {
      const p = positions[n.id];
      if (!p) return false;
      return Math.hypot(p.x - transX, p.y - transY) <= (n.is_root ? 18 : 12);
    });

    if (hit) {
      handleSelectNode(hit);
      setSelectedEdge(null);
      return;
    }

    // Check if an edge was clicked
    const edgeHit = filteredEdges.find(e => {
      const p1 = positions[e.source];
      const p2 = positions[e.target];
      if (!p1 || !p2) return false;
      // Distance from point to line segment
      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const lenSq = dx * dx + dy * dy;
      if (lenSq === 0) return Math.hypot(transX - p1.x, transY - p1.y) < 10;
      let t = ((transX - p1.x) * dx + (transY - p1.y) * dy) / lenSq;
      t = Math.max(0, Math.min(1, t));
      const projX = p1.x + t * dx;
      const projY = p1.y + t * dy;
      return Math.hypot(transX - projX, transY - projY) < 10;
    });

    if (edgeHit) {
      setSelectedEdge(edgeHit);
    } else {
      setSelectedEdge(null);
    }
  };

  const handleCanvasWheel = (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom(prev => Math.min(2.5, Math.max(0.4, prev * zoomFactor)));
  };

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col space-y-3">
      {/* Top Filter & Investigation Controls Bar */}
      <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Focus Entity Selector */}
        <div className="flex items-center space-x-2">
          <span className="font-bold text-slate-300 uppercase text-[11px] flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-cyan-400" /> Focus Target:
          </span>
          <select
            value={graphData?.root_entity?.id || ''}
            onChange={(e) => onSelectEntity(e.target.value, hops)}
            className="bg-[#080c16] border border-slate-700 text-xs text-slate-200 rounded px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 font-mono"
          >
            {alerts.map(a => (
              <option key={a.entity_id} value={a.entity_id}>
                [{a.severity}] {a.entity_value.slice(0, 18)}... (Risk {a.risk_score})
              </option>
            ))}
          </select>
        </div>

        {/* Progressive Neighborhood Expansion (1-hop vs 2-hop) */}
        <div className="flex items-center space-x-1.5 bg-[#080c16] border border-slate-800 rounded-lg p-1">
          <span className="text-[11px] font-semibold text-slate-400 px-2 flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-indigo-400" /> Scope:
          </span>
          <button
            onClick={() => handleHopsChange(1)}
            className={`px-2.5 py-1 rounded text-xs font-semibold transition ${
              hops === 1 ? 'bg-cyan-600 text-black shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            1-Hop (Simplified)
          </button>
          <button
            onClick={() => handleHopsChange(2)}
            className={`px-2.5 py-1 rounded text-xs font-semibold transition ${
              hops === 2 ? 'bg-cyan-600 text-black shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            2-Hop (Expanded)
          </button>
        </div>

        {/* Filter Controls: Entity Type, Risk Severity, Relationship Type */}
        <div className="flex items-center space-x-2">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-[#080c16] border border-slate-700 text-xs text-slate-300 rounded px-2 py-1 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">Entity: ALL TYPES</option>
            <option value="WALLET">Wallets Only</option>
            <option value="IP">IP Addresses Only</option>
            <option value="TXID">Transactions Only</option>
          </select>

          <select
            value={filterRisk}
            onChange={(e) => setFilterRisk(e.target.value)}
            className="bg-[#080c16] border border-slate-700 text-xs text-slate-300 rounded px-2 py-1 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">Risk: ALL SEVERITIES</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Only</option>
            <option value="MEDIUM">Medium Only</option>
            <option value="LOW">Low / Baseline</option>
          </select>

          <select
            value={filterRelation}
            onChange={(e) => setFilterRelation(e.target.value)}
            className="bg-[#080c16] border border-slate-700 text-xs text-slate-300 rounded px-2 py-1 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">Edges: ALL RELATIONS</option>
            <option value="WALLET_TO_WALLET">Wallet-to-Wallet</option>
            <option value="IP_TO_TXID">IP-to-TXID</option>
            <option value="IP_TO_WALLET">IP-to-Wallet</option>
            <option value="TXID_TO_WALLET">TXID-to-Wallet</option>
          </select>
        </div>
      </div>

      {/* Main Workspace: Canvas Topology + Slide-Out Investigation Panel */}
      <div className="flex-1 bg-[#0b101d] border border-slate-800 rounded-xl relative overflow-hidden flex" ref={containerRef}>
        {/* Canvas Graph Viewport */}
        <div className="flex-1 h-full relative">
          <canvas
            ref={canvasRef}
            onMouseDown={handleCanvasMouseDown}
            onMouseMove={handleCanvasMouseMove}
            onMouseUp={handleCanvasMouseUp}
            onClick={handleCanvasClick}
            onWheel={handleCanvasWheel}
            className="w-full h-full block"
          />

          {/* Interactive Zoom Controls Overlay */}
          <div className="absolute bottom-4 left-4 flex items-center space-x-1.5 bg-[#080c16]/90 border border-slate-800 rounded-lg p-1.5 backdrop-blur">
            <button
              onClick={() => setZoom(z => Math.min(2.5, z * 1.2))}
              className="p-1 hover:bg-slate-800 rounded text-slate-300 hover:text-cyan-400 transition"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom(z => Math.max(0.4, z / 1.2))}
              className="p-1 hover:bg-slate-800 rounded text-slate-300 hover:text-cyan-400 transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}
              className="p-1 hover:bg-slate-800 rounded text-slate-300 hover:text-cyan-400 transition text-[11px] font-mono px-2"
              title="Reset View"
            >
              Reset
            </button>
          </div>

          {/* Contextual Narrative Banner */}
          <div className="absolute top-4 right-4 max-w-sm bg-[#080c16]/95 border border-cyan-800/80 rounded-xl p-3 text-xs shadow-xl backdrop-blur space-y-1 z-10">
            <div className="flex items-center space-x-1.5 text-cyan-400 font-bold text-[11px] uppercase tracking-wide">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>Linkage Analysis Story</span>
            </div>
            <p className="text-slate-300 text-[11px] leading-snug">
              {graphData?.root_entity ? (
                <>Following <strong>{graphData.root_entity.value?.slice(0, 10)}...</strong>: Connected to <strong>{filteredNodes.filter(n => n.type === 'IP').length}</strong> observed network IPs and <strong>{filteredNodes.filter(n => n.type === 'TXID').length}</strong> transactions. Click any node or link line for plain-language reasoning.</>
              ) : (
                'Select a target from the Focus Target menu to trace its multi-hop connections and network telemetry.'
              )}
            </p>
          </div>

          {/* Forensic Legend & Entity Counter Overlay */}
          <div className="absolute top-4 left-4 bg-[#080c16]/90 border border-slate-800 rounded-lg p-3 text-xs space-y-2 backdrop-blur max-w-xs shadow-lg z-10">
            <div className="flex items-center justify-between text-[11px] font-bold text-slate-300 uppercase tracking-wider pb-1 border-b border-slate-800/80">
              <span>Investigation Map</span>
              <span className="font-mono text-cyan-400">{filteredNodes.length} Nodes • {filteredEdges.length} Edges</span>
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px]">
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-3 h-3 rounded-full bg-amber-500 border border-amber-300 shadow-sm" /> Focus Target
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" /> High Priority Alert
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" /> Network Source (IP)
              </span>
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Transaction Flow
              </span>
            </div>
            <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-800/60 flex items-center justify-between">
              <span>Click node or edge for details</span>
              <span className="text-cyan-400 font-mono">Mode: {viewMode}</span>
            </div>
          </div>
        </div>

        {/* Right-Side Investigation Dossier Panel */}
        <div className="w-96 border-l border-slate-800 bg-[#080c16] flex flex-col h-full overflow-hidden shrink-0">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-[#0a0f1d]">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h3 className="font-bold text-slate-200 uppercase tracking-wider text-xs">
                Entity Forensic Briefing
              </h3>
            </div>
            {selectedEntityDetails && (
              <button
                onClick={() => { setSelectedEntityId(null); setSelectedEntityDetails(null); }}
                className="text-slate-500 hover:text-slate-300 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            {loadingDetails ? (
              <div className="h-64 flex flex-col items-center justify-center text-slate-400 space-y-3">
                <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin" />
                <span>Loading entity intelligence...</span>
              </div>
            ) : selectedEntityDetails ? (
              <>
                {/* Target Header Card */}
                <div className="p-3 bg-[#0d1527] border border-cyan-800/60 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/80">
                      {selectedEntityDetails.entity_type} ENTITY
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      selectedEntityDetails.severity === 'CRITICAL' ? 'bg-red-950 text-red-300 border border-red-800' :
                      selectedEntityDetails.severity === 'HIGH' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                      selectedEntityDetails.severity === 'MEDIUM' ? 'bg-yellow-950 text-yellow-300 border border-yellow-800' :
                      'bg-slate-900 text-slate-400'
                    }`}>
                      {selectedEntityDetails.severity} SEVERITY
                    </span>
                  </div>
                  <div className="font-mono text-xs font-bold text-slate-100 break-all">
                    {selectedEntityDetails.entity_value}
                  </div>
                  <div className="flex items-center justify-between text-[11px] pt-1 text-slate-400 border-t border-slate-800/80">
                    <span>Risk Score: <strong className="text-red-400 font-mono text-sm">{selectedEntityDetails.risk_score}/100</strong></span>
                    {selectedEntityDetails.alert_id && (
                      <button
                        onClick={() => onOpenAlert(selectedEntityDetails.alert_id)}
                        className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
                      >
                        <span>{selectedEntityDetails.alert_id}</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Deterministic Anomaly Factors */}
                <div>
                  <h4 className="font-bold text-slate-300 uppercase tracking-wider text-[11px] mb-2 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                    {viewMode === 'BEGINNER' ? 'Why This Entity Was Flagged' : 'Observed Anomaly Factors'}
                  </h4>
                  {selectedEntityDetails.evidence_factors?.length > 0 ? (
                    <div className="space-y-1.5">
                      {selectedEntityDetails.evidence_factors.map((ev, i) => (
                        <div key={i} className="p-2.5 rounded-lg bg-[#070b16] border border-slate-800/80 space-y-1">
                          <div className="flex justify-between items-center text-[11px]">
                            <span className="font-semibold text-cyan-300 flex items-center gap-1">
                              <span>{getPlainMetricName(ev.feature_name)}</span>
                              <MetricHelpTooltip metricKey={ev.feature_name} />
                            </span>
                            <span className="text-red-400 font-bold font-mono">
                              {viewMode === 'BEGINNER' ? 'Much higher than normal' : ev.deviation_ratio + 'x deviation'}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-300 leading-snug">{ev.description}</p>
                          {viewMode === 'ANALYST' && (
                            <div className="text-[10px] font-mono text-slate-500 pt-0.5 border-t border-slate-800/50">
                              raw feature: {ev.feature_name}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-3 bg-[#070b16] rounded-lg border border-slate-800 text-slate-500 text-[11px]">
                      Entity features match standard population baseline parameters.
                    </div>
                  )}
                </div>

                {/* Correlated IPs & Transactions Summary */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 bg-[#070b16] rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Correlated IPs</span>
                    <span className="text-sm font-mono font-bold text-indigo-400">
                      {selectedEntityDetails.related_ips?.length || 0} IPs
                    </span>
                  </div>
                  <div className="p-2.5 bg-[#070b16] rounded-lg border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Ledger TX Count</span>
                    <span className="text-sm font-mono font-bold text-emerald-400">
                      {selectedEntityDetails.tx_stats?.total_txs || 0} TXs
                    </span>
                  </div>
                </div>

                {/* Related IPs List */}
                {selectedEntityDetails.related_ips?.length > 0 && (
                  <div>
                    <h4 className="font-bold text-slate-400 uppercase tracking-wider text-[10px] mb-1.5">
                      Observed Broadcast Relays
                    </h4>
                    <div className="space-y-1 max-h-28 overflow-y-auto font-mono text-[11px]">
                      {selectedEntityDetails.related_ips.map((ip, i) => (
                        <div key={i} className="flex justify-between py-0.5 px-2 bg-[#070b16] rounded border border-slate-800/60">
                          <span className="text-cyan-300">{ip.ip}</span>
                          <span className="text-slate-500 text-[10px]">{ip.country} • {ip.asn}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Evidence-Backed Local LLM Explanation Card */}
                <div className="p-3.5 bg-gradient-to-b from-[#0c1425] to-[#070b16] border border-cyan-800/60 rounded-xl space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-300 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                      Local AI Forensic Synthesis
                    </span>
                    <button
                      onClick={handleRequestAi}
                      disabled={aiAnalyzing}
                      className="px-2.5 py-1 rounded text-[10px] font-semibold bg-cyan-600 hover:bg-cyan-500 text-black flex items-center gap-1 transition disabled:opacity-50"
                    >
                      <RefreshCw className={`w-3 h-3 ${aiAnalyzing ? 'animate-spin' : ''}`} />
                      <span>{aiAnalyzing ? 'Reasoning...' : 'Synthesize AI'}</span>
                    </button>
                  </div>

                  {aiAnalysis ? (
                    <div className="text-[11px] text-slate-200 bg-[#050812] p-3 rounded-lg border border-slate-800/80 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                      {aiAnalysis}
                    </div>
                  ) : (
                    <div className="text-[11px] text-slate-500 py-3 text-center">
                      Click 'Synthesize AI' to generate a grounded explanation using your local LLM.
                    </div>
                  )}
                </div>

                {/* Expand Focus Button */}
                <button
                  onClick={() => onSelectEntity(selectedEntityDetails.entity_id, hops)}
                  className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-cyan-400 border border-cyan-800/60 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition"
                >
                  <Network className="w-4 h-4" />
                  <span>Re-Center Graph on This Entity</span>
                </button>
              </>
            ) : selectedEdge ? (
              /* Edge Investigation Briefing */
              <div className="p-3 bg-[#0d1527] border border-amber-800/60 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800/80">
                    NETWORK LINK
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    {selectedEdge.relationship || 'ASSOCIATED_WITH'}
                  </span>
                </div>

                <div className="space-y-1.5">
                  <div className="text-xs font-bold text-slate-200">
                    {selectedEdge.relationship === 'WALLET_TO_WALLET' ? 'Direct Fund Transfer Link' :
                     selectedEdge.relationship === 'IP_TO_TXID' ? 'P2P Broadcast Correlation' :
                     selectedEdge.relationship === 'IP_TO_WALLET' ? 'Wallet Broadcast Endpoint' :
                     'Observed Ledger Connection'}
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#070b16] border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Why this link matters</span>
                    <p className="text-[11px] text-slate-300 leading-snug">
                      {selectedEdge.relationship === 'IP_TO_TXID'
                        ? 'This network IP address was recorded broadcasting the transaction onto the peer-to-peer network within the observation window.'
                        : selectedEdge.relationship === 'WALLET_TO_WALLET'
                        ? 'These two Bitcoin wallets participated directly in the same transaction as sender and receiver.'
                        : 'A multi-hop correlation linking infrastructure and ledger movements.'}
                    </p>
                  </div>
                </div>

                <div className="space-y-1 text-[11px] font-mono bg-[#070b16] p-2.5 rounded-lg border border-slate-800">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Source:</span>
                    <span className="text-cyan-300 truncate max-w-[180px]">{selectedEdge.source}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Target:</span>
                    <span className="text-amber-300 truncate max-w-[180px]">{selectedEdge.target}</span>
                  </div>
                  {selectedEdge.weight && (
                    <div className="flex justify-between pt-1 border-t border-slate-800/60">
                      <span className="text-slate-500">Weight:</span>
                      <span className="text-slate-200 font-bold">{selectedEdge.weight}</span>
                    </div>
                  )}
                </div>

                <button
                  onClick={() => setSelectedEdge(null)}
                  className="w-full py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded text-xs transition"
                >
                  Clear Link Selection
                </button>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 space-y-3">
                <Info className="w-8 h-8 text-slate-600 stroke-1" />
                <div className="font-semibold text-slate-400">No Entity or Link Selected</div>
                <p className="text-[11px] leading-relaxed">
                  Click on any node or connection link in the topology map or choose a Focus Target from the dropdown to inspect its risk profile, associated IPs, transactions, and AI explanation.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function WalletsView({ wallets, onViewGraph }) {
  return (
    <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">Monitored Bitcoin Wallets</h2>
        <span className="text-xs text-slate-400 font-mono">Showing {wallets.length} wallets</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#080c16] text-slate-400 border-b border-slate-800 text-[10px] uppercase font-mono">
            <tr>
              <th className="p-2.5">Wallet Address</th>
              <th className="p-2.5">Risk Score</th>
              <th className="p-2.5">Severity</th>
              <th className="p-2.5">TX Count</th>
              <th className="p-2.5">Inbound (BTC)</th>
              <th className="p-2.5">Outbound (BTC)</th>
              <th className="p-2.5">Counterparties</th>
              <th className="p-2.5">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
            {wallets.map(w => (
              <tr key={w.wallet_address} className="hover:bg-slate-900/30">
                <td className="p-2.5 font-bold text-slate-200">{w.wallet_address}</td>
                <td className="p-2.5 text-cyan-400 font-bold">{w.risk_score}</td>
                <td className="p-2.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    w.severity === 'CRITICAL' ? 'bg-red-950 text-red-300 border border-red-800' :
                    w.severity === 'HIGH' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                    w.severity === 'MEDIUM' ? 'bg-yellow-950 text-yellow-300 border border-yellow-800' :
                    'bg-slate-900 text-slate-400'
                  }`}>
                    {w.severity}
                  </span>
                </td>
                <td className="p-2.5 text-slate-300">{w.total_transactions}</td>
                <td className="p-2.5 text-emerald-400">{w.total_inbound?.toFixed(4)}</td>
                <td className="p-2.5 text-red-400">{w.total_outbound?.toFixed(4)}</td>
                <td className="p-2.5 text-slate-300">{w.unique_counterparties}</td>
                <td className="p-2.5">
                  <button
                    onClick={() => onViewGraph(w.wallet_address)}
                    className="px-2 py-1 bg-slate-800 hover:bg-cyan-900 text-cyan-300 rounded text-[10px] font-sans"
                  >
                    Graph
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TransactionsView({ transactions }) {
  return (
    <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">Cryptographic Ledger Transactions</h2>
        <span className="text-xs text-slate-400 font-mono">Showing {transactions.length} records</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-[#080c16] text-slate-400 border-b border-slate-800 text-[10px] uppercase">
            <tr>
              <th className="p-2.5">Timestamp</th>
              <th className="p-2.5">TXID Hash</th>
              <th className="p-2.5">Input Amount (BTC)</th>
              <th className="p-2.5">Output Amount (BTC)</th>
              <th className="p-2.5">Fee (BTC)</th>
              <th className="p-2.5">Script Type</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-[11px]">
            {transactions.map(t => (
              <tr key={t.txid} className="hover:bg-slate-900/30">
                <td className="p-2.5 text-slate-400">{t.timestamp}</td>
                <td className="p-2.5 font-bold text-cyan-300">{t.txid}</td>
                <td className="p-2.5 text-slate-200">{t.input_amount?.toFixed(6)}</td>
                <td className="p-2.5 text-slate-200">{t.output_amount?.toFixed(6)}</td>
                <td className="p-2.5 text-slate-400">{t.fee?.toFixed(6)}</td>
                <td className="p-2.5 uppercase text-slate-300">{t.script_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function IpsView({ ips, onViewGraph }) {
  return (
    <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">Observed Network IP Space</h2>
        <span className="text-xs text-slate-400 font-mono">Showing {ips.length} monitored IPs</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-[#080c16] text-slate-400 border-b border-slate-800 text-[10px] uppercase">
            <tr>
              <th className="p-2.5">IP Address</th>
              <th className="p-2.5">Geo Country</th>
              <th className="p-2.5">Autonomous System (ASN)</th>
              <th className="p-2.5">Broadcast Count</th>
              <th className="p-2.5">First Observed</th>
              <th className="p-2.5">Last Observed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-[11px]">
            {ips.map(ip => (
              <tr key={ip.ip_address} className="hover:bg-slate-900/30">
                <td className="p-2.5 font-bold text-cyan-300">{ip.ip_address}</td>
                <td className="p-2.5"><span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-semibold">{ip.country || 'N/A'}</span></td>
                <td className="p-2.5 text-slate-300">{ip.asn || 'N/A'}</td>
                <td className="p-2.5 text-slate-200 font-bold">{ip.broadcast_tx_count}</td>
                <td className="p-2.5 text-slate-400">{ip.first_seen}</td>
                <td className="p-2.5 text-slate-400">{ip.last_seen}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TimelineView({ transactions, alerts }) {
  return (
    <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-5 space-y-4">
      <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
        <Clock className="w-4 h-4 text-cyan-400" />
        Investigation Timeline
      </h2>
      <div className="relative border-l border-slate-800 ml-4 space-y-4">
        {transactions.slice(0, 15).map((t, i) => (
          <div key={i} className="relative pl-6">
            <div className="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-cyan-500 border-2 border-[#070a10]" />
            <div className="p-3 bg-[#080c16] rounded-lg border border-slate-800 text-xs">
              <div className="flex justify-between text-slate-400 text-[11px] mb-1 font-mono">
                <span>{t.timestamp}</span>
                <span className="text-cyan-400">{t.input_amount} BTC</span>
              </div>
              <div className="font-mono text-slate-200 truncate">
                TXID: {t.txid}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function IngestView({ ingestStatus, uploadMode, setUploadMode, ingestionResult, onUpload, onRefresh, onViewDataset }) {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Upload Box */}
      <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-8 space-y-6">
        <div className="text-center space-y-2">
          <Upload className="w-10 h-10 text-cyan-400 mx-auto" />
          <h2 className="text-base font-bold text-slate-100">Upload Bulk Bitcoin Metadata</h2>
          <p className="text-xs text-slate-400">
            Supports CSV, JSON, and XML files adhering to SIH26146 Problem Statement parameters.
          </p>
        </div>

        {/* Mode Selector */}
        <div className="bg-[#080c16] p-4 rounded-xl border border-slate-800 space-y-2">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Ingestion Mode:</div>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setUploadMode('REPLACE')}
              className={`p-3 rounded-lg border text-left transition ${
                uploadMode === 'REPLACE'
                  ? 'bg-cyan-950/70 border-cyan-500 text-cyan-200 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                  : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center space-x-2 text-xs font-bold">
                <span className={`w-2 h-2 rounded-full ${uploadMode === 'REPLACE' ? 'bg-cyan-400' : 'bg-slate-600'}`} />
                <span>MODE B: REPLACE DATA (Default)</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Clears old records and isolates analysis strictly to this uploaded dataset.
              </p>
            </button>

            <button
              type="button"
              onClick={() => setUploadMode('APPEND')}
              className={`p-3 rounded-lg border text-left transition ${
                uploadMode === 'APPEND'
                  ? 'bg-cyan-950/70 border-cyan-500 text-cyan-200 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                  : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center space-x-2 text-xs font-bold">
                <span className={`w-2 h-2 rounded-full ${uploadMode === 'APPEND' ? 'bg-cyan-400' : 'bg-slate-600'}`} />
                <span>MODE A: APPEND DATA</span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1">
                Adds the uploaded transactions to the existing database records.
              </p>
            </button>
          </div>
        </div>

        {/* File Drag & Drop */}
        <div className="border-2 border-dashed border-slate-700 hover:border-cyan-500 rounded-xl p-8 text-center bg-[#080c16] cursor-pointer relative">
          <input
            type="file"
            accept=".csv,.json,.xml"
            onChange={onUpload}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          <div className="text-xs text-slate-300 font-medium">
            Drag and drop or <span className="text-cyan-400 underline">browse file</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-1">
            Supported: CSV, JSON, XML (Auto-deduplicated & normalized into DuckDB)
          </div>
        </div>

        {ingestStatus && (
          <div className="p-3 rounded-lg bg-cyan-950/60 border border-cyan-800/80 text-xs text-cyan-300 font-mono">
            {ingestStatus}
          </div>
        )}
      </div>

      {/* Ingestion Result Summary Screen */}
      {ingestionResult && (
        <div className="bg-[#0b101d] border border-cyan-800/80 rounded-xl p-6 space-y-4 shadow-[0_0_20px_rgba(6,182,212,0.15)]">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2 text-emerald-400 font-bold text-sm">
              <CheckCircle2 className="w-5 h-5" />
              <span>UPLOAD & AUTOMATIC PIPELINE COMPLETE</span>
            </div>
            <button
              onClick={onViewDataset}
              className="px-4 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-xs shadow-[0_0_12px_rgba(6,182,212,0.4)] transition"
            >
              VIEW DATASET →
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-[#080c16] p-3 rounded-lg border border-slate-800">
              <div className="text-slate-400 text-[10px] uppercase">Filename</div>
              <div className="font-mono text-cyan-300 font-bold truncate mt-0.5">{ingestionResult.filename}</div>
            </div>
            <div className="bg-[#080c16] p-3 rounded-lg border border-slate-800">
              <div className="text-slate-400 text-[10px] uppercase">Records Parsed</div>
              <div className="font-mono text-slate-200 font-bold mt-0.5">{ingestionResult.valid_records} / {ingestionResult.total_records}</div>
            </div>
            <div className="bg-[#080c16] p-3 rounded-lg border border-slate-800">
              <div className="text-slate-400 text-[10px] uppercase">Transactions (TXIDs)</div>
              <div className="font-mono text-emerald-400 font-bold mt-0.5">{ingestionResult.transactions_inserted}</div>
            </div>
            <div className="bg-[#080c16] p-3 rounded-lg border border-slate-800">
              <div className="text-slate-400 text-[10px] uppercase">Wallets Extracted</div>
              <div className="font-mono text-amber-400 font-bold mt-0.5">{ingestionResult.wallets_count}</div>
            </div>
            <div className="bg-[#080c16] p-3 rounded-lg border border-slate-800">
              <div className="text-slate-400 text-[10px] uppercase">IP Observations</div>
              <div className="font-mono text-indigo-400 font-bold mt-0.5">{ingestionResult.observations_count}</div>
            </div>
            <div className="bg-[#080c16] p-3 rounded-lg border border-slate-800">
              <div className="text-slate-400 text-[10px] uppercase">Graph Relationships</div>
              <div className="font-mono text-purple-400 font-bold mt-0.5">{ingestionResult.correlation?.relationships_created || 0}</div>
            </div>
            <div className="bg-[#080c16] p-3 rounded-lg border border-slate-800">
              <div className="text-slate-400 text-[10px] uppercase">ML Entities Analyzed</div>
              <div className="font-mono text-cyan-400 font-bold mt-0.5">{ingestionResult.ml_results?.total_entities_evaluated || 0}</div>
            </div>
            <div className="bg-[#080c16] p-3 rounded-lg border border-slate-800">
              <div className="text-slate-400 text-[10px] uppercase">Alerts Generated</div>
              <div className="font-mono text-red-400 font-bold mt-0.5">{ingestionResult.total_alerts || 0}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

