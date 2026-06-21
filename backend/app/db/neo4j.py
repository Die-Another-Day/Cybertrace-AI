from neo4j import AsyncGraphDatabase, AsyncDriver
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

_driver: AsyncDriver = None


async def get_neo4j_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=50,
        )
    return _driver


async def close_neo4j_driver():
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


@asynccontextmanager
async def neo4j_session() -> AsyncGenerator:
    driver = await get_neo4j_driver()
    async with driver.session() as session:
        yield session


async def init_graph_schema():
    """Create indexes and constraints on Neo4j graph."""
    constraints = [
        "CREATE CONSTRAINT entity_unique IF NOT EXISTS FOR (e:Entity) REQUIRE (e.type, e.value) IS UNIQUE",
        "CREATE CONSTRAINT complaint_id IF NOT EXISTS FOR (c:Complaint) REQUIRE c.complaint_id IS UNIQUE",
        "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
        "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
        "CREATE INDEX entity_risk IF NOT EXISTS FOR (e:Entity) ON (e.risk_score)",
        "CREATE INDEX complaint_status IF NOT EXISTS FOR (c:Complaint) ON (c.status)",
    ]
    async with neo4j_session() as session:
        for cypher in constraints:
            try:
                await session.run(cypher)
            except Exception as e:
                logger.warning(f"Schema init: {e}")
    logger.info("Neo4j graph schema initialized.")
