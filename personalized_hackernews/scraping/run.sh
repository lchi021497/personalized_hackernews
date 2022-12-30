#!/bin/zsh

source ../venv/bin/activate
export POST_DB_NAME="mongo_hnposts_2"
export SITE_DB_NAME="mongo_sites_2"

export PATH=$PATH:/opt/anaconda3/bin
# export PROJECT_HOME='' # export project home dir
export PYTHONPATH=${PROJECT_HOME}/personalized_hackernews

scrapy runspider spider.py
