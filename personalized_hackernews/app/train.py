# from nltk.corpus import stopwords
from collections import Counter
from pymongo import MongoClient
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler

import gensim

# import nltk
import numpy as np

# nltk.download('stopwords')
import pickle

DEBUG = False
EXCLUDE_SITES = set(["www.ft.com"])
DO_HYPTERTUNE = False


class DataPipeline:
    def __init__(self):
        self.postprocessors = []

    def transform(self, data, DEBUG=False):
        for pp in self.postprocessors:
            processor, _ = pp
            try:
                data = processor.transform(data, DEBUG=DEBUG)
            except AbortException as e:
                print("dropping example because of {}".format(e))
                return None
        return data

    def register_postprocessor(self, postprocessor, order):
        if not self.postprocessors:
            self.postprocessors = [(postprocessor, order)]
        else:
            # insert postprocessors according to order
            insert_idx = 0
            while (
                insert_idx < len(self.postprocessors)
                and order > self.postprocessors[insert_idx][1]
            ):
                insert_idx += 1

            self.postprocessors.insert(insert_idx, (postprocessor, order))


class Processor(object):
    def __init__(self, name, *args, **kwargs):
        self.name = name

    def transform(self, inputs):
        # input is list of words/sentences
        # output modified list
        pass

    def log(self, msg):
        print("[{}] {}".format(self.name.upper(), msg))


# Processors: these could be simple functions, if processing function is stateless, too
class AbortException(Exception):
    pass


class ExcludeSitePreProcessor(Processor):
    def __init__(self, name, exclude_sites):
        Processor.__init__(self, name)
        self.exclude_sites = set(exclude_sites)

    def transform(self, doc, DEBUG=False):
        if doc["href"][0] in self.exclude_sites:
            raise AbortException
        if DEBUG:
            self.log(doc)
        return doc


class GenSimProcessor(Processor):
    def __Init__(self, name):
        Processor.__init__(self, name)

    def transform(self, pgraphs, DEBUG=False):
        tokens_list = []
        for pgraph in pgraphs:
            tokens = gensim.utils.simple_preprocess(pgraph)

            if tokens:
                tokens_list.append(tokens)
        if DEBUG:
            self.log(tokens_list)
        return tokens_list


class WordCountLimitProcessor(Processor):
    def __init__(self, name, word_count_lb):
        Processor.__init__(self, name)
        self.word_count_thres = word_count_lb
        self.num_drops = 0

    def transform(self, word_list, DEBUG=False):
        if len(word_list) < self.word_count_thres:
            self.num_drops += 1
            raise AbortException("word count threshold is not met")
        if DEBUG:
            self.log(word_list)
        return word_list


class FlattenProcessor(Processor):
    def __init__(self, name):
        Processor.__init__(self, name)

    def transform(self, word_lists, DEBUG=False):
        return [word for word_list in word_lists for word in word_list]


title_pipeline = DataPipeline()
title_pipeline.register_postprocessor(
    GenSimProcessor("title_gensim_processor"), 30
)
title_pipeline.register_postprocessor(
    FlattenProcessor("title_flatten_processor"), 60
)
title_pipeline.register_postprocessor(
    WordCountLimitProcessor("title_word_limit_processor", 3), 70
)

pgraph_pipeline = DataPipeline()
pgraph_pipeline.register_postprocessor(
    GenSimProcessor("pgraph_gensim_processor"), 30
)
pgraph_pipeline.register_postprocessor(
    FlattenProcessor("pgraph_flatten_processor"), 60
)
pgraph_pipeline.register_postprocessor(
    WordCountLimitProcessor("pgraph_word_limit_processor", 1000), 70
)


def transform_instance(doc, title_pipeline, pgraph_pipeline, DEBUG=False):
    titles = doc["title"]
    if type(titles) is not list:
        titles = [titles]  # make title to list to concatenate with subtitles
    subtitles = doc.get("subtitles", [])
    titles = titles + subtitles
    print("[INFO] transforming doc {}".format(doc["href"]))
    title_data = title_pipeline.transform(titles, DEBUG=DEBUG)

    pgraphs = doc.get("paragraphs", [])
    pgraph_data = pgraph_pipeline.transform(pgraphs, DEBUG=DEBUG)

    return title_data, pgraph_data


def hypertune_kmeans(X_vectors, min_cluster=5, max_cluster=30, step=5):
    # fit kmeans with different n_clusters, returning the "elbow" of the error curve
    num_clusters = range(min_cluster, max_cluster, step)
    ave_dists = []
    for n in num_clusters:
        kmeans = KMeans(n_clusters=n, random_state=0).fit(X_vectors)

        labels = kmeans.labels_
        ave_dist = np.sum(
            np.sum(
                np.square(X_vectors - kmeans.cluster_centers_[kmeans.labels_])
            )
        ) / len(X_vectors)
        ave_dists.append(ave_dist)

    plt.figure()
    plt.plot(num_clusters, ave_dists)
    plt.title("kmeans hyptertune")
    plt.show()

