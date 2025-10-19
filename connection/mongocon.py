from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv("./.env")

CONNECTION_STRING = os.getenv("CONNECTION_STRING")

def mongoCon(): 
    # Don't print sensitive connection string
    try:
        client = MongoClient(CONNECTION_STRING)
        db = client["webcrawl"]
        print("MongoDB connection successful!")
        return db
    except Exception as e:
        print("MongoDB connection failed!")
        print(e)
        return None
    