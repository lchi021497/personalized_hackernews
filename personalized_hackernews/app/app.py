from flask import Flask, render_template, request
from pymongo import MongoClient
from gensim.models.doc2vec import Doc2Vec
from train import transform_instance, pgraph_pipeline, title_pipeline
from collections import Counter

import joblib
import numpy as np
import pickle

with open("model.pkl", "rb") as f:
    clf2 = pickle.load(f)

MONGO_ADDRESS = '3.85.159.141'
MONGO_PORT = 80

app = Flask("personalized hackernews", template_folder="templates")

client = MongoClient(MONGO_ADDRESS, 80, maxPoolSize=20)
db = client.hndb
collection = db["filtered_hn_sites"]
docs = list(collection.find().sort("_id", 1))

kmeans_model = pickle.load(open("model.pkl", "rb"))
gensim_model = Doc2Vec.load("gensim.model")

labels = kmeans_model.labels_
centroids = kmeans_model.cluster_centers_

X_vectors = np.load("X_vectors.npy")
print('ready to serve')

def pick_samples_of_label(
    doc_vecs, labels, of_label, doc_vec, sample=10, top=10
):
    # pick docs that are closest to of_label, sampling `sample` amount
    # and picking the `top` ones
    label_idxs = np.equal(labels, of_label).nonzero()[0]
    label_vecs = doc_vecs[label_idxs]
    dists = np.linalg.norm(label_vecs - doc_vec, axis=1)
    assert len(label_vecs) == len(
        label_idxs
    ), f"Lengths must be same, but {len(label_vecs)} != {len(label_idxs)}"
    dists_idx = list(zip(dists, label_idxs))
    sorted_dists = sorted(dists_idx, key=lambda x: x[0])

    return [idx for _, idx in sorted_dists]


@app.route("/")
def index():
    return (render_template("index.html", table_data=[]), 200)


@app.route("/query")
def get_posts():
    keywords = request.args.get("keywords", default="")
    if keywords == "":
        return

    # pipeline expects list of words
    # relevant_doc = list(collection.find({ '$text': {'$search': keywords,
    #     '$caseSensitive': False}}))

    keywords = [word.strip() for word in keywords.split(",")]
    keywords_match = [{"paragraphs": {"$regex": kw}} for kw in keywords]
    print("keywords_match: ", keywords_match)
    relevant_doc = list(
        collection.aggregate(
            [
                {"$unwind": "$paragraphs"},
                {"$match": {"$or": keywords_match}},
                {"$group": {"_id": "$_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
        )
    )
    print("relevant doc by search by keyword: ", relevant_doc)

    if len(relevant_doc) == 0:
        return (
            render_template(
                "index.html",
                table_data=[],
            ),
            200,
        )

    relevant_doc_id = relevant_doc[0]["_id"]
    relevant_doc = collection.find_one({"_id": relevant_doc_id})

    title_data, pgraph_data = transform_instance(
        relevant_doc, title_pipeline, pgraph_pipeline, DEBUG=True
    )
    word_vec = title_data + pgraph_data
    feature_vec = gensim_model.infer_vector(word_vec).reshape(1, -1)
    scaler_filename = "scaler.save"
    scaler = joblib.load(scaler_filename)

    doc_label = kmeans_model.predict(scaler.transform(feature_vec))[0]

    # related docs to keywords
    related_docs_idxs = pick_samples_of_label(
        X_vectors, labels, doc_label, feature_vec
    )

    related_docs = [docs[i] for i in related_docs_idxs]

    return (render_template("index.html", table_data=related_docs), 200)
