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
import pymongo

def get_time():
    return strftime("%Y-%m-%d %H:%M", gmtime())

class JLPipeline:
    def open_spider(self, spider, jl_dir, jl_name):
        self.file = open(os.path.join(jl_dir, jl_name), 'w')

    def close_spider(self, spider):
        self.file.close()


class JLPostPipeline(JLPipeline):
    def __init__(self):
        super(JLPostPipeline, self).__init__()

    def open_spider(self, spider):
        super().open_spider(spider, "hnposts", 'hn_{}.jl'.format(get_time()))

    def process_item(self, item, spider):
        if not isinstance(item, HNItem):
            return item
        adapter = ItemAdapter(item)
        line = json.dumps(adapter.asdict()) + "\n"
        self.file.write(line)

        return item

class JLSitePipeline(JLPipeline):
    collection_name = 'sites'

    def __init__(self):
        super(JLSitePipeline, self).__init__()

    def open_spider(self, spider):
        open_spider(spider, 'sites', 'sites_{}.jl'.format(get_time()))

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

class MongoPipeline:
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE', 'items')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        self.db[self.collection_name].insert_one(ItemAdapter(item).asdict())
        return item


class MongoPostPipeline(MongoPipeline):
    collection_name = 'mongo_hnposts'

    def __init__(self, mongo_uri, mongo_db):
        super(MongoPostPipeline, self).__init__(mongo_uri, mongo_db)

    def process_item(self, item, spider):
        if not isinstance(item, HNItem):
            return item

        self.db[self.collection_name].insert_one(ItemAdapter(item).asdict())
        return item

class MongoSitePipeline(MongoPipeline):
    collection_name = 'mongo_sites'
    def __init__(self, mongo_uri, mongo_db):
        super(MongoSitePipeline, self).__init__(mongo_uri, mongo_db)

    def process_item(self, item, spider):
        # pass item to downstream without doing anything
        if not isinstance(item, SiteItem):
            return item
        adapter = ItemAdapter(item)

        if adapter.get("title") == None or adapter.get("href") == None:
            raise DropItem("missing title or href")
        else:
            self.db[self.collection_name].insert_one(ItemAdapter(item).asdict())

            return item


