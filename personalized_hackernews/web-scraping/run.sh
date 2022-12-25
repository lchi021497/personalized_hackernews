#!/bin/bash

source venv/bin/activate
export POST_DB_NAME="mongo_hnposts_1"
export SITE_DB_NAME="mongo_sites_1"

scrapy runspider spider.py --logfile=logfile
