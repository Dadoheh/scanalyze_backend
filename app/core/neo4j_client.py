import os
from typing import Any, Dict, List, Optional
from neo4j import AsyncGraphDatabase, GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "scanalyze123")


class Neo4jClient:
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        await self._driver.close()

    async def run(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        async with self._driver.session() as session:
            result = await session.run(cypher, params or {})
            return [record.data() async for record in result]

neo4j_client = Neo4jClient()

async def ensure_constraints():
    cypher = """
    CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;
    CREATE CONSTRAINT cond_name IF NOT EXISTS FOR (c:Condition) REQUIRE c.name IS UNIQUE;
    CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE;
    CREATE CONSTRAINT ing_key IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.key IS UNIQUE;
    CREATE CONSTRAINT effect_name IF NOT EXISTS FOR (e:Effect) REQUIRE e.name IS UNIQUE;
    """
    await neo4j_client.run(cypher)