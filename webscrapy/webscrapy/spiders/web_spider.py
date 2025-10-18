import scrapy

class WebSpider(scrapy.Spider):
    name = "dynamic_crawler"

    def __init__(self, start_urls=None, *args, **kwargs):
        super(WebSpider, self).__init__(*args, **kwargs)
        self.start_urls = start_urls or []

    def parse(self, response):
        # Extract all text from body, join with spaces, then strip
        body_text = " ".join(response.xpath("//body//text()").getall()).strip()
        print(body_text)
        yield {
            "url": response.url,
            "title": response.xpath("//title/text()").get(),
            "content": body_text
        }  
        
    