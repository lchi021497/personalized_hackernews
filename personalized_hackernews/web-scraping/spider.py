import os
from time import gmtime, strftime
from urllib.parse import urlparse

import scrapy
from items import HNItem, SiteItem
from scrapy.loader import ItemLoader
from scrapy.selector import Selector

# parse first ten pages of HN
PAGE_DEPTH_LIMIT = 10

class HNSpider(scrapy.Spider):
    '''
       Spider that scrapes the hacker news page.
       Scrapes the title, source_url(to crawl), src domain,
       score, author, age of each page.
       
       Send Requests of the urls crawled to the scheduler
       that triggers other specific spiders (blog spider,
       forum spider, or news spider) to crawl different
       types of news sources.
    '''
    name = 'hn_spider'
    start_urls = [
        'https://news.ycombinator.com/',
    ]

    LOG_FILE = "logfile"
    page_depth = 0

    def check_list_len(self, list_name, mylist, expected_len):
        if (len(mylist) != expected_len):
            self.logger.error("[HNSpider ERROR] length of {} ({}) do not match length of title list({})".format(list_name, len(mylist), expected_len))

    def parse(self, response):
        # parse each entry in the table
        entries = response.css("td")

        titles = []
        src_urls = []
        srcs = []
        scores = []
        authors = []
        ages = []
        for td in response.css("td"):
            entry = td.css(".title")
            subtext = td.css(".subtext")

            title = entry.css("a::text").get()
            if not title or title == "More":
                continue

            src_url = entry.css("a.titlelink::attr(href)").get()
            src = entry.css(".sitebit a span::text").get()
            score = subtext.css(".score::text").get()
            author = subtext.css(".hnuser::text").get()
            age = subtext.css(".age a::text").get()

            # defaults
            if score == None:
                score = -1
            if author == None:
                author = ""

            titles.append(title)
            src_urls.append(src_url)
            srcs.append(src)
            scores.append(score)
            authors.append(author)
            ages.append(age)

        list_len = len(titles)
        self.check_list_len("src_urls", src_urls, list_len)
        self.check_list_len("srcs", srcs, list_len)
        self.check_list_len("scores", scores, list_len)
        self.check_list_len("authors", authors, list_len)
        self.check_list_len("ages", ages, list_len)

        now = strftime("%Y %b %d %H:%M:%S +0000", gmtime())
        for i in range(len(titles)):
            l = ItemLoader(item=HNItem(), selector=Selector(response=response))
            l.add_value("post_title", titles[i])
            l.add_value("src_url", src_urls[i])
            l.add_value("src", srcs[i])
            l.add_value("score", scores[i])
            l.add_value("author", authors[i])
            l.add_value("age", ages[i])
            l.add_value("last_update_time", now) 
            l.add_value("insertion_time", now)
            yield l.load_item()

        for url in src_urls:
            yield response.follow(url, self.parse_site)

        # parse more on later paginations
        if self.page_depth < PAGE_DEPTH_LIMIT:
            self.page_depth += 1
            next_page_path = response.css(".morelink::attr(href)").get() 
           
            self.logger.debug("[SPIDER_DEBUG] following more link ({})".format(next_page_path))
            yield response.follow(os.path.join(self.start_urls[0], next_page_path), self.parse)

    def parse_site(self, response):
        now = strftime("%Y %b %d %H:%M:%S +0000", gmtime())
        l = ItemLoader(item=SiteItem(), response=response)
        l.add_css("title", "title::text")
        l.add_css("title", "h1::text")
        l.add_css("subtitles", "h2::text")
        l.add_css("subtitles", "h3::text")
        l.add_css("paragraphs", "p::text")
        l.add_xpath("paragraphs", '//div[@class="body"]')
        l.add_value("href", response.url)
        l.add_css("relevantHrefs", "body a::attr(href)")
        l.add_css("date", "time::text")
        l.add_value("last_update_time", now)
        l.add_value("insertion_time", now)
        
        # pass to pipeline
        return l.load_item()


