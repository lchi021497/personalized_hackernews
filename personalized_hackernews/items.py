# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field


class PersonalizedHackernewsItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class SiteItem(Item):
  title = Field()
  subtitles = Field()
  paragraphs = Field() 
  href = Field()
  relevantHrefs = Field()
  date = Field()
  parsedDate = Field(serializer=str)


class Blog(SiteItem):
  author = Field()
  blogHome = Field()
  tableHrefs = Field()
  tags = Field()

class GitHubRepo(SiteItem):
  about = Field()
  readme = Field()
  numStars = Field()
  numForks = Field()
  tags = Field()
  repoGroup = Field()
  contributers = Field()
  languages = Field()

class Arxiv(SiteItem):
  pdfHred = Field()
  authors = Field()

class pdfItem(Item):
  pdfHref = Field()
