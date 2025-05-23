import os
from motor.motor_asyncio import AsyncIOMotorClient

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27055")
client = AsyncIOMotorClient(mongo_uri)
db = client["scanalyze"]
users_collection = db["users"]