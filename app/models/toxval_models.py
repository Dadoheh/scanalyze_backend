from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..core.mysql_database import Base

class Chemical(Base):
    __tablename__ = "chemical"
    
    dtxsid = Column(String(45), primary_key=True)
    casrn = Column(String(45))
    name = Column(Text)
    
class Toxval(Base):
    __tablename__ = "toxval"
    
    toxval_id = Column(Integer, primary_key=True, autoincrement=True)
    chemical_id = Column(String(45))
    dtxsid = Column(String(45), index=True)
    source = Column(String(255))
    toxval_type = Column(String(255))
    toxval_numeric = Column(Float)
    toxval_units = Column(String(255))
    toxicological_effect = Column(Text)
    toxicological_effect_original = Column(Text)
    exposure_route = Column(String(255))
    exposure_route_original = Column(String(255))
    species_id = Column(Integer)
    species_original = Column(String(255))
    
class MvToxValDB(Base):
    __tablename__ = "mv_toxvaldb"
    
    id = Column(Integer, primary_key=True)
    dtxsid = Column(String(255), index=True)
    casrn = Column(String(45), index=True)
    name = Column(String(255))
    source = Column(String(255))
    toxval_type = Column(String(255))
    toxval_numeric = Column(Float)
    toxval_units = Column(String(255))
    risk_assessment_class = Column(String(255))
    human_eco = Column(String(255))
    study_type = Column(String(255))
    species_common = Column(String(255))
    exposure_route = Column(String(255))
    toxicological_effect = Column(Text)
    qc_category = Column(Text)

class MvSkinEye(Base):
    __tablename__ = "mv_skin_eye"
    
    id = Column(Integer, primary_key=True)
    dtxsid = Column(String(255))
    endpoint = Column(String(45))
    classification = Column(String(255))
    result_text = Column(String(1024))
    score = Column(String(45))
    species = Column(String(255))
    source = Column(String(45))

class MvCancerSummary(Base):
    __tablename__ = "mv_cancer_summary"
    
    id = Column(Integer, primary_key=True)
    dtxsid = Column(String(255))
    source = Column(String(255))
    exposure_route = Column(String(255))
    cancer_call = Column(String(255))
    source_url = Column(String(255))

class Species(Base):
    __tablename__ = "species"
    
    species_id = Column(Integer, primary_key=True)
    common_name = Column(String(255))
    latin_name = Column(String(255))
    kingdom = Column(String(255))