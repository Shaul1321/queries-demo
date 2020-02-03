#http://localhost:8080/static/index2.html

from bottle import route, run, template, static_file, get, post
from collections import defaultdict, Counter
import json
import os
import pandas as pd
import pickle
import sklearn
from sklearn import cluster
from sklearn.decomposition import PCA
import numpy as np

def load_df(query_word):

     df = pd.read_pickle("data/df.query=lipase.pickle")
     return df

def load_states(query_word):

        vecs_path = "data/states.query=lipase.pickle"
        with open(vecs_path, "rb") as f:

                vecs = pickle.load(f)
        return vecs

@route('/query/<query_word>')
def get_word(query_word):
        df = load_df(query_word)
        vecs = load_states(query_word)

        df, vecs = df.head(200), vecs[:200]
        
        print("Performing PCA...")
        pca = PCA(n_components = min(300, len(vecs)))
        vecs_pca = pca.fit_transform(vecs)
        print("Done PCA. Explained vairance: {}".format(np.sum(pca.explained_variance_ratio_)))
        print("Performing clustering...")
        kmeans = sklearn.cluster.KMeans(n_clusters=100, random_state=0).fit(vecs_pca)
        print("Done.")
        df["cluster_id"] = kmeans.labels_

        return template('query_results.tpl', df = df)


@get('/query') # or @route('/login')
def get_clusters():

    return template('results.tpl', elements_by_freq = words_by_freq, type = "words")


@route('/index.html')
@route('/')
def server_static(filename='index.html'):
    return static_file(filename, root='./')

if __name__ == '__main__':
       
        
    run(host='localhost', port=8000)


