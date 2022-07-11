import scrapy

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

    def check_list_len(self, list_name, mylist, expected_len):
        if (len(mylist) != expected_len):
            self.logger.error("[HNSpider ERROR] length of {} ({}) do not match length of title list({})".format(list_name, len(mylist), expected_len))

    def parse(self, response):
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

        for i in range(len(titles)):
            yield {'title': titles[i],
                   'src_url': src_urls[i],
                   'src': srcs[i],
                   'score': scores[i],
                   'author': authors[i],
                   'age': ages[i] }

        for url in src_urls:
            yield response.follow(url, self.reached_end_of_search)

    def reached_end_of_search(self, response):
        return {}


