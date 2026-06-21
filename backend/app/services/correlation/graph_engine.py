"""
CyberTrace AI – Graph-Based Threat Correlation Engine
Core intelligence layer: maps entities and complaints into Neo4j,
detects hidden relationships, and identifies criminal campaigns.
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from app.db.neo4j import neo4j_session

logger = logging.getLogger(__name__)


class GraphCorrelationEngine:
    """
    Maps extracted entities and complaints into Neo4j graph.
    Runs correlation queries to surface hidden relationships
    between complaints that share common cyber indicators.
    """

    # ── Graph Ingestion ────────────────────────────────────────────────────
    async def add_complaint_node(self, complaint_id: str, data: dict) -> str:
        """Create or update a Complaint node in the graph."""
        cypher = """
        MERGE (c:Complaint {complaint_id: $complaint_id})
        SET c.complaint_number = $complaint_number,
            c.category         = $category,
            c.status           = $status,
            c.risk_score       = $risk_score,
            c.created_at       = $created_at,
            c.financial_loss   = $financial_loss
        RETURN elementId(c) AS node_id
        """
        async with neo4j_session() as session:
            result = await session.run(cypher, complaint_id=complaint_id, **data)
            record = await result.single()
            return record["node_id"] if record else ""

    async def add_entity_node(
        self,
        entity_type: str,
        value: str,
        normalized_value: str,
        confidence: float,
        risk_score: float = 0.0,
    ) -> str:
        """Create or update an Entity node."""
        cypher = """
        MERGE (e:Entity {type: $entity_type, value: $normalized_value})
        ON CREATE SET e.raw_value    = $value,
                      e.confidence   = $confidence,
                      e.risk_score   = $risk_score,
                      e.first_seen   = datetime(),
                      e.seen_count   = 1
        ON MATCH  SET e.seen_count   = e.seen_count + 1,
                      e.risk_score   = CASE WHEN $risk_score > e.risk_score
                                       THEN $risk_score ELSE e.risk_score END,
                      e.last_seen    = datetime()
        RETURN elementId(e) AS node_id
        """
        async with neo4j_session() as session:
            result = await session.run(
                cypher,
                entity_type=entity_type,
                value=value,
                normalized_value=normalized_value or value,
                confidence=confidence,
                risk_score=risk_score,
            )
            record = await result.single()
            return record["node_id"] if record else ""

    async def link_entity_to_complaint(
        self,
        complaint_id: str,
        entity_type: str,
        normalized_value: str,
        source: str = "nlp",
    ):
        """Create CONTAINS relationship from Complaint to Entity."""
        cypher = """
        MATCH (c:Complaint {complaint_id: $complaint_id})
        MATCH (e:Entity {type: $entity_type, value: $normalized_value})
        MERGE (c)-[r:CONTAINS {source: $source}]->(e)
        ON CREATE SET r.linked_at = datetime()
        """
        async with neo4j_session() as session:
            await session.run(
                cypher,
                complaint_id=complaint_id,
                entity_type=entity_type,
                normalized_value=normalized_value,
                source=source,
            )

    # ── Correlation Queries ────────────────────────────────────────────────
    async def find_related_complaints(
        self, complaint_id: str, min_shared: int = 1, limit: int = 20
    ) -> List[Dict]:
        """
        Find complaints sharing one or more entities with the given complaint.
        Returns ranked list with shared entity details.
        """
        cypher = """
        MATCH (c1:Complaint {complaint_id: $complaint_id})-[:CONTAINS]->(e:Entity)
              <-[:CONTAINS]-(c2:Complaint)
        WHERE c2.complaint_id <> $complaint_id
        WITH c2, collect(e) AS shared_entities, count(e) AS shared_count
        WHERE shared_count >= $min_shared
        RETURN c2.complaint_id        AS complaint_id,
               c2.complaint_number    AS complaint_number,
               c2.category            AS category,
               c2.risk_score          AS risk_score,
               shared_count,
               [e IN shared_entities | {type: e.type, value: e.value}]
                   AS shared_entities
        ORDER BY shared_count DESC, c2.risk_score DESC
        LIMIT $limit
        """
        async with neo4j_session() as session:
            result = await session.run(
                cypher,
                complaint_id=complaint_id,
                min_shared=min_shared,
                limit=limit,
            )
            return [dict(r) async for r in result]

    async def find_entity_network(
        self, entity_type: str, value: str, depth: int = 2
    ) -> Dict:
        """
        Return the full network around an entity up to N hops.
        Used for graph visualization in the dashboard.
        """
        cypher = """
        MATCH path = (e:Entity {type: $entity_type, value: $value})
                     -[:CONTAINS*1..$depth]-(c:Complaint)
        WITH e, c,
             [rel IN relationships(path) | type(rel)] AS rel_types
        RETURN e.type AS entity_type,
               e.value AS entity_value,
               e.risk_score AS entity_risk,
               collect(DISTINCT {
                   id:     c.complaint_id,
                   number: c.complaint_number,
                   cat:    c.category,
                   risk:   c.risk_score
               }) AS complaints
        """
        async with neo4j_session() as session:
            result = await session.run(
                cypher, entity_type=entity_type, value=value, depth=depth
            )
            record = await result.single()
            if not record:
                return {}
            return dict(record)

    async def detect_campaigns(self, min_complaints: int = 3) -> List[Dict]:
        """
        Detect potential scam campaigns: clusters of complaints
        sharing multiple high-risk entities.
        """
        cypher = """
        MATCH (e:Entity)<-[:CONTAINS]-(c:Complaint)
        WHERE e.seen_count >= $min_complaints
        WITH e, collect(DISTINCT c) AS complaints, count(DISTINCT c) AS complaint_count
        WHERE complaint_count >= $min_complaints
        WITH e, complaints, complaint_count
        ORDER BY complaint_count DESC
        LIMIT 20

        // Find other entities shared by these same complaints
        UNWIND complaints AS c
        MATCH (c)-[:CONTAINS]->(e2:Entity)
        WHERE e2.seen_count >= $min_complaints AND e2 <> e
        WITH e, complaints, complaint_count,
             collect(DISTINCT e2) AS sibling_entities

        RETURN e.type                AS pivot_entity_type,
               e.value               AS pivot_entity_value,
               e.risk_score          AS pivot_risk,
               complaint_count,
               [c IN complaints | c.complaint_id]   AS complaint_ids,
               [c IN complaints | c.category][0..1] AS categories,
               size(sibling_entities)                AS correlated_entity_count
        ORDER BY complaint_count DESC, pivot_risk DESC
        """
        async with neo4j_session() as session:
            result = await session.run(cypher, min_complaints=min_complaints)
            return [dict(r) async for r in result]

    async def get_entity_risk_profile(
        self, entity_type: str, value: str
    ) -> Dict:
        """
        Get full risk profile for an entity:
        appearance count, associated complaints, campaign membership.
        """
        cypher = """
        MATCH (e:Entity {type: $entity_type, value: $value})
        OPTIONAL MATCH (c:Complaint)-[:CONTAINS]->(e)
        RETURN e.type         AS type,
               e.value        AS value,
               e.seen_count   AS total_appearances,
               e.risk_score   AS risk_score,
               e.first_seen   AS first_seen,
               e.last_seen    AS last_seen,
               collect(DISTINCT c.complaint_id) AS complaint_ids,
               avg(c.risk_score)                AS avg_complaint_risk,
               max(c.financial_loss)            AS max_financial_loss
        """
        async with neo4j_session() as session:
            result = await session.run(
                cypher, entity_type=entity_type, value=value
            )
            record = await result.single()
            return dict(record) if record else {}

    async def get_graph_stats(self) -> Dict:
        """Return platform-wide graph statistics for the dashboard."""
        cypher = """
        MATCH (c:Complaint) WITH count(c) AS total_complaints
        MATCH (e:Entity)    WITH total_complaints, count(e) AS total_entities
        MATCH ()-[r:CONTAINS]->() WITH total_complaints, total_entities, count(r) AS total_links
        MATCH (e2:Entity) WHERE e2.seen_count > 1
        RETURN total_complaints,
               total_entities,
               total_links,
               count(e2) AS recurring_entities
        """
        async with neo4j_session() as session:
            result = await session.run(cypher)
            record = await result.single()
            return dict(record) if record else {
                "total_complaints": 0,
                "total_entities": 0,
                "total_links": 0,
                "recurring_entities": 0,
            }

    async def get_full_graph(self, limit: int = 200) -> Dict:
        """
        Export nodes and edges for frontend graph visualization.
        Returns D3/vis.js compatible structure.
        """
        cypher = """
        MATCH (c:Complaint)-[r:CONTAINS]->(e:Entity)
        WITH c, e, r LIMIT $limit
        RETURN collect(DISTINCT {
                   id:       c.complaint_id,
                   label:    c.complaint_number,
                   type:     'complaint',
                   risk:     c.risk_score,
                   category: c.category
               }) AS complaints,
               collect(DISTINCT {
                   id:    e.type + ':' + e.value,
                   label: e.value,
                   type:  e.type,
                   risk:  e.risk_score,
                   count: e.seen_count
               }) AS entities,
               collect({
                   source: c.complaint_id,
                   target: e.type + ':' + e.value,
                   rel:    type(r)
               }) AS edges
        """
        async with neo4j_session() as session:
            result = await session.run(cypher, limit=limit)
            record = await result.single()
            if not record:
                return {"nodes": [], "edges": []}
            nodes = list(record["complaints"]) + list(record["entities"])
            return {"nodes": nodes, "edges": list(record["edges"])}


graph_engine = GraphCorrelationEngine()
