"""
backend/app/graph/network.py
NetworkX Graph Engine for SIH26146.
Constructs entity-relationship graphs linking IPs, TXIDs, and Wallets.
Computes:
- Node degrees & weighted degrees
- PageRank & Centrality metrics
- Connected components
- k-hop investigative subgraphs for visual link analysis.
"""

import networkx as nx
from typing import Dict, Any, List, Optional, Set
from app.database.connection import DatabaseManager

class EntityGraphManager:
    def __init__(self, db_conn=None):
        self.db_mgr = DatabaseManager.get_instance()
        self._external_conn = db_conn
        self.G = nx.DiGraph()
        self.undirected_G = nx.Graph()

    def _get_conn(self):
        return self._external_conn if self._external_conn else self.db_mgr.get_connection()

    def load_graph(self):
        """Loads all entities and relationships from DuckDB into NetworkX DiGraph."""
        conn = self._get_conn()
        try:
            self.G.clear()
            self.undirected_G.clear()

            # Load entities as nodes
            nodes = conn.execute("""
                SELECT entity_id, entity_type, entity_value, first_seen, last_seen
                FROM entities;
            """).fetchall()

            for eid, etype, evalue, fs, ls in nodes:
                self.G.add_node(
                    eid,
                    entity_type=etype,
                    entity_value=evalue,
                    first_seen=str(fs) if fs else "",
                    last_seen=str(ls) if ls else ""
                )

            # Load relationships as edges
            edges = conn.execute("""
                SELECT source_entity_id, target_entity_id, relationship_type, weight, transaction_count
                FROM entity_relationships;
            """).fetchall()

            for src, tgt, rtype, weight, tx_cnt in edges:
                self.G.add_edge(
                    src, tgt,
                    relationship_type=rtype,
                    weight=float(weight or 1.0),
                    transaction_count=int(tx_cnt or 1)
                )

            self.undirected_G = self.G.to_undirected()
            return self.G
        finally:
            if not self._external_conn:
                conn.close()

    def compute_graph_metrics(self) -> Dict[int, Dict[str, float]]:
        """Computes degree, PageRank, and centrality for all nodes."""
        if len(self.G) == 0:
            self.load_graph()

        if len(self.G) == 0:
            return {}

        pagerank = nx.pagerank(self.G, weight="weight", alpha=0.85)
        in_degrees = dict(self.G.in_degree())
        out_degrees = dict(self.G.out_degree())
        weighted_degrees = dict(self.G.degree(weight="weight"))

        # Approximate betweenness centrality for speed on large sets
        k_samples = min(50, len(self.G))
        betweenness = nx.betweenness_centrality(self.G, k=k_samples, weight="weight", seed=42)

        metrics = {}
        for node_id in self.G.nodes:
            total_deg = in_degrees.get(node_id, 0) + out_degrees.get(node_id, 0)
            metrics[node_id] = {
                "degree": total_deg,
                "weighted_degree": round(float(weighted_degrees.get(node_id, 0.0)), 4),
                "pagerank": round(float(pagerank.get(node_id, 0.0)), 6),
                "centrality": round(float(betweenness.get(node_id, 0.0)), 6)
            }
        return metrics

    def compute_common_input_clusters(self) -> Dict[str, Any]:
        """
        Implements Satoshi's Common-Input Ownership Heuristic (Multi-Input Clustering).
        If multiple input addresses appear in the same transaction, they are controlled
        by the same entity. Uses Disjoint-Set / Connected Components to group wallets.
        """
        conn = self._get_conn()
        try:
            # Fetch transactions with multiple distinct input addresses
            rows = conn.execute("""
                SELECT txid, wallet_address
                FROM transaction_inputs
                ORDER BY txid;
            """).fetchall()

            tx_to_wallets: Dict[str, Set[str]] = {}
            for txid, w_addr in rows:
                if txid not in tx_to_wallets:
                    tx_to_wallets[txid] = set()
                tx_to_wallets[txid].add(w_addr)

            # Build wallet co-input graph
            co_input_graph = nx.Graph()
            for txid, wallets in tx_to_wallets.items():
                if len(wallets) > 1:
                    w_list = list(wallets)
                    for i in range(len(w_list)):
                        for j in range(i + 1, len(w_list)):
                            co_input_graph.add_edge(w_list[i], w_list[j], txid=txid)

            # Find connected components (each component is one entity)
            clusters: Dict[str, str] = {} # wallet_address -> cluster_id
            cluster_summaries = []
            
            for cluster_idx, component in enumerate(nx.connected_components(co_input_graph), start=1):
                cid = f"ENTITY-CLUSTER-{cluster_idx:04d}"
                w_list = list(component)
                for w in w_list:
                    clusters[w] = cid
                cluster_summaries.append({
                    "cluster_id": cid,
                    "wallet_count": len(w_list),
                    "wallets": w_list[:10],
                    "heuristic": "Common-Input Ownership (Multi-Input Heuristic)"
                })

            print(f"[HEURISTIC] Common-Input Ownership Clustering: Grouped {len(clusters)} wallets into {len(cluster_summaries)} multi-input entities.")
            return {
                "wallet_to_cluster": clusters,
                "cluster_summaries": cluster_summaries,
                "total_clusters": len(cluster_summaries),
                "total_clustered_wallets": len(clusters)
            }
        finally:
            if not self._external_conn:
                conn.close()

    def propagate_risk_scores(self, base_risk_scores: Dict[int, float], alpha: float = 0.85) -> Dict[int, float]:
        """
        Propagates risk scores from high-risk seed illicit wallets across the transaction
        graph using Personalized PageRank (PPR) / Graph Diffusion.
        - Seeds: Entities with base risk >= 70.0
        - Alpha: Restart probability / damping factor (0.85 standard)
        Returns blended risk scores: 0.6 * base_risk + 0.4 * propagated_risk.
        """
        if len(self.G) == 0:
            self.load_graph()

        if len(self.G) == 0 or not base_risk_scores:
            return base_risk_scores

        # Define personalization vector weighted by seed risk
        personalization = {}
        seed_weight_sum = 0.0
        for node_id in self.G.nodes:
            r = base_risk_scores.get(node_id, 0.0)
            if r >= 70.0:
                personalization[node_id] = r
                seed_weight_sum += r
            else:
                personalization[node_id] = 0.0

        # If no critical/high seeds, return base scores
        if seed_weight_sum <= 0:
            return base_risk_scores

        # Normalize personalization vector
        for k in personalization:
            personalization[k] /= seed_weight_sum

        try:
            ppr = nx.pagerank(self.G, alpha=alpha, personalization=personalization, weight="weight")
            # Normalize PPR to 0-100 scale
            max_ppr = max(ppr.values()) if ppr else 1.0
            scale = 100.0 / max_ppr if max_ppr > 0 else 1.0

            propagated_scores = {}
            for node_id, base_r in base_risk_scores.items():
                ppr_val = ppr.get(node_id, 0.0) * scale
                # Blended risk score: incorporates native behavioral anomaly + graph network contagion
                blended = round(0.65 * base_r + 0.35 * ppr_val, 1)
                propagated_scores[node_id] = min(100.0, max(0.0, blended))

            return propagated_scores
        except Exception as e:
            print(f"[WARN] Risk propagation fallback: {e}")
            return base_risk_scores

    def get_neighborhood_subgraph(self, root_entity_id_or_val: Any, max_hops: int = 2, max_nodes: int = 60) -> Dict[str, Any]:
        """Extracts a localized subgraph around an investigative focus entity."""
        if len(self.G) == 0:
            self.load_graph()

        # Resolve entity_id if value provided
        root_id = None
        if isinstance(root_entity_id_or_val, int):
            root_id = root_entity_id_or_val
        else:
            # Search by value
            for n, data in self.G.nodes(data=True):
                if data.get("entity_value") == str(root_entity_id_or_val):
                    root_id = n
                    break

        if root_id is None or root_id not in self.G:
            return {"nodes": [], "edges": [], "root_entity": None}

        # Breadth-first search up to max_hops
        visited = {root_id}
        current_layer = {root_id}
        for hop in range(max_hops):
            next_layer = set()
            for node in current_layer:
                nbrs = set(self.undirected_G.neighbors(node))
                for nbr in nbrs:
                    if nbr not in visited:
                        visited.add(nbr)
                        next_layer.add(nbr)
                        if len(visited) >= max_nodes:
                            break
                if len(visited) >= max_nodes:
                    break
            current_layer = next_layer
            if len(visited) >= max_nodes:
                break

        # Build Cytoscape / VisNetwork JSON
        sub_G = self.G.subgraph(visited)

        # Batch fetch risk scores & alert IDs for sub_G nodes from DuckDB
        conn = self._get_conn()
        node_enrichment = {}
        edge_enrichment = {}
        try:
            node_ids = list(sub_G.nodes)
            if node_ids:
                placeholders = ",".join(["?"] * len(node_ids))
                q = f"""
                    SELECT e.entity_id,
                           coalesce(s.normalized_risk_score, 0.0) as risk,
                           coalesce(s.severity, 'LOW') as sev,
                           a.alert_id,
                           e.first_seen,
                           e.last_seen
                    FROM entities e
                    LEFT JOIN anomaly_scores s ON e.entity_id = s.entity_id
                    LEFT JOIN investigation_alerts a ON e.entity_id = a.entity_id
                    WHERE e.entity_id IN ({placeholders});
                """
                rows = conn.execute(q, node_ids).fetchall()
                for r in rows:
                    node_enrichment[r[0]] = {
                        "risk_score": float(r[1]),
                        "severity": str(r[2]),
                        "alert_id": r[3],
                        "first_seen": str(r[4]) if r[4] else "",
                        "last_seen": str(r[5]) if r[5] else ""
                    }
        except Exception as e:
            print(f"[WARN] Error fetching node enrichment: {e}")
        finally:
            if not self._external_conn:
                conn.close()

        nodes_out = []
        for n in sub_G.nodes:
            data = self.G.nodes[n]
            enr = node_enrichment.get(n, {})
            nodes_out.append({
                "id": str(n),
                "label": data.get("entity_value")[:14] + ("..." if len(data.get("entity_value", "")) > 14 else ""),
                "full_value": data.get("entity_value"),
                "type": data.get("entity_type"),
                "is_root": (n == root_id),
                "risk_score": enr.get("risk_score", 0.0),
                "severity": enr.get("severity", "LOW"),
                "alert_id": enr.get("alert_id"),
                "first_seen": enr.get("first_seen", data.get("first_seen", "")),
                "last_seen": enr.get("last_seen", data.get("last_seen", ""))
            })

        edges_out = []
        for u, v, data in sub_G.edges(data=True):
            edges_out.append({
                "source": str(u),
                "target": str(v),
                "relationship": data.get("relationship_type"),
                "weight": data.get("weight"),
                "transaction_count": data.get("transaction_count")
            })

        root_enr = node_enrichment.get(root_id, {})
        return {
            "root_entity": {
                "id": str(root_id),
                "value": self.G.nodes[root_id].get("entity_value"),
                "type": self.G.nodes[root_id].get("entity_type"),
                "risk_score": root_enr.get("risk_score", 0.0),
                "severity": root_enr.get("severity", "LOW"),
                "alert_id": root_enr.get("alert_id")
            },
            "nodes": nodes_out,
            "edges": edges_out,
            "total_nodes": len(nodes_out),
            "total_edges": len(edges_out)
        }
