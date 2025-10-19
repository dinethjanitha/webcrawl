from scrapy.crawler import CrawlerProcess
from webscrapy.webscrapy.spiders.web_spider import WebSpider
from webscrapy.webscrapy.spiders.web_spider_new import WebCrawSpider
from connection.mongocon import mongoCon
from googlesearchmethod.googlesearch import googlesearch
from scrapy import signals
from pydispatch import dispatcher
from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from bson.objectid import ObjectId

load_dotenv("./env")

# Don't connect on import - only when needed
db = None

def get_db():
    """Lazy initialization - only connects when first called"""
    global db
    if db is None:
        db = mongoCon()
        if db is None:
            raise Exception("MongoDB connection failed! Check connection settings.")
    return db


# # Stored Keyword in mongoDB
def storeKeyword(keyword , siteDomain):
    mycol = get_db()["keyword"]
    mydict = {
        "keyword" : keyword,
        "siteDomain" : siteDomain,
    }
    try:
        x = mycol.insert_one(mydict)  
    except Exception as e:
        print(e)
        return None    
    print("xxxxxxxxxxxxxxxxxxxxxx")
    print(x)
    return x


# #Get details with keyword ID
def getKeywordById(id):
    mycol = get_db()["keyword"]
    try:
        result = mycol.find_one({"_id" : id})
    except Exception as e:
        print(e)
        return None    
    return result


# storedKeyword = storeKeyword("Sri lanka" , "lk")

# print(storedKeyword.inserted_id)

# resultMongo = getKeywordById(storedKeyword.inserted_id)
# print(resultMongo["_id"])


# # Add urls to keyword document
def storeRelevantUrls(keywordId):
    myCol = get_db()["keyword"]
    try:
        keywordDetails = getKeywordById(keywordId)
        
        keyword = keywordDetails["keyword"]
        siteDomain = keywordDetails["siteDomain"]

        results = googlesearch(keyword , siteDomain)

        urlList = []

        for item in results.get("items", []):
            print(f"Title: {item['title']}")
            urlList.append(item['link'])
            print(f"Link: {item['link']}\n")

        print(urlList)

        updatedValues = myCol.update_one({"_id" : keywordId} , {"$set" : {"urls" : urlList}})
        print("Updated Values")
        print(updatedValues)

        if updatedValues.acknowledged:
            print("Update successful!")
            result = keywordId
            return result    
        return None
    except Exception as e:
        print(e)
        return None


# updatedKey = storeRelevantUrls(storedKeyword.inserted_id)
# if not updatedKey:
#     print("Updated not successful")
# else : 
#     print("Output")
#     print(updatedKey)

#     updatedDetails = getKeywordById(updatedKey)
#     print("updated Details")
#     if "urls" in updatedDetails : 
#         print(updatedDetails["urls"])
#     else : 
#         print("Urls not set successfully!")
#         raise Exception("Urls not set successfully!")


# urls = updatedDetails["urls"]

# Crawl status checker success / not
def spider_closed(spider, reason):
    global crawl_done
    if reason == "finished":
        print("crawl done!")
        crawl_done = True
    else : 
        print("crawl failed!")
        crawl_done = False

# dispatcher.connect(spider_closed , signal=signals.spider_closed)

# Initialize crawl status flag
crawl_done = False

# #Crawl web data
# urls = ["https://en.wikipedia.org/wiki/Sri_Lanka" , "https://www.customs.gov.lk/"]

# process = CrawlerProcess()
# process.crawl(WebCrawSpider , start_urls=urls ,keywordId="68f485fbe80683cac7fafc93" )
# process.start()

# if crawl_done : 
#     print("It finished!")

def summarizeUsingAgent(keywordId):
    myKeywordCol = get_db()["keyword"]
    mySiteConCol = get_db()["sitesData"]
    joinAllContent = None

    print(keywordId)
    try:
        keywordDetails = myKeywordCol.find_one({'_id' : ObjectId(keywordId)})

        siteDataResults = mySiteConCol.find({'keywordId' : ObjectId(keywordId)})
        print("siteDataResults")
        # print(siteDataResults.to_list)
        mainKeyword = keywordDetails['keyword']
        print("mainKeyword")
        print(mainKeyword)
        content = []
        for document in siteDataResults:
            # print(document)
            content.append(document['content'])

        print("content")
        print(len(content))
        if len(content) > 0 :
            joinAllContent = "".join(content)
            print(joinAllContent)

        openai_key = os.getenv("GOOGLE_API_KEY")

        llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

        prompt = f"Summarize  the following and align that details with this keyword {mainKeyword} :{joinAllContent if joinAllContent else "Not text founded" }"

        print("Prompt: " , prompt)

        response = llm.invoke([HumanMessage(content=prompt)])

        # Print the result's content
        print(response.content) 

        return(response.content)
    except Exception as e:
        return "error"
        print(e)
    

# summarizeUsingAgent("68f485fbe80683cac7fafc93")


def exec():
    """
    WARNING: This function uses CrawlerProcess which CANNOT be used in FastAPI!
    CrawlerProcess blocks the event loop and will hang your server.
    
    For production, use Celery/background tasks or run Scrapy separately.
    """
    global crawl_done
    crawl_done = False  # Reset before crawling
    
    storedKeyword = storeKeyword("Travel Sigiriya" , "lk")
    # print(storedKeyword)
    # print(storedKeyword.inserted_id)

    resultMongo = getKeywordById(storedKeyword.inserted_id)
    keywordId = resultMongo["_id"]

    updatedKey = storeRelevantUrls(storedKeyword.inserted_id)
    if not updatedKey:
        print("Updated not successful")
        return {"error": "Failed to store URLs"}
    else : 
        print("Output")
        print(updatedKey)

        updatedDetails = getKeywordById(updatedKey)
        print("updated Details")
        if "urls" in updatedDetails : 
            print(updatedDetails["urls"])
        else : 
            print("Urls not set successfully!")
            raise Exception("Urls not set successfully!")

    urls = updatedDetails["urls"]

    dispatcher.connect(spider_closed , signal=signals.spider_closed)

    # WARNING: This will BLOCK FastAPI and may cause reactor errors
    process = CrawlerProcess()
    process.crawl(WebCrawSpider , start_urls=urls ,keywordId=updatedKey )
    process.start()

    if crawl_done : 
        print("It finished!")

    finalValue = summarizeUsingAgent(updatedKey)

    return finalValue

# exec()
# mycol = db["keyword"]
# try:
#     result = mycol.find_one({'_id' : ObjectId('68f485fbe80683cac7fafc93')})
#     print(result)
# except Exception as e:
#     print(e)
        