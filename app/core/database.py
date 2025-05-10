import os
from motor.motor_asyncio import AsyncIOMotorClient

# Używa zmiennej środowiskowej MONGO_URI lub domyślnej wartości
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27055")
client = AsyncIOMotorClient(mongo_uri)
db = client["scanalyze"]
users_collection = db["users"]