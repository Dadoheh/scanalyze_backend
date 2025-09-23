from typing import Any, Dict, List, Optional
from app.core.neo4j_client import neo4j_client
from app.models.chemical_identity import ChemicalIdentityResult, ToxicologyData, BasicChemicalIdentifiers

def _ingredient_key(basic: Optional[BasicChemicalIdentifiers], tox: Optional[ToxicologyData], inci_name: str) -> str:
    if basic and basic.inchi_key:
        return basic.inchi_key.lower()
    if basic and basic.cas_number:
        return f"cas:{basic.cas_number}"
    if tox and tox.dtxsid:
        return f"dtxsid:{tox.dtxsid}"
    return f"inci:{inci_name.lower()}"

def _hazards_from_tox(tox: ToxicologyData) -> List[Dict[str, Any]]:
    hazards: List[Dict[str, Any]] = []
    # allergen_status → Effect: sensitization
    if tox.allergen_status:
        sev = "high" if "1a" in tox.allergen_status.lower() else ("medium" if "1b" in tox.allergen_status.lower() else "medium")
        hazards.append({
            "type": "allergen_status",
            "value": tox.allergen_status,
            "route": "dermal",
            "unit": "-",
            "species": "-",
            "effect": "sensitization",
            "severity": sev,
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    # irritation_potential → Effect: irritation
    if tox.irritation_potential:
        hazards.append({
            "type": "irritation",
            "value": tox.irritation_potential,
            "route": "dermal",
            "unit": "-",
            "species": "-",
            "effect": "irritation",
            "severity": "medium",
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    # sensitization_risk → Effect: sensitization
    if tox.sensitization_risk and not tox.allergen_status:
        hazards.append({
            "type": "sensitization_risk",
            "value": tox.sensitization_risk,
            "route": "dermal",
            "unit": "-",
            "species": "-",
            "effect": "sensitization",
            "severity": "medium",
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    # NOAEL
    if tox.noael_value is not None:
        hazards.append({
            "type": "NOAEL",
            "value": tox.noael_value,
            "route": "dermal",
            "unit": "mg/kg-day",
            "species": "-",
            "effect": "threshold",
            "severity": "low",
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    # DNEL/safe_concentration
    if tox.safe_concentration:
        hazards.append({
            "type": "DNEL",
            "value": tox.safe_concentration,
            "route": "dermal",
            "unit": "-",
            "species": "Human",
            "effect": "limit",
            "severity": "low",
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    # carcinogenicity
    if tox.carcinogenicity:
        hazards.append({
            "type": "carcinogenicity",
            "value": tox.carcinogenicity,
            "route": "dermal",
            "unit": "-",
            "species": "-",
            "effect": "cancer",
            "severity": "high",
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    return hazards

async def upsert_ingredient_from_identity(result: ChemicalIdentityResult):
    if not result or not result.found or not result.comprehensive_data:
        return
    basic = result.comprehensive_data.basic_identifiers
    tox = result.comprehensive_data.toxicology
    key = _ingredient_key(basic, tox, result.inci_name)

    await neo4j_client.run("""
    MERGE (i:Ingredient {key: $key})
    SET i.inci = $inci,
        i.cas = $cas,
        i.inchi_key = $inchi_key,
        i.dtxsid = $dtxsid
    """, {
        "key": key,
        "inci": result.inci_name,
        "cas": basic.cas_number if basic else None,
        "inchi_key": basic.inchi_key if basic else None,
        "dtxsid": tox.dtxsid if tox else None
    })

    if tox:
        hazards = _hazards_from_tox(tox)
        if hazards:
            await neo4j_client.run("""
            MATCH (i:Ingredient {key: $key})
            WITH i, $hazards AS hz
            UNWIND hz AS h
              MERGE (z:Hazard {
                type: h.type,
                route: toLower(h.route),
                unit: h.unit,
                species: h.species,
                value: h.value
              })
              SET z.severity = h.severity,
                  z.source = h.source,
                  z.confidence = h.confidence
              MERGE (i)-[:HAS_HAZARD]->(z)
              FOREACH (e IN CASE WHEN h.effect IS NULL THEN [] ELSE [h.effect] END |
                MERGE (ef:Effect {name: e})
                MERGE (z)-[:CAUSES]->(ef)
              )
            """, {"key": key, "hazards": hazards})

async def upsert_product(product_id: str, ingredient_keys: List[str]):
    await neo4j_client.run("""
    MERGE (p:Product {id: $pid})
    WITH p, $keys AS ks
    UNWIND ks AS k
      MERGE (i:Ingredient {key: k})
      MERGE (p)-[:CONTAINS]->(i)
    """, {"pid": product_id, "keys": ingredient_keys})

async def upsert_user_profile(user_id: str, conditions: List[str]):
    await neo4j_client.run("""
    MERGE (u:User {id: $uid})
    WITH u, $conds AS cs
    UNWIND cs AS c
      MERGE (cond:Condition {name: c})
      MERGE (u)-[:HAS_CONDITION]->(cond)
    """, {"uid": user_id, "conds": conditions})