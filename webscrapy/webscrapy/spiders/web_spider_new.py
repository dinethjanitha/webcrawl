from pathlib import Path

import scrapy


class WebCrawSpider(scrapy.Spider):
    name = "WebSpider"

    def __init__(self,start_urls=None, *args, **kwargs):
        super(WebCrawSpider , self).__init__(*args, **kwargs)
        self.start_urls = start_urls or []

    def parse(self, response):
        page = response.url.split("/")[-2]
        print(page)