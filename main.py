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
from collections import Counter

FUNC_WORDS = set(["in", "on", "at", "the", "a", "an", "who", "that", "this", "which", "can",
                                     "cannot", "not", "no", "do", "does", "of", "these", "those", ",", ".", "'", "(",
                                     ")", "under", "above", "near", "without", "with", "have", "having", "has", "as", "nor", "am",
                                     "is", "are", "although", "while", "between", "neither", "and", "or",
                                     "among", "anything", "beside", "besides", "both", "off", "did", "nothing", "now",
                                     "over", "rather", "perhaps", "sometime", "such", "upon",
                                     "whereas", "where", "when", "who", "whom", "what", "why", "yes", "yet", "were", "was", "been", "be", "will", "would","could", "should", "amongst", "always", "along", "all", "afterwards", "after", "'s", "during", '"', "for", "from", "to", "into", "there", "instead", "-", ":", "-", ";", "?", "about", "but", "something", "out", "up", "it", "being", "just", "i", "'ve", "some", "against", "...", "'re", "much", "``", "''", "only", "least", "first", "n't", "its", "'ll", "--", "more", "such", "how", "by", "thus", "[", "]", "/", "sometime", "sometimes", "so", "even", "got", "gotten", "get", "due", "since", "because", "though", "however", "why", "off", "one", "very", "if", "until", "then", "than", "must", "through", "almost", "any", "may", "further", "less", "least", "worthy", "course", "before", "beforehand", "either", "whatever", "behalf", "well", "had", "need", "ought", "whether", "own", "according", "accordingly", "regarding", "you", "he", "mine", "our", "his", "her", "she", "my", "they", "their", "most", "!", "?", "each", "too", "once", "again", "soon", "apart", "enough", "few", "many", "forth", "thereafter", "several", "times", "ever", "simply", "specific", "per", "underneath", "beneath", "every", "er", "ed", "ing", "whole", "alone", "nearby", "within", "whom", "toward", "towards", "doesn't", "dont", "don't", "doesnt", "probably", "same", "other", "we", "nevertheless", "via", "already", "various", "still", "aftermath", "despite", "none", "i", "ii", "beyond", "also", "away", "prior", "below", "following", "here", "'s", "s", "me", "new", "united", "beyond", "your", "am", "at-large", "ie", "eg", "upstairs", "downstairs", "down", "anywhere", "everywhere", "else", "onto", "into", "across", "alongside", "##s", "##ly", "##out", "##ing", "##ifying", "##le", "##ivating", "##uate", "##set", "##ught", "##fly", "##ize", "##open", "##izes", "##i", "##r", "##l", "##ized", "##ally", "around", "onto", "behind", "forwards", "inside", "outside", "except", "ok", "<", "*", "also", "lot"])

def load_df(query_word):

     df = pd.read_pickle("data/df.query=lipase.pickle")
     return df

def load_states(query_word):

        vecs_path = "data/states.query=lipase.pickle"
        with open(vecs_path, "rb") as f:

                vecs = pickle.load(f)
        return vecs


def calculate_cluster_stats(df):

                # Collect counts for coocurring words

                cluster_common_words = []
                
                for clust_id in set(df["cluster_id"].tolist()):
                        counter = Counter()
                        
                        clust_sents = []
                        relevant = df[df["cluster_id"] == clust_id]
                        for i, row in relevant.iterrows():

                              sent = row["sentence_text"].split(" ")
                              clust_sents.extend([w for w in sent if w not in FUNC_WORDS])
                        
                        counter = Counter(clust_sents)
                        common_words_and_counts = counter.most_common(5000)
                        #common_words, _ = list(zip(*common_words_and_counts))
                        cluster_common_words.append(common_words_and_counts)

                total_count = Counter()
                for clust_data in cluster_common_words:

                        for w,c in clust_data:

                              total_count[w] += c

                # calculate PMI

                PMIs = []
                total_count_all = sum(total_count.values())
                for clust_data in cluster_common_words:

                      clust_pmis = []
                      clust_total_counts = sum([c for w,c in clust_data])

                      for w,count in clust_data:
                                
                                p1 = count / clust_total_counts
                                p2 = total_count[w] / total_count_all

                                pmi = np.log(p1 / p2)
                                clust_pmis.append((w, pmi))
                      
                      clust_pmis = sorted(clust_pmis, key = lambda pair: -pair[1])
                      PMIs.append(clust_pmis)

                return PMIs

                
                        

@route('/query/<query_word>')
def get_word(query_word):
        df = load_df(query_word)
        vecs = load_states(query_word)

        df, vecs = df.head(30000), vecs[:30000]
        
        print("Performing PCA...")
        pca = PCA(n_components = min(400, len(vecs)))
        vecs_pca = pca.fit_transform(vecs)
        print("Done PCA. Explained vairance: {}".format(np.sum(pca.explained_variance_ratio_)))
        print("Performing clustering...")
        kmeans = sklearn.cluster.KMeans(n_clusters=150, random_state=0).fit(vecs_pca)
        print("Done.")
        df["cluster_id"] = kmeans.labels_
        pmis = calculate_cluster_stats(df)
        clust_stats = {"pmis": pmis}

        return template('query_results.tpl', df = df, clust_stats = clust_stats)


@get('/query') # or @route('/login')
def get_clusters():

    return template('results.tpl', elements_by_freq = words_by_freq, type = "words")


@route('/index.html')
@route('/')
def server_static(filename='index.html'):
    return static_file(filename, root='./')

if __name__ == '__main__':
       
        
    run(host='localhost', port=8000)

