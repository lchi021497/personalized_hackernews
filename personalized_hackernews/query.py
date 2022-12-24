import nltk

nltk.download('stopwords')
import json
import string

from nltk.corpus import stopwords
from pymongo import MongoClient

MONGO_URI = 'mongodb://127.0.0.1:27017'
MONGO_DATABASE = 'hndb'

client = MongoClient(MONGO_URI)
db = client[MONGO_DATABASE]

sites = db['mongo_sites'].find({})
posts = db['mongo_hnposts'].find({})

a = list(sites)
b = list(posts)
inst = a[-2]

paragraphs = ''.join(inst['paragraphs'])
stopws = set(stopwords.words('english'))

punctuations = string.punctuation+'—”\'\’'
translator = str.maketrans(punctuations, ' '*len(punctuations))
tokens = paragraphs.translate(translator).split()

tokens = [token for token in tokens if token.lower() not in stopws]


