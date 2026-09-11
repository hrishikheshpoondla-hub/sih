# SIH26146 Machine Learning & Risk Scoring Pipeline

## 1. Feature Engineering (19 Deterministic Metrics)
Each monitored entity is quantified across behavioral and topological dimensions:

1. `transaction_count`: Number of distinct transactions observed.
2. `transaction_frequency`: Transactions per hour over active lifespan.
3. `transaction_volume`: Cumulative inbound and outbound Bitcoin volume.
4. `average_transaction_amount`: Mean value transferred per transaction.
5. `transaction_amount_variance`: Variance of transfer values.
6. `unique_counterparties`: Count of distinct transacting counterparty wallets.
7. `unique_ips`: Count of distinct source IPs broadcasting transactions.
8. `unique_countries`: Geographical distribution of observed broadcasts.
9. `unique_asns`: Number of distinct Autonomous Systems broadcasting.
10. `inbound_volume`: Total Bitcoin credited to wallet.
11. `outbound_volume`: Total Bitcoin debited from wallet.
12. `inbound_outbound_ratio`: Ratio of incoming to outgoing funds.
13. `fee_average`: Mean miner fee paid.
14. `fee_variance`: Variance of miner fees paid.
15. `burst_frequency`: Maximum transactions within any 15-minute sliding window.
16. `graph_degree`: In-degree + out-degree in the entity relationship graph.
17. `graph_weighted_degree`: Transaction-flow-weighted connectivity.
18. `graph_centrality`: Approximate betweenness centrality across network.
19. `cluster_size`: Size of the connected topological component.

---

## 2. Model: Isolation Forest
- **Algorithm**: `sklearn.ensemble.IsolationForest`
- **Parameters**: `contamination=0.08`, `random_state=42`, `n_estimators=100`
- **Scaling**: `RobustScaler` (handles extreme financial transaction volume outliers safely)

## 3. Standardized Risk Scoring
- Raw anomaly score from `score_samples()` is inverted and normalized onto a transparent `[0, 100]` scale.
- **Severity Brackets**:
  - `CRITICAL`: Risk Score >= 85.0
  - `HIGH`: Risk Score 70.0 - 84.9
  - `MEDIUM`: Risk Score 45.0 - 69.9
  - `LOW`: Risk Score < 45.0
