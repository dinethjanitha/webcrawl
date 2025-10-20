# from scrapy.crawler import CrawlerProcess
# from webscrapy.webscrapy.spiders.web_spider import WebSpider
# from webscrapy.webscrapy.spiders.web_spider_new import WebCrawSpider
# from connection.mongocon import mongoCon
from googlesearchmethod.googlesearch import googlesearch
# from scrapy import signals
# from pydispatch import dispatcher
from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from bson.objectid import ObjectId
from model.keyword import keyword_collection
from model.siteData import siteDataCollection
import subprocess
import sys

load_dotenv("./env")

# Stored Keyword in mongoDB
async def storeKeyword(keyword , siteDomain):
    mydict = {
        "keyword" : keyword,
        "siteDomain" : siteDomain,
    }
    try:
        x = await keyword_collection.insert_one(mydict) 
        print("---x----") 
        print(x) 
    except Exception as e:
        print(e)
        return None    
    print("xxxxxxxxxxxxxxxxxxxxxx")
    print(x)
    return x


# Get details with keyword ID
async def getKeywordById(id):
    try:
        result = await keyword_collection.find_one({"_id" : ObjectId(id)})
    except Exception as e:
        print(e)
        return None    
    return result


# Add urls to keyword document
async def storeRelevantUrls(keywordId):
    
    try:
        keywordDetails = await getKeywordById(keywordId)
        
        keyword = keywordDetails["keyword"]
        siteDomain = keywordDetails["siteDomain"]

        results = googlesearch(keyword , siteDomain)

        urlList = []

        for item in results.get("items", []):
            print(f"Title: {item['title']}")
            urlList.append(item['link'])
            print(f"Link: {item['link']}\n")

        print(urlList)

        updatedValues = await keyword_collection.update_one({"_id" : ObjectId(keywordId)} , {"$set" : {"urls" : urlList}})
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


# Crawl web data using subprocess
async def crawlUrls(urls, keywordId):
    """
    Runs the web crawler in a separate subprocess
    Returns: True if successful, False if failed
    """
    python_path = os.path.join(sys.prefix, "Scripts", "python.exe")  # Windows venv
    
    if not os.path.exists(python_path):
        python_path = os.path.join(sys.prefix, "bin", "python")  # Linux/Mac
    
    print("=" * 80)
    print("Starting crawler subprocess")
    print(f"Keyword ID: {keywordId}")
    print(f"Total URLs to crawl: {len(urls)}")
    print("=" * 80)
    
    try:
        # Run web_crawl_runner.py with URLs and keywordId as arguments
        process = subprocess.run(
            [python_path, "web_crawl_runner.py", *urls, str(keywordId)],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=300  # 5 minutes timeout
        )
        
        print("\n--- Crawler Output ---")
        print(process.stdout)
        
        if process.stderr:
            print("\n--- Crawler Warnings/Errors ---")
            print(process.stderr)
        
        print(f"\n--- Return Code: {process.returncode} ---")
        
        if process.returncode == 0:
            print("SUCCESS: Crawler completed successfully!")
            return True
        else:
            print(f"FAILED: Crawler failed with exit code {process.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("ERROR: Crawler timeout after 5 minutes")
        return False
    except Exception as e:
        print(f"ERROR: Subprocess exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def summarizeUsingAgent(keywordId):

    joinAllContent = None

    print(keywordId)
    try:
        keywordDetails = await keyword_collection.find_one({'_id' : ObjectId(keywordId)})

        siteDataResults = await siteDataCollection.find({'keywordId' : ObjectId(keywordId)}).to_list(length=None)
        print("siteDataResults")
        mainKeyword = keywordDetails['keyword']
        print("mainKeyword")
        print(mainKeyword)
        content = []
        for document in siteDataResults:
            content.append(document['content'])

        print("content")
        print(len(content))
        if len(content) > 0 :
            joinAllContent = "".join(content)
            print(f"Total content length: {len(joinAllContent)} characters")

        openai_key = os.getenv("GOOGLE_API_KEY")

        llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

        prompt = f"Summarize the following and align that details with this keyword {mainKeyword}: {joinAllContent if joinAllContent else 'No text found'}"

        print("Prompt length: ", len(prompt))

        

        response = llm.invoke([HumanMessage(content=prompt)])


        # Print the result's content
        print("Summary generated successfully!")
        print(response.content) 

        return response.content
    except Exception as e:
        print(f"Summarization error: {e}")
        return None


async def exec():
    """
    Complete workflow:
    1. Store keyword
    2. Fetch Google search URLs
    3. Crawl URLs (subprocess)
    4. Summarize content (only if crawl succeeds)
    """
    
    # Step 1: Store keyword
    print("\n" + "=" * 80)
    print("STEP 1: Storing keyword")
    print("=" * 80)
    storedKeyword = await storeKeyword("Travel Sigiriya", "lk")
    print(f"Keyword stored with ID: {storedKeyword.inserted_id}")

    # Step 2: Get keyword details
    print("\n" + "=" * 80)
    print("STEP 2: Fetching keyword details")
    print("=" * 80)
    resultMongo = await getKeywordById(storedKeyword.inserted_id)
    keywordId = resultMongo["_id"]

    # Step 3: Fetch Google URLs
    print("\n" + "=" * 80)
    print("STEP 3: Fetching Google search URLs")
    print("=" * 80)
    updatedKey = await storeRelevantUrls(storedKeyword.inserted_id)
    
    if not updatedKey:
        print("ERROR: Failed to store URLs")
        return {"error": "Failed to fetch URLs from Google"}
    
    # Get updated details with URLs
    updatedDetails = await getKeywordById(updatedKey)
    
    if "urls" not in updatedDetails or not updatedDetails["urls"]:
        print("ERROR: No URLs found!")
        return {"error": "No URLs found in Google search results"}
    
    urls = updatedDetails["urls"]
    print(f"Found {len(urls)} URLs to crawl")
    for i, url in enumerate(urls, 1):
        print(f"   [{i}] {url}")

    # Step 4: Crawl URLs
    print("\n" + "=" * 80)
    print("STEP 4: Starting web crawl")
    print("=" * 80)
    
    crawl_success = await crawlUrls(urls, updatedKey)
    
    if not crawl_success:
        print("ERROR: Crawl failed!")
        return {
            "error": "Web crawl failed",
            "keyword_id": str(updatedKey),
            "urls_attempted": len(urls)
        }
    
    # Step 5: Summarize (only if crawl succeeded)
    print("\n" + "=" * 80)
    print("STEP 5: Generating AI summary")
    print("=" * 80)
    
    finalValue = await summarizeUsingAgent(updatedKey)
    if finalValue == None :
        return {
        "status": "Summarization failed!",
    }
    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    
    return {
        "status": "success",
        "keyword_id": str(updatedKey),
        "urls_crawled": len(urls),
        "summary": finalValue
    }