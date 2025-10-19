from scrapy.crawler import CrawlerProcess
from webscrapy.webscrapy.spiders.web_spider import WebSpider
from connection.mongocon import mongoCon
from googlesearchmethod.googlesearch import googlesearch
from scrapy import signals
from pydispatch import dispatcher

db = mongoCon()

if db == None:
    print("Connection failed! go and check connection please...")


def storeKeyword(keyword , siteDomain):
    mycol = db["keyword"]
    mydict = {
        "keyword" : keyword,
        "siteDomain" : siteDomain,
    }
    try:
        x = mycol.insert_one(mydict)  
    except Exception as e:
        print(e)
        return None    
    print(x)
    return x

def getKeywordById(id):
    mycol = db["keyword"]
    try:
        result = mycol.find_one({"_id" : id})
    except Exception as e:
        print(e)
        return None    
    return result


storedKeyword = storeKeyword("Sri lanka" , "lk")

print(storedKeyword.inserted_id)

resultMongo = getKeywordById(storedKeyword.inserted_id)
print(resultMongo["_id"])

def storeRelevantUrls(keywordId):
    myCol = db["keyword"]
    try:
        keywordDetails = getKeywordById(storedKeyword.inserted_id)
        
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


updatedKey = storeRelevantUrls(storedKeyword.inserted_id)
if not updatedKey:
    print("Updated not successful")
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

def spider_closed(spider, reason):
    global crawl_done
    if reason == "finished":
        print("crawl done!")
        crawl_done = True
    else : 
        print("crawl failed!")
        crawl_done = False

dispatcher.connect(spider_closed , signal=signals.spider_closed)




# print(x)
#Crawl web data
# urls = ["https://eta.gov.lk/" , "https://www.customs.gov.lk/"]

# process = CrawlerProcess()
# process.crawl(WebSpider , start_urls=urls , )
# process.start()