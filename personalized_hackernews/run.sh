#!/bin/bash

export POST_DB_NAME="mongo_hnposts_1"
export ITE_DB_NAME="mongo_sites_1"

source venv/bin/activate && scrapy runspider spider.py --logfile=logfile
