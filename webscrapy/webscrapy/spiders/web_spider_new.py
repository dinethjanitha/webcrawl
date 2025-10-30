from pathlib import Path
from bson.objectid import ObjectId
from bs4 import BeautifulSoup
import scrapy
import pymongo
from dotenv import load_dotenv
import os
from urllib.parse import urlparse, urljoin

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
        'CLOSESPIDER_PAGECOUNT': 5,  # Stop after 100 pages
    }

    def __init__(self, start_urls=None, keywordId=None, *args, **kwargs):
        super(WebCrawSpider, self).__init__(*args, **kwargs)

        if not start_urls[0].startswith("https://"):
            start_urls[0] = "https://" + start_urls[0]

        self.start_urls = [start_urls[0]] or []
        self.keywordId = keywordId or ""
        self.client = pymongo.MongoClient(CONNECTION_STRING)
        self.db = self.client['webcrawl']
        self.collection = self.db['sitesData']
        
        # Track progress and visited URLs
        self.processed_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.visited_urls = set()
        self.max_pages = 100  # Maximum pages to crawl
        
        # Extract allowed domains from start_urls
        self.allowed_domains = set()
        for url in self.start_urls:
            domain = urlparse(url).netloc
            self.allowed_domains.add(domain)
        
        print("=" * 80)
        print("WebSpider Initialized")
        print(f"Keyword ID: {self.keywordId}")
        print(f"Allowed domains: {', '.join(self.allowed_domains)}")
        print(f"Maximum pages to crawl: {self.max_pages}")
        print(f"Initial URLs to crawl: {len(self.start_urls)}")
        for i, url in enumerate(self.start_urls, 1):
            print(f"   [{i}] {url}")
        print("=" * 80)
        
        if not self.keywordId or not self.start_urls:
            raise Exception("Keyword id or sites url not found!")

    def parse(self, response):
        """Parse each URL - called automatically for each URL in start_urls"""
        # Check if max pages reached
        if self.processed_count >= self.max_pages:
            print(f"\nMax pages limit ({self.max_pages}) reached. Stopping crawler.")
            return
        
        # Skip if already visited
        if response.url in self.visited_urls:
            return
        
        self.visited_urls.add(response.url)
        self.processed_count += 1
        
        print(f"\n[{self.processed_count}/{self.max_pages}] Processing: {response.url}")
        
        try:
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract image URLs
            image_urls = []
            for img in soup.find_all('img'):
                img_src = img.get('src') or img.get('data-src')
                if img_src:
                    # Convert relative URLs to absolute
                    absolute_img_url = urljoin(response.url, img_src)
                    image_urls.append(absolute_img_url)
            
            # Remove duplicate image URLs
            image_urls = list(set(image_urls))

            # Remove unwanted tags
            for tag in soup(["script", "style", "noscript", "header", "footer", "svg", "meta"]):
                tag.decompose()

            # Extract clean text
            body_text = " ".join(soup.get_text(separator=" ").split())

            # Prepare data
            data = {
                "keywordId": ObjectId(self.keywordId),
                "siteUrl": response.url,
                "content": body_text,
                "imageUrls": image_urls
            }

            # Save to MongoDB
            result = self.collection.insert_one(data)
            self.success_count += 1
            
            print(f"SUCCESS - SAVED to MongoDB!")
            print(f"   Document ID: {result.inserted_id}")
            print(f"   Content length: {len(body_text)} characters")
            print(f"   Images found: {len(image_urls)}")
            
            # Extract and follow links from the same domain
            # Only if we haven't reached max pages
            if self.processed_count < self.max_pages:
                links_found = 0
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(response.url, href)
                    
                    # Check if link belongs to allowed domain
                    link_domain = urlparse(absolute_url).netloc
                    
                    if link_domain in self.allowed_domains and absolute_url not in self.visited_urls:
                        links_found += 1
                        print(f"   Found new link: {absolute_url}")
                        yield scrapy.Request(absolute_url, callback=self.parse)
                
                if links_found > 0:
                    print(f"   Queued {links_found} new links from this page")
            else:
                print(f"   Reached max page limit - not queuing more links")
            
        except Exception as e:
            self.fail_count += 1
            print(f"FAILED: {response.url}")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def closed(self, reason):
        """Called when spider finishes - print summary"""
        print("\n" + "=" * 80)
        print(f"Spider Finished: {reason}")
        print("Results:")
        print(f"   Initial URLs: {len(self.start_urls)}")
        print(f"   Maximum pages limit: {self.max_pages}")
        print(f"   Total Processed: {self.processed_count}")
        print(f"   Success: {self.success_count}")
        print(f"   Failed: {self.fail_count}")
        print(f"   Unique URLs visited: {len(self.visited_urls)}")
        print("=" * 80)
        
        # Close MongoDB connection
        if hasattr(self, 'client'):
            self.client.close()