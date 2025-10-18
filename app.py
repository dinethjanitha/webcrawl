from scrapy.crawler import CrawlerProcess
from webscrapy.webscrapy.spiders.web_spider import WebSpider
from connection.mongocon import mongoCon

db = mongoCon()

#Crawl web data
urls = ["https://eta.gov.lk/" , "https://www.customs.gov.lk/"]

process = CrawlerProcess()
process.crawl(WebSpider , start_urls=urls)
process.start()