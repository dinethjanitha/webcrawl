from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv("./.env")

CONNECTION_STRING = os.getenv("CONNECTION_STRING")

def mongoCon(): 
    print(CONNECTION_STRING)
    try:
        client = MongoClient(CONNECTION_STRING)
        db = client["webcrawl"]
        
        print("Connection success!")
        return db
    except Exception as e:
        print("Connection fail!")
        print(e)
        return None
    