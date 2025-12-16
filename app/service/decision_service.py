from typing import List, Dict, Any
from app.core.neo4j_client import neo4j_client

async def decide_product(user_email: str, product_id: str, preferred_routes: List[str] = None) -> List[Dict[str, Any]]:
    routes = [r.lower() for r in (preferred_routes or ["dermal"])]
    cypher = """
    MATCH (u:User {email: $uid})-[:HAS_CONDITION]->(c:Condition)
    WITH collect(c.name) AS conds
    MATCH (p:Product {id: $pid})-[:CONTAINS]->(i:Ingredient)-[:HAS_HAZARD]->(h:Hazard)
    WHERE h.route IN $routes
    OPTIONAL MATCH (h)-[:CAUSES]->(e:Effect)
    WITH i, h, collect(e.name) AS effects, conds
    WITH i, h, effects,
         // prosta reguła powiązań Condition × Effect
         CASE 
           WHEN 'sensitive_skin' IN conds AND 'irritation' IN effects THEN 0.8
           WHEN 'allergies' IN conds AND 'sensitization' IN effects THEN 0.9
           ELSE 0.3
         END AS profile_boost,
         CASE h.severity WHEN 'high' THEN 0.9 WHEN 'medium' THEN 0.6 ELSE 0.3 END AS hazard_w
    RETURN i.inci AS inci, i.key AS ingredient_key,
           h.type AS hazard_type, h.value AS hazard_value, h.unit AS unit, h.route AS route,
           effects AS effects,
           round(100*(profile_boost*0.6 + hazard_w*0.4)) AS risk_score
    ORDER BY risk_score DESC
    """
    return await neo4j_client.run(cypher, {"uid": user_email, "pid": product_id, "routes": routes})