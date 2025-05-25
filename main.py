from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, user, product
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    path = request.url.path
    method = request.method
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    logger.info(f"{method} {path} - Status: {response.status_code} - Czas: {process_time:.3f}s")
    
    return response

app.include_router(auth.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["auth"])
app.include_router(user.router, prefix="/user", tags=["user"])
app.include_router(product.router)

@app.get("/")
async def root():
    return {"message": "Scanalyze API"}