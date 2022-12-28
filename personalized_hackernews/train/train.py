from nltk.corpus import stopwords
from pymongo import MongoClient
import nltk
nltk.download('stopwords')
import string
import tqdm

DEBUG = False

class DataPipeline:
    def __init__(self):
        self.postprocessors = []

    def transform(self, data):
        for pp in self.postprocessors:
            processor, _ = pp
            data = processor.transform(data)
        return data

    def register_postprocessor(self, postprocessor, order):
        if not self.postprocessors:
            self.postprocessors = [(postprocessor, order)]
        else:
            # insert postprocessors according to order
            insert_idx = 0
            while insert_idx < len(self.postprocessors) and order > self.postprocessors[insert_idx][1]:
                insert_idx += 1

            self.postprocessors.insert(insert_idx, (postprocessor, order))

class PostProcessor(object):
    def __init__(self, name, *args, **kwargs):
        self.name = name

    def transform(self, inputs):
        # input is list of words/sentences
        # output modified list
        pass

    def log(self, msg):
        print('[{}] {}'.format(self.name.upper(), msg))

# Processors: these could be simple functions, if processing function is stateless, too
class AbortException(Exception):
    pass

class StripProcessor(PostProcessor):
    def __init__(self, name):
        PostProcessor.__init__(self, name)
    
    def transform(self, doc):
        doc = [_doc.strip() for _doc in doc]
        return doc
        
class SkipProcessor(PostProcessor):
    def __init__(self, name, skip_criteria):
        PostProcessor.__init__(self, name)
        self.skip_criteria = skip_criteria

    def transform(self, doc):
        if self.skip_criteria(doc):
            raise AbortException
        self.log(doc)
        return doc
    
class SplitProcessor(PostProcessor):
    def __init__(self, name, split_type='sentence'):
        PostProcessor.__init__(self, name)
        self.split_way = split_type

    def transform(self, words_lists):
        # Params:
        #   wordLists: list of words, could be sentence or paragraphs.
        #   split_way: word, sentence, or paragraphs
        assert self.split_way in ['word', 'sentence', 'paragraph']

        if self.split_way == 'paragraph':
            # split by sentence
            raise NotImplemented('paragraph splitting not implemented yet.') 

        splits = []

        print('words_list: ', words_lists)
        if self.split_way == 'sentence':
            # split by sentence
            delimiter = '.'
            for wl in words_lists:
                splits += wl.split(delimiter)
        else:
            # split by word
            delimiter = ' '
            for wl in words_lists:
                splits += wl.split(delimiter)

        self.log(splits)
        return splits

class StopWordProcessor(PostProcessor):
    def __init__(self, name, lang='english'):
        PostProcessor.__init__(self, name)
        punctuations = string.punctuation+'—”\'\’'

        # get english stopwords
        self.stopws = set(stopwords.words(lang))
        # replace punctuations with whitespaces
        self.translator = str.maketrans(punctuations, ' '*len(punctuations))
    
    def transform(self, words_lists):
        # Params:
        #   wordLists: list of words, could be sentence or paragraphs.
        tokens_lists = []
        for wl in words_lists:
            # get rid of punctuations
            filtered_wl = wl.translate(self.translator).split()
            # get rid of stop words
            tokens = [token.lower() for token in filtered_wl if token.lower() not in self.stopws]
            tokens_lists += tokens
        
        self.log(tokens_lists)
        return tokens_lists

class WordCountLimitProcessor(PostProcessor):
    def __init__(self, name, word_count_lb):
        PostProcessor.__init__(self, name)
        self.word_count_lb = word_count_lb

    def transform(self, sentences):
        return [sentence for sentence in sentences if len(sentence.split(' ')) > self.word_count_lb]

title_pipeline = DataPipeline()
title_pipeline.register_postprocessor(SkipProcessor('title_skip_processor', lambda x: any(map(lambda y: 'Are you a robot' in y, x))), 0)
title_pipeline.register_postprocessor(StripProcessor('title_strip_processor'), 20)
title_pipeline.register_postprocessor(SplitProcessor('title_split_processor', split_type='sentence'), 30)
title_pipeline.register_postprocessor(StopWordProcessor('title_stop_processor'), 40)
# title_pipeline.register_postprocessor(WordCountLimitProcessor('title_word_limit_processor', 3), 50)

pgraph_pipeline = DataPipeline()
pgraph_pipeline.register_postprocessor(StripProcessor('pgraph_strip_processor'), 0)
pgraph_pipeline.register_postprocessor(SplitProcessor('pgraph_split_processor', split_type='sentence'), 10)
pgraph_pipeline.register_postprocessor(StopWordProcessor('pgraph_stop_processor'), 20)
# pgraph_pipeline.register_postprocessor(WordCountLimitProcessor('pgraph_word_limit_processor', 10), 40)

if __name__ == '__main__':
    # two training pipelines
    # 1. titles
    # 2. paragraphs


    client = MongoClient("localhost", 27017, maxPoolSize=50)
    db = client.hndb
    collection = db['mongo_sites_1']
    docs = list(collection.find().sort('_id', 1))

    X = []
    to_keep = []
    for i, doc in tqdm.tqdm(enumerate(docs)):
        titles = doc['title']
        if type(title) is not list:
            titles = [titles] # make title to list to concatenate with subtitles
        #     subtitles = doc.get('subtitles', [])
        #     titles = title + subtitles

        try:
            print('raw titles: ', titles)
            title_data = title_pipeline.transform(titles)
            pgraph_data = pgraph_pipeline.transform(doc.get('paragraphs', []))

            doc_data = title_data + pgraph_data
            X.append(doc_data)
            to_keep.append(i)
        except AbortException:
            pass
    docs = [docs[i] for i in to_keep]