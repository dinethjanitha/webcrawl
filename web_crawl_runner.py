from scrapy.crawler import CrawlerProcess
from webscrapy.webscrapy.spiders.web_spider import WebSpider
from webscrapy.webscrapy.spiders.web_spider_new import WebCrawSpider
from pydispatch import dispatcher
from scrapy import signals
import sys

def spider_closed(spider, reason):
    global crawl_done
    if reason == "finished":
        print("crawl done!")
        crawl_done = True
    else : 
        print("crawl failed!")
        crawl_done = False

dispatcher.connect(spider_closed , signal=signals.spider_closed)

urls = sys.argv[1:-1]
keywordId = sys.argv[-1]

print("-----------------------urls---------------------------")
print(urls)
print("-----------------------urls---------------------------")
    # WARNING: This will BLOCK FastAPI and may cause reactor errors
process = CrawlerProcess()
process.crawl(WebCrawSpider , start_urls=urls ,keywordId=keywordId )
process.start()

if crawl_done : 
        print("It finished!")