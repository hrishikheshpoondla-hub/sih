# SIH26146 Demonstration Walkthrough Scenario

This walkthrough presents a complete end-to-end investigation scenario on the benchmark dataset.

---

## 1. System Launch
1. Start the platform:
   ```bash
   python backend/run.py
   ```
2. Open dashboard in browser: `http://localhost:8000/`.

---

## 2. Investigation Case Study: ALERT #001
- **Entity**: `1W1837DarkNodeHighFreqLeadX99999`
- **Severity**: `CRITICAL`
- **Risk Score**: `100.0 / 100`
- **Confidence**: `94.0%`
- **Status**: `NEW`

### Forensic Evidence Highlights:
1. **Burst Frequency**: 40 transactions in a 15-minute window (**40.0x population median**).
2. **Transaction Velocity**: 160.0 transactions/hour compared to baseline median of 1.5 tx/hr (**108.3x deviation**).
3. **Correlated IPs**: Broadcast observed across 14 distinct source IPs (**14.0x baseline**).
4. **Counterparties**: 31 distinct recipient wallets (**31.0x baseline**).
5. **Graph Connectivity**: Network degree of 85 links across the transaction topology (**14.2x baseline**).
6. **Total Throughput**: 451.49 BTC volume (**143.6x baseline**).

---

## 3. Link Analysis Topology
Selecting `1W1837DarkNodeHighFreqLeadX99999` in the **Entity Graph** reveals:
```
           [IP: 185.220.101.10]   [IP: 185.220.101.25]   [IP: 185.220.101.11]
                     \                      |                      /
                      \                     |                     /
                       v                    v                    v
                                 [TXIDs: burst_w1837_...]
                                            |
                                            v
                         [WALLET: 1W1837DarkNodeHighFreq...]
                                            |
                                            v
                             [Counterparty Wallets: 31 Nodes]
```

---

## 4. Local AI Narrative (NVIDIA Nemotron 3.5)
Clicking **Generate AI Explanation** produces a structured briefing:
- **Executive Summary**: Synthesizes the critical risk rating based solely on recorded metrics.
- **Key Forensic Evidence**: Highlights the 40x burst and 14 correlated IPs.
- **Observed Pattern**: Identifies coordinated multi-IP infrastructure hopping.
- **Recommended Leads**: Recommends inspecting forward 2-hop flows and correlating AS9009 infrastructure.
- **Limitations**: Reiterates decision-support nature and notes possibility of automated exchange batch operations.
