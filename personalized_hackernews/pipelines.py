# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from items import SiteItem, HNItem
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from time import time, gmtime, strftime
import json
import os

def get_time():
    return strftime("%Y-%m-%d %H:%M", gmtime())

class HNPostPipeline:
    def open_spider(self, spider):
        self.file = open(os.path.join('hnposts', 'hn_{}.jl'.format(get_time())), 'w')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        if not isinstance(item, HNItem):
            return item
        adapter = ItemAdapter(item)
        line = json.dumps(adapter.asdict()) + "\n"
        self.file.write(line)

        return item

class SitePipeline:
    def open_spider(self, spider):
        self.file = open(os.path.join('sites', 'sites_{}.jl'.format(get_time())), 'w')

    def close_spider(self, spider):
        self.file.close()


    def process_item(self, item, spider):
        # pass item to downstream without doing anything
        if not isinstance(item, SiteItem):
            return item
        adapter = ItemAdapter(item)

        if adapter.get("title") == None or adapter.get("href") == None:
            raise DropItem("missing title or href")
        else:
            line = json.dumps(ItemAdapter(item).asdict()) + "\n"
            self.file.write(line)

            return item
