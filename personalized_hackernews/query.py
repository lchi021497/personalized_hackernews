import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
from pymongo import MongoClient
import json
import string

MONGO_URI = 'mongodb://127.0.0.1:27017'
MONGO_DATABASE = 'hndb'

client = MongoClient(MONGO_URI)
db = client[MONGO_DATABASE]

documents = db['mongo_sites'].find({})

a = list(documents)
inst = a[-2]

paragraphs = ''.join(inst['paragraphs'])
stopws = set(stopwords.words('english'))

punctuations = string.punctuation+'—”\'\’'
translator = str.maketrans(punctuations, ' '*len(punctuations))
tokens = paragraphs.translate(translator).split()

tokens = [token for token in tokens if token.lower() not in stopws]


