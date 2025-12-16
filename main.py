from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, user, product,  toxval 
import time
import logging

from app.core import neo4j_client
from app.core.neo4j_client import ensure_constraints

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    try:
        await ensure_constraints()
        logger.info("Neo4j constraints ensured")
    except Exception as e:
        logger.error(f"Neo4j init failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        await neo4j_client.neo4j_client.close()
        logger.info("Neo4j driver closed")
    except Exception as e:
        logger.warning(f"Neo4j close failed: {e}")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    path = request.url.path
    method = request.method
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    logger.info(f"{method} {path} - Status: {response.status_code} - Czas: {process_time:.3f}s")
    
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["auth"])
app.include_router(user.router, prefix="/user", tags=["user"])
app.include_router(toxval.router, prefix="/api/v1", tags=["toxval"])
app.include_router(product.router)

@app.get("/")
async def root():
    return {"message": "Scanalyze API"}
