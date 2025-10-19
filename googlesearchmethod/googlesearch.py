#Goolge search API
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

load_dotenv("./.env")

api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
cse_id = os.getenv("CUSTOM_SEARCH_ENGIN_ID")

def googlesearch(keyword , siteDomain):
    if siteDomain == "" or siteDomain == None:
        siteDomain = "com"
    try : 
        service = build("customsearch", "v1", developerKey=api_key)
        results = service.cse().list(
            q=keyword,
            cx=cse_id,
            num=10,  # Number of results to return (max 10)
            cr="sri lanka",
            siteSearch=siteDomain
    ).execute()
    except Exception as e :
        print(e)

    if not results : 
        return None
    
    return results