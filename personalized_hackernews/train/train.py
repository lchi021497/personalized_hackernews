# from nltk.corpus import stopwords
from collections import Counter
from pymongo import MongoClient
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler
from tqdm import tqdm

import gensim

# import nltk
import numpy as np
import matplotlib.pyplot as plt

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


if __name__ == "__main__":
    # two training pipelines
    # 1. titles
    # 2. paragraphs
    client = MongoClient("localhost", 27017, maxPoolSize=50)
    db = client.hndb
    collection = db["mongo_sites_2"]
    orig_docs = list(collection.find().sort("_id", 1))
    num_dropped = 0

    X = []
    to_keep = []
    exclude_site_processor = ExcludeSitePreProcessor(
        "exclude_site_preprocessor", EXCLUDE_SITES
    )
    for i, doc in tqdm(enumerate(orig_docs)):
        doc = exclude_site_processor.transform(doc)
        title_data, pgraph_data = transform_instance(
            doc, title_pipeline, pgraph_pipeline, DEBUG=DEBUG
        )

        if title_data and pgraph_data:
            doc_data = title_data + pgraph_data
            X.append(doc_data)
            to_keep.append(i)
        else:
            num_dropped += 1

    docs = [orig_docs[i] for i in to_keep]
    print("number of documents dropped: ", num_dropped)

    documents = [TaggedDocument(doc, [i]) for i, doc in enumerate(X)]

    print("making model...")
    model = Doc2Vec(
        documents, vector_size=50, window=8, min_count=1, workers=4, epochs=30
    )

    print("building vocab with model...")
    model.build_vocab(documents)

    print("training model...")
    model.train(
        documents, total_examples=model.corpus_count, epochs=model.epochs
    )

    ranks = []
    second_ranks = []
    X_vectors = []
    print("performing sanity check...")
    for doc_id in tqdm(range(len(docs))):
        inferred_vector = model.infer_vector(documents[doc_id].words)
        X_vectors.append(inferred_vector)
        sims = model.dv.most_similar([inferred_vector], topn=len(model.dv))
        rank = [docid for docid, sim in sims].index(doc_id)
        ranks.append(rank)

    second_ranks.append(sims[1])

    # sanity check
    counter = Counter(ranks)
    print(counter)

    # standardize X_vectors
    print("standardizing feature vectors...")
    scaler = MinMaxScaler()
    standardized_X_vectors = scaler.fit_transform(X_vectors)

    # save X_vectors and model
    print("saving gensim model...")
    model.save("gensim.model")

    # save vectors
    print("saving feature vectors...")
    with open("X_vectors.npy", "wb") as f:
        np.save(f, standardized_X_vectors)

    if DO_HYPTERTUNE:
        print("hypertuning kmeans parameters...")
        hypertune_kmeans(
            standardized_X_vectors, min_cluster=50, max_cluster=1000, step=20
        )

    # fit model
    print("fitting kmeans model...")
    kmeans = KMeans(n_clusters=30, random_state=3).fit(standardized_X_vectors)

    # save model
    print("saving kmeans model...")
    with open("model.pkl", "wb") as f:
        pickle.dump(kmeans, f)

    # analysis
    labels = kmeans.labels_
    centroids = kmeans.cluster_centers_

    # plot distance between centroids
    centroid_dists = []
    for centroidi in centroids:
        tmp = []
        for centroidj in centroids:
            tmp.append(np.linalg.norm(centroidj - centroidi))
        centroid_dists.append(tmp)
    centroid_dists = np.array(centroid_dists)

    plt.figure()
    plt.imshow(centroid_dists, cmap="hot", interpolation="nearest")
    plt.title("distance between centroids")
    plt.show()

    # plot label counts
    label_counts = Counter(labels)
    plt.figure()
    plt.bar(label_counts.keys(), label_counts.values())
    plt.title("count by label")
    plt.show()

    doc_len_by_labels = {}
    for i, doc in enumerate(documents):
        label = labels[i]
        doc_len = len(documents[i].words)

        doc_len_by_labels.setdefault(label, [])
        doc_len_by_labels[label].append(doc_len)

    plot_data = {
        label: np.mean(docs_len)
        for label, docs_len in doc_len_by_labels.items()
    }
    plt.figure()
    plt.bar(plot_data.keys(), plot_data.values())
    plt.title("document length by label")
    plt.show()

    print("saving labels...")
    with open("labels.npy", "wb") as f:
        np.save(f, labels)

    for i, label in enumerate(labels):
        docs[i]["label"] = label.item()
    # save docs to DB with labels
    db["filtered_hn_sites"].drop()
    collection = db["filtered_hn_sites"]
    collection.insert_many(docs)

    # plot PCA decomposition
    # pca = PCA(n_components=2)
    # X_transformed = pca.fit_transform(standardized_X_vectors)

    # plt.scatter(X_transformed[:,0], X_transformed[:, 1], c=kmeans.labels_)
    # plt.title("Kmeans clustering on 300-dimensional feature vectors")
    # plt.legend()
    # plt.show()


# class StripProcessor(PostProcessor):
#     def __init__(self, name):
#         PostProcessor.__init__(self, name)

#     def transform(self, doc, DEBUG=False):
#         doc = [_doc.strip() for _doc in doc]
#         return doc

# class SkipProcessor(PostProcessor):
#     def __init__(self, name, skip_criteria):
#         PostProcessor.__init__(self, name)
#         self.skip_criteria = skip_criteria
#         self.num_skips = 0

#     def transform(self, doc, DEBUG=False):
#         if self.skip_criteria(doc):
#             self.num_skips += 1
#             raise AbortException('skip criteria is met')
#         if DEBUG:
#             self.log(doc)
#         return doc

# class SplitProcessor(PostProcessor):
#     def __init__(self, name, split_type='sentence'):
#         PostProcessor.__init__(self, name)
#         self.split_way = split_type

#     def transform(self, words_lists, DEBUG=False):
#         # Params:
#         #   wordLists: list of words, could be sentence or paragraphs.
#         #   split_way: word, sentence, or paragraphs
#         assert self.split_way in ['word', 'sentence', 'paragraph']

#         if self.split_way == 'paragraph':
#             # split by sentence
#             raise NotImplemented('paragraph splitting not implemented yet.')

#         splits = []

#         if self.split_way == 'sentence':
#             # split by sentence
#             delimiter = '.'
#             for wl in words_lists:
#                 splits += wl.split(delimiter)
#         else:
#             # split by word
#             delimiter = ' '
#             for wl in words_lists:
#                 splits += wl.split(delimiter)

#         if DEBUG:
#             self.log(splits)
#         return splits

# class StopWordProcessor(PostProcessor):
#     def __init__(self, name, lang='english'):
#         PostProcessor.__init__(self, name)
#         punctuations = string.punctuation+'—”\'\’'

#         # get english stopwords
#         self.stopws = set(stopwords.words(lang))
#         # replace punctuations with whitespaces
#         self.translator = str.maketrans(punctuations, ' '*len(punctuations))

#     def transform(self, words_lists, DEBUG=False):
#         # Params:
#         #   wordLists: list of words, could be sentence or paragraphs.
#         tokens_lists = []
#         for wl in words_lists:
#             # get rid of punctuations
#             filtered_wl = wl.translate(self.translator).split()
#             # get rid of stop words
#             tokens = [token.lower() for token in filtered_wl if token.lower() not in self.stopws]
#             tokens_lists += tokens

#         if DEBUG:
#             self.log(tokens_lists)
#         return tokens_lists
