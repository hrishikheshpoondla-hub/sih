// frontend/src/utils/interpretation.js
// SIH26146 - Plain-Language Human Interpretation Layer
// Translates complex blockchain, graph theory, and ML terminology into plain language.

export const METRIC_DICTIONARY = {
  transaction_frequency: {
    plainName: 'Transaction Speed',
    whatItMeans: 'How quickly transactions are occurring over time.',
    whyItMatters: 'Rapid bursts of transactions often indicate automated bots, batch payouts, or rapid fund dispersal across networks.',
    technicalCalculation: 'Count of transactions normalized per hour from first seen to last seen timestamp in DuckDB ledger.'
  },
  burst_frequency: {
    plainName: 'Transaction Velocity Burst',
    whatItMeans: 'The highest number of transactions executed within a short 15-minute window.',
    whyItMatters: 'Bursts help identify automated coordination or flash fund movements that deviate from regular human wallet usage.',
    technicalCalculation: 'Rolling 15-minute window maximum transaction count computed over transaction input/output timestamps.'
  },
  unique_counterparties: {
    plainName: 'Different Destinations & Sources',
    whatItMeans: 'How many different wallets this entity sent funds to or received funds from.',
    whyItMatters: 'Interacting with dozens of unique destinations can indicate peeling chains, mixing services, or distribution hubs.',
    technicalCalculation: 'Distinct count of counterparties in transaction_inputs and transaction_outputs.'
  },
  unique_ips: {
    plainName: 'Observed Network Sources',
    whatItMeans: 'How many distinct internet addresses broadcasted transactions associated with this entity.',
    whyItMatters: 'Legitimate personal wallets usually broadcast from 1 or 2 locations. Using many IPs can point to VPN rotation, proxies, or coordinated infrastructure.',
    technicalCalculation: 'Distinct count of source IP addresses linked via P2P network broadcast observations.'
  },
  unique_countries: {
    plainName: 'Geographic Locations',
    whatItMeans: 'How many different countries were observed broadcasting transactions for this entity.',
    whyItMatters: 'Simultaneous or rapid geographic distribution suggests routing through global proxy networks or Tor exit nodes.',
    technicalCalculation: 'Distinct ISO country codes mapped from observed source IP addresses.'
  },
  unique_asns: {
    plainName: 'Hosting & Internet Providers',
    whatItMeans: 'The number of distinct internet network carriers or cloud data center providers observed.',
    whyItMatters: 'Activity originating from data centers rather than residential internet providers is common in automated scripts.',
    technicalCalculation: 'Distinct Autonomous System Numbers (ASNs) mapped from source IP observations.'
  },
  graph_degree: {
    plainName: 'Network Connection Count',
    whatItMeans: 'How many direct links this entity has to other wallets, transactions, or IPs.',
    whyItMatters: 'Entities with high connections act as central routing bridges or concentration points in the flow of funds.',
    technicalCalculation: 'Total degree (in-degree + out-degree) in the NetworkX multi-relational graph topology.'
  },
  graph_centrality: {
    plainName: 'Network Importance Position',
    whatItMeans: 'How strategically positioned this wallet is within the broader transaction web.',
    whyItMatters: 'A high position means funds flowing through this entity can quickly reach large portions of the network.',
    technicalCalculation: 'Betweenness and eigenvector graph centrality calculated on the connected transaction subnetwork.'
  },
  transaction_volume: {
    plainName: 'Total Bitcoin Moved',
    whatItMeans: 'The cumulative amount of Bitcoin sent and received by this entity.',
    whyItMatters: 'Significant deviations in total throughput highlight high-value movement relative to the rest of the monitored population.',
    technicalCalculation: 'Sum of total input amounts and output amounts recorded in transactions table.'
  },
  cluster_size: {
    plainName: 'Associated Behavioral Group',
    whatItMeans: 'The group of entities showing similar transaction patterns or connected flows.',
    whyItMatters: 'Helps identify clusters of wallets likely controlled by the same actor or automated workflow.',
    technicalCalculation: 'DBSCAN behavioral cluster or connected topological component size.'
  }
};

export const CONCEPT_TOOLTIPS = {
  isolation_forest: {
    term: 'Anomaly Detection',
    simple: 'A machine-learning model used to spot behavior that looks significantly different from normal wallets.',
    analyst: 'Unsupervised Isolation Forest algorithm isolating multidimensional feature anomalies without labeled data.'
  },
  dbscan: {
    term: 'Behavioral Grouping',
    simple: 'An algorithm that automatically groups together entities that behave similarly.',
    analyst: 'Density-Based Spatial Clustering of Applications with Noise (DBSCAN) using min_samples and epsilon.'
  },
  risk_score: {
    term: 'Investigation Priority',
    simple: 'A 0–100 ranking showing how urgently this entity should be reviewed by an investigator.',
    analyst: 'RobustScaler normalized decision-function anomaly score combining 19 behavioral and topological features.'
  },
  pagerank: {
    term: 'Connection Influence',
    simple: 'How strongly this entity is connected to other active or influential entities in the network.',
    analyst: 'Random-walk stationary probability distribution over directed transaction linkages.'
  },
  fan_out: {
    term: 'Multiple Destinations',
    simple: 'How many different destination wallets this address distributes funds out to.',
    analyst: 'Out-degree transaction output distribution indicating potential peeling chains or fan-out dispersion.'
  },
  fan_in: {
    term: 'Multiple Sources',
    simple: 'How many different source wallets send funds into this address.',
    analyst: 'In-degree consolidation pattern showing aggregation from disparate funding origins.'
  },
  wallet: {
    term: 'Wallet',
    simple: 'A Bitcoin address used to hold, send, and receive digital funds.',
    analyst: 'P2PKH / P2SH / Bech32 cryptographic public key hash on the Bitcoin ledger.'
  },
  ip_address: {
    term: 'Network Source',
    simple: 'The internet address from which transaction traffic was broadcasted onto the P2P network.',
    analyst: 'IPv4/IPv6 source endpoint observed by network peer telemetry nodes during inventory broadcasts.'
  },
  transaction: {
    term: 'Blockchain Transaction',
    simple: 'A recorded transfer of Bitcoin funds from input addresses to output addresses.',
    analyst: 'Cryptographically signed transaction hash (TXID) with inputs, outputs, fee rate, and timestamp.'
  }
};

export function getPlainMetricName(featureName) {
  return METRIC_DICTIONARY[featureName]?.plainName || featureName.replace(/_/g, ' ');
}

export function buildPlainSummary(dossier) {
  if (!dossier) return '';
  const val = dossier.entity_value || 'This entity';
  const shortVal = val.length > 24 ? val.slice(0, 10) + '...' : val;
  const evList = dossier.evidence || [];
  const relatedIps = dossier.related_ips || [];

  let summary = 'This wallet shows an unusual pattern of activity. ';

  const hasBurst = evList.some(e => e.feature_name && (e.feature_name.includes('burst') || e.feature_name.includes('frequency')));
  const hasCounterparties = evList.some(e => e.feature_name && (e.feature_name.includes('counterparties') || e.feature_name.includes('degree')));
  const hasMultipleIps = relatedIps.length > 2 || evList.some(e => e.feature_name && e.feature_name.includes('unique_ips'));

  if (hasBurst && hasMultipleIps) {
    summary += 'It moved funds much faster than typical wallets in this dataset and was observed broadcasting from ' + relatedIps.length + ' different network source IP addresses. ';
  } else if (hasBurst) {
    summary += 'It executed transactions at a rate significantly higher than typical wallets, suggesting automated or rapid batch activity. ';
  } else if (hasCounterparties) {
    summary += 'It interacted with a high number of different counterparties within a brief observation window. ';
  } else {
    summary += 'Its transaction velocity and network relationships deviate significantly from standard baseline patterns. ';
  }

  summary += 'This pattern is distinctive enough to warrant prioritized review by an investigator.';
  return summary;
}

export function buildPlainReasons(dossier) {
  if (!dossier) return [];
  const evList = dossier.evidence || [];
  const relatedIps = dossier.related_ips || [];
  const reasons = [];

  evList.forEach(ev => {
    const fn = ev.feature_name || '';
    const fv = ev.feature_value != null ? Number(ev.feature_value).toFixed(1) : '';
    if (fn.includes('burst')) {
      reasons.push({
        icon: '🔴',
        color: 'text-red-400',
        title: 'Very unusual transaction speed',
        desc: 'The wallet made transactions in rapid bursts' + (fv ? ' (' + fv + ' in 15 min)' : '') + ', far faster than typical wallets in this dataset.'
      });
    } else if (fn.includes('frequency')) {
      reasons.push({
        icon: '🔴',
        color: 'text-red-400',
        title: 'Elevated transaction rate',
        desc: 'Active at ' + (fv || 'unusually high') + ' transactions per hour, which is noticeably higher than normal.'
      });
    } else if (fn.includes('counterparties') || fn.includes('degree')) {
      reasons.push({
        icon: '🟠',
        color: 'text-amber-400',
        title: 'Many destinations & sources',
        desc: 'The wallet interacted with ' + (fv ? Math.round(Number(fv)) : 'multiple') + ' different counterparties across the network.'
      });
    } else if (fn.includes('unique_ips')) {
      reasons.push({
        icon: '🟠',
        color: 'text-amber-400',
        title: 'Multiple network sources',
        desc: 'Activity associated with this wallet was observed from ' + (fv ? Math.round(Number(fv)) : relatedIps.length) + ' different IP addresses.'
      });
    } else if (fn.includes('volume')) {
      reasons.push({
        icon: '🟡',
        color: 'text-yellow-400',
        title: 'Higher than normal Bitcoin volume',
        desc: 'Moved ' + (fv || 'substantial') + ' BTC, exceeding the median volume baseline.'
      });
    } else if (fn.includes('centrality')) {
      reasons.push({
        icon: '🟡',
        color: 'text-yellow-400',
        title: 'Unusual network position',
        desc: 'This entity occupies a central position that connects multiple disparate transaction groups.'
      });
    }
  });

  if (reasons.length === 0 && relatedIps.length > 1) {
    reasons.push({
      icon: '🟠',
      color: 'text-amber-400',
      title: 'Multiple source locations',
      desc: 'Transactions were broadcast from ' + relatedIps.length + ' distinct internet source addresses.'
    });
  }

  if (reasons.length === 0) {
    reasons.push({
      icon: '🟡',
      color: 'text-yellow-400',
      title: 'Statistical behavioral deviation',
      desc: 'Activity falls into an outlier cluster compared with standard population baselines.'
    });
  }

  return reasons.slice(0, 4);
}

export function buildInvestigationStory(dossier) {
  if (!dossier) return [];
  const steps = [];
  const val = dossier.entity_value || 'Wallet';
  const shortVal = val.length > 20 ? val.slice(0, 10) + '...' : val;
  const ips = dossier.related_ips || [];
  const txs = dossier.related_txs || [];
  const evList = dossier.evidence || [];

  steps.push({
    step: 1,
    title: 'Initial Ledger Activity Observed',
    text: 'Bitcoin ledger activity was recorded involving ' + shortVal + ', with ' + (txs.length || 1) + ' linked transactions observed in the monitored window.'
  });

  if (ips.length > 0) {
    const firstIp = ips[0]?.ip ? ips[0].ip + (ips[0]?.country ? ' in ' + ips[0].country : '') : 'external endpoints';
    steps.push({
      step: 2,
      title: 'Network Telemetry Correlated',
      text: 'Transactions were broadcast across the P2P network and correlated with ' + ips.length + ' distinct source IP address(es) (' + firstIp + ').'
    });
  }

  const burstEv = evList.find(e => e.feature_name && (e.feature_name.includes('burst') || e.feature_name.includes('frequency')));
  if (burstEv) {
    steps.push({
      step: steps.length + 1,
      title: 'Unusual Transaction Speed Detected',
      text: 'The activity occurred in rapid succession, peaking at ' + (burstEv.feature_value != null ? Number(burstEv.feature_value).toFixed(1) : 'high') + ' transactions within a short timeframe—greatly exceeding baseline behavior.'
    });
  }

  const cpEv = evList.find(e => e.feature_name && (e.feature_name.includes('counterparties') || e.feature_name.includes('degree')));
  if (cpEv) {
    steps.push({
      step: steps.length + 1,
      title: 'Multiple Counterparties Identified',
      text: 'Funds flowed to/from ' + (cpEv.feature_value != null ? Math.round(Number(cpEv.feature_value)) : 'several') + ' distinct addresses, showing widespread network linkage.'
    });
  }

  steps.push({
    step: steps.length + 1,
    title: 'Investigation Priority Assigned',
    text: 'Due to the combination of velocity, source distribution, and network connections, this entity was assigned a priority score of ' + (dossier.risk_score || 0) + '/100 (' + (dossier.severity || 'HIGH') + ' priority).'
  });

  return steps;
}
