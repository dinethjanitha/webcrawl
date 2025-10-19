from pathlib import Path
from connection.mongocon import mongoCon
from bson.objectid import ObjectId
from bs4 import BeautifulSoup
import scrapy


db = mongoCon()

myCol = db["sitesData"]

class WebCrawSpider(scrapy.Spider):
    name = "WebSpider"
    
    

    def __init__(self,start_urls=None, keywordId=None ,  *args, **kwargs):
        super(WebCrawSpider , self).__init__(*args, **kwargs)
        self.start_urls = start_urls or []
        self.keywordId = keywordId or ""

        # global keywordID
        # keywordId = self.keywordId

        if not self.keywordId or not self.start_urls:
            raise Exception("Keyword id or sites url not found!")

    def parse(self, response):
        # body_text = " ".join(response.xpath("//body//text()").getall()).strip()
        soup = BeautifulSoup(response.text , "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "svg", "meta"]):
            tag.decompose()

        # page = response.url.split("/")[-2]
        # print(page)
        body_text = " ".join(soup.get_text(separator=" ").split())

        data = {"keywordId" : ObjectId(self.keywordId) , "siteUrl" : response.url , "content" : body_text }

        print(data)
        
        try:
            result = myCol.insert_one(data)
        except Exception as e:
            print(e)

        print(result)
        print("body_text--------------------------------------------------------------------------------------")
        # print(body_text)