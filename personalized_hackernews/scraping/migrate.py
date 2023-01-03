# use previously parsed hnposts to parse sites data again using new data pipeline
from scraping.spider import HNSpider
from pymongo import MongoClient
from tqdm import tqdm
import requests
import os

EXCLUDE_SITE_SUFFIXES = ['.pdf', 'robots.txt', '.docx']

SRC_POST_DB_NAME = os.environ.get("POST_DB_NAME")

client = MongoClient("localhost", 27017, maxPoolSize=50)
db = client.hndb
collection = db[SRC_POST_DB_NAME]
docs = list(collection.find().sort('_id', 1))

spider = HNSpider()

for doc in tqdm(docs):
    src_url = doc['src_url'][0]
    # if src_url == 'https://github.com/carbon-language/carbon-lang':
    #     continue
    skip = False
    for exclude in EXCLUDE_SITE_SUFFIXES:
        if exclude in src_url:
            skip = True
    if skip:
        continue
    try:
        response = requests.get(src_url, timeout=10)
        content_type = response.headers.get('content-type')
        if 'application/pdf' in content_type:
            continue
    except:
        print('parsing src_url {} failed'.format(src_url))

    spider.parse_site(response, send_to_pipeline_manually=True) 

