import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
from multiprocessing import Process
from pymongo import MongoClient
import os
import string
import tqdm

DEBUG = False

class TrainPipeline:
  def __init__(self):
    punctuations = string.punctuation+'—”\'\’'

    self.stopws = set(stopwords.words('english'))
    self.translator = str.maketrans(punctuations, ' '*len(punctuations))
    self.postprocessors = []

  def split(self, wordLists, split_way='sentence'):
    assert split_way == 'word' or split_way == 'sentence' or split_way == 'paragraph'

    if split_way == 'paragraph':
      return 

    splits = []

    if split_way == 'sentence':
      delimiter = '.'
      for wl in wordLists:
        splits.append(wl.split(delimiter))
    else:
      delimiter = ' '
      for wl in wordLists:
        splits += wl.split(delimiter)
    return splits 

  def elim_stopwords(self, wordLists):
    wl_tokens = []
    for wl in wordLists:
      filtered_wl = wl.translate(self.translator).split()
      tokens = [token.lower() for token in filtered_wl if token.lower() not in self.stopws]
      wl_tokens += tokens
    return wl_tokens

  def transform(self, doc):
    if DEBUG:
      print(doc.keys())
    title_outputs = self.transform_titles(doc['title'], doc.get('subtitles', []))
    pgraph_outputs = self.transform_paragraphs(doc.get('paragraphs', []))

    return (title_outputs, pgraph_outputs)

  def transform_titles(self, title, subtitles):
    if not isinstance(title, list):
      title = [title]

    titles = title + subtitles
    keywords = self.split(titles, split_way='word')
    return self.elim_stopwords(keywords)

  def transform_paragraphs(self, paragraphs):
    sentences = self.split(paragraphs, split_way='sentence')
    sentences = [self.elim_stopwords(s) for s in sentences]
    return sentences 

  def register_postprocessor(self, postprocessor, order):
    if not self.postprocessors:
      self.postprocessors = [(postprocessor, order)]
    else:
      insert_idx = 0
      while order > self.posprocessors[i]:
        insert_idx += 1

      self.postprocessors.insert(insert_idx, (postprocessor, order))
   
  def run_postprocessors(self, data):
    for pp in self.postprocessors:
      processor, _ = pp
      data = processor.transform(data)
    return data

class PostProcessors:
  def __init__(*args, **kwargs):
    raise AssertionError('Base class for post processors, not to be instantiated')

  def transform(self, inputs):
    # input is list of words/sentences
    # output modified list
    pass

class WordCountLimitProcessor:
  def __init__(self, word_count_lb):
    self.word_count_lb = word_count_lb

  def transform(self, sentences):
    return [sentence for sentence in sentences if len(sentence) > self.word_count_lb]

if __name__ == '__main__':
  pipeline = TrainPipeline()
  client = MongoClient("localhost", 27017, maxPoolSize=50)
  db = client.hndb
  collection = db['mongo_sites_1']
  docs = list(collection.find({}))

  titles = []
  for doc in tqdm.tqdm(docs):
    title_data, pgraph_data = pipeline.transform(doc)
    titles.append(title_data)
  # wc_processor = WordCountLimitProcessor(5)

  # pipeline.register_postprocessor(wc_processor, 5)
  # pgraph_data = pipeline.run_postprocessors(pgraph_data)
