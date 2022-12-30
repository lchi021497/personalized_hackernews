import os
from time import gmtime, strftime
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import scrapy
from scraping.items import HNItem, SiteItem
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from scraping.scrape import parse_paragraphs
import logging
from scrapy.utils.log import configure_logging 

# parse first ten pages of HN
configs = {
    'PAGE_DEPTH_LIMIT': 10, # number of pages to crawl on hackernews
    'UPVOTE_THRESHOLD': 20, # number of upvotes
    'PGRAPH_LEN_THRES': 30,
    'PGRAPH_ROLLING_WINDOW': 5,
    'EXCLUDE_SITE_SUFFIXES': ['.pdf', 'robots.txt'],
    'LOGFILE_NAME': 'logfile',
}


class HNSpider(scrapy.Spider):
    '''
       Spider that scrapes the hacker news page.
       Scrapes the title, source_url(to crawl), src domain``
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

    LOG_FILE = configs['LOGFILE_NAME']
    page_depth = 0

    configure_logging(install_root_handler=False)
    logging.basicConfig(
        filename=LOG_FILE,
        format='%(levelname)s: %(message)s',
        level=logging.INFO
    )

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
        for td in entries:
            entry = td.css(".title")
            subtext = td.css(".subtext")

            title = entry.css("a::text").get()
            if not title or title == "More":
                continue

            src_url = entry.css("a::attr(href)").get()
            src = entry.css(".sitebit a span::text").get()
            score = subtext.css(".score::text").get()
            author = subtext.css(".hnuser::text").get()
            age = subtext.css(".age a::text").get()

            # if score is None or int(score.split(' ')[0]) < configs['UPVOTE_THRESHOLD']:
            #     continue

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

        # sanity check: check that all fields have same length
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
            print('following url: ', url)
            if url is None:
                continue
            for suffix in configs['EXCLUDE_SITE_SUFFIXES']:
                if url.endswith(suffix):
                    continue
            # TODO: handle hn posts differently
            if urlparse(url).netloc == 'www.washingtonpost.com':
                break

            yield response.follow(url, self.parse_site)

        # parse more on later paginations
        if self.page_depth < configs['PAGE_DEPTH_LIMIT']:
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
 
        soup = BeautifulSoup(response.text, 'html.parser')
        pgraphs = soup.find_all('p')

        # for github sites, parse list as paragraphs
        domain = urlparse(response.url).netloc
        list_as_paragraph = (domain.find('github.com') != -1)
        parsed_paragraphs = parse_paragraphs(pgraphs, configs['PGRAPH_LEN_THRES'], configs['PGRAPH_ROLLING_WINDOW'], list_as_paragraph=list_as_paragraph)

        l.add_value("paragraphs", parsed_paragraphs)
        l.add_value("href", response.url)
        l.add_css("relevantHrefs", "body a::attr(href)")
        l.add_css("date", "time::text")
        l.add_value("last_update_time", now)
        l.add_value("insertion_time", now)
        
        # pass to pipeline
        return l.load_item()


