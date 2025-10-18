from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv("./.env")

CONNECTION_STRING = os.getenv("CONNECTION_STRING")

def mongoCon(): 
    print(CONNECTION_STRING)
    client = MongoClient(CONNECTION_STRING)
    db = client["webcrawl"]
    return db