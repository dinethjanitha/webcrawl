from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv("./.env")

MONGO_URL = os.getenv("CONNECTION_STRING")

client = AsyncIOMotorClient(MONGO_URL)
db = client["webcrawl"]