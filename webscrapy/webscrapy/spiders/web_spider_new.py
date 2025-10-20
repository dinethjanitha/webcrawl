from pathlib import Path
from bson.objectid import ObjectId
from bs4 import BeautifulSoup
import scrapy
import pymongo
from dotenv import load_dotenv
import os

load_dotenv("./.env")

CONNECTION_STRING = os.getenv("CONNECTION_STRING")


class WebCrawSpider(scrapy.Spider):
    name = "WebSpider"
    
    # Custom settings
    custom_settings = {
        'ROBOTSTXT_OBEY': False,  # Bypass robots.txt blocking
        'CONCURRENT_REQUESTS': 1,  # Process URLs one at a time
        'DOWNLOAD_DELAY': 1,  # 1 second between requests
        'DOWNLOAD_TIMEOUT': 30,  # 30 second timeout per URL
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 2,
        'LOG_LEVEL': 'INFO',
        'CLOSESPIDER_TIMEOUT': 0,
        'CLOSESPIDER_PAGECOUNT': 0,
    }

    def __init__(self, start_urls=None, keywordId=None, *args, **kwargs):
        super(WebCrawSpider, self).__init__(*args, **kwargs)
        self.start_urls = start_urls or []
        self.keywordId = keywordId or ""
        self.client = pymongo.MongoClient(CONNECTION_STRING)

        self.db = self.client['webcrawl']
        self.collection = self.db['sitesData']
        
        # Track progress
        self.processed_count = 0
        self.success_count = 0
        self.fail_count = 0
        
        print("=" * 80)
        print("WebSpider Initialized")  # Removed emoji
        print(f"Keyword ID: {self.keywordId}")
        print(f"Total URLs to crawl: {len(self.start_urls)}")
        for i, url in enumerate(self.start_urls, 1):
            print(f"   [{i}] {url}")
        print("=" * 80)
        
        if not self.keywordId or not self.start_urls:
            raise Exception("Keyword id or sites url not found!")

    def parse(self, response):
        """Parse each URL - called automatically for each URL in start_urls"""
        self.processed_count += 1
        url_num = f"[{self.processed_count}/{len(self.start_urls)}]"
        
        print(f"\n{url_num} Processing: {response.url}")  # Removed emoji
        
        try:
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unwanted tags
            for tag in soup(["script", "style", "noscript", "header", "footer", "svg", "meta"]):
                tag.decompose()

            # Extract clean text
            body_text = " ".join(soup.get_text(separator=" ").split())

            # Prepare data
            data = {
                "keywordId": ObjectId(self.keywordId),
                "siteUrl": response.url,
                "content": body_text
            }

            # Save to MongoDB
            result = self.collection.insert_one(data)
            self.success_count += 1
            
            print(f"SUCCESS {url_num} SAVED to MongoDB!")  # Removed emoji
            print(f"   Document ID: {result.inserted_id}")
            print(f"   Content length: {len(body_text)} characters")
            
        except Exception as e:
            self.fail_count += 1
            print(f"FAILED {url_num}: {response.url}")  # Removed emoji
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def closed(self, reason):
        """Called when spider finishes - print summary"""
        print("\n" + "=" * 80)
        print(f"Spider Finished: {reason}")  # Removed emoji
        print("Results:")
        print(f"   Total URLs: {len(self.start_urls)}")
        print(f"   Processed: {self.processed_count}")
        print(f"   Success: {self.success_count}")
        print(f"   Failed: {self.fail_count}")
        print("=" * 80)
        
        # Close MongoDB connection
        if hasattr(self, 'client'):
            self.client.close()