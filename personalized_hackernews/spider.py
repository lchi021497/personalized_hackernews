import scrapy
from scrapy.loader import ItemLoader
from time import strftime, gmtime
from items import SiteItem, HNItem

class HNEntry:
    def __init__(self, title, src_url, src, score, author, age):
       self.title = title
       self.src_url = src_url
       self.src = src
       self.score = score
       self.author = author
       self.age = age

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
 
    def check_list_len(self, list_name, mylist, expected_len):
        if (len(mylist) != expected_len):
            self.logger.error("[HNSpider ERROR] length of {} ({}) do not match length of title list({})".format(list_name, len(mylist), expected_len))

    def parse(self, response):
        print("SETTINGS: ", dict(self.settings["ITEM_PIPELINES"]))
        entries = response.css("td")
        titles = entries.css(".title a::text").getall()
        src_urls = entries.css(".title a.titlelink::attr(href)").getall()
        srcs = entries.css(".title .sitebit a span::text").getall()
        scores = entries.css(".subtext .score::text").getall()
        authors = entries.css(".subtext .hnuser::text").getall()
        ages = entries.css(".subtext .age a::text").getall()

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

        l = ItemLoader(item=HNItem(), response=response)
        for i in range(len(titles)):
            l.add_value("post_title", titles[i])
            l.add_value("src_url", src_urls[i])
            l.add_value("src", srcs[i])
            l.add_value("score", scores[i])
            l.add_value("author", authors[i])
            l.add_value("age", ages[i])
            yield l.load_item()

        for url in src_urls:
            if url != "https://begriffs.com/posts/2022-07-17-debugging-gdb-ddd.html":
                yield response.follow(url, self.parse_site)

    def parse_site(self, response):
        l = ItemLoader(item=SiteItem(), response=response)
        l.add_css("title", "title::text")
        l.add_css("title", "h1::text")
        l.add_css("subtitles", "h2::text")
        l.add_css("subtitles", "h3::text")
        l.add_css("paragraphs", "p::text")
        l.add_xpath("paragraphs", '//div[@class="body"]')
        l.add_value("href", response.url)
        l.add_css("relevantHrefs", "body a::text")
        l.add_css("date", "time::text")
        l.add_value("parsedDate", strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()))
        
        return l.load_item()


