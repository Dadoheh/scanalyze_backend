import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "test")


class Neo4jService:
    def __init__(self):
        self._driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self):
        self._driver.close()

    async def run_query(self, query, parameters=None):
        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

# Singleton instance
neo4j_service = Neo4jService()

async def get_neo4j():
    """Dependency for Neo4j service."""
    try:
        yield neo4j_service
    finally:
        pass