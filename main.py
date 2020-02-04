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
from typing import List

FUNC_WORDS = set(["in", "on", "at", "the", "a", "an", "who", "that", "this", "which", "can",
                                     "cannot", "not", "no", "do", "does", "of", "these", "those", ",", ".", "'", "(",
                                     ")", "under", "above", "near", "without", "with", "have", "having", "has", "as", "nor", "am",
                                     "is", "are", "although", "while", "between", "neither", "and", "or",
                                     "among", "anything", "beside", "besides", "both", "off", "did", "nothing", "now",
                                     "over", "rather", "perhaps", "sometime", "such", "upon",
                                     "whereas", "where", "when", "who", "whom", "what", "why", "yes", "yet", "were", "was", "been", "be", "will", "would","could", "should", "amongst", "always", "along", "all", "afterwards", "after", "'s", "during", '"', "for", "from", "to", "into", "there", "instead", "-", ":", "-", ";", "?", "about", "but", "something", "out", "up", "it", "being", "just", "i", "'ve", "some", "against", "...", "'re", "much", "``", "''", "only", "least", "first", "n't", "its", "'ll", "--", "more", "such", "how", "by", "thus", "[", "]", "/", "sometime", "sometimes", "so", "even", "got", "gotten", "get", "due", "since", "because", "though", "however", "why", "off", "one", "very", "if", "until", "then", "than", "must", "through", "almost", "any", "may", "further", "less", "least", "worthy", "course", "before", "beforehand", "either", "whatever", "behalf", "well", "had", "need", "ought", "whether", "own", "according", "accordingly", "regarding", "you", "he", "mine", "our", "his", "her", "she", "my", "they", "their", "most", "!", "?", "each", "too", "once", "again", "soon", "apart", "enough", "few", "many", "forth", "thereafter", "several", "times", "ever", "simply", "specific", "per", "underneath", "beneath", "every", "er", "ed", "ing", "whole", "alone", "nearby", "within", "whom", "toward", "towards", "doesn't", "dont", "don't", "doesnt", "probably", "same", "other", "we", "nevertheless", "via", "already", "various", "still", "aftermath", "despite", "none", "i", "ii", "beyond", "also", "away", "prior", "below", "following", "here", "'s", "s", "me", "new", "united", "beyond", "your", "am", "at-large", "ie", "eg", "upstairs", "downstairs", "down", "anywhere", "everywhere", "else", "onto", "into", "across", "alongside", "##s", "##ly", "##out", "##ing", "##ifying", "##le", "##ivating", "##uate", "##set", "##ught", "##fly", "##ize", "##open", "##izes", "##i", "##r", "##l", "##ized", "##ally", "around", "onto", "behind", "forwards", "inside", "outside", "except", "ok", "<", "*", "also", "lot"])

def load_df(query_word):

     df = pd.read_pickle("data/df.query={}.pickle".format(query_word))
     return df

def load_states(query_word):

        vecs_path = "data/states.query={}.pickle".format(query_word)
        with open(vecs_path, "rb") as f:

                vecs = pickle.load(f)
        return vecs


def calculate_pmi_for_clusters(df, environment_extracting_func):

                # Collect counts for coocurring words

                total_count, cluster_common_words = collect_per_cluster_counts(df, environment_extracting_func)

                # calculate PMI

                PMIs = []
                total_count_all = sum(total_count.values())
                for clust_data in cluster_common_words:

                      clust_pmis = []
                      clust_total_counts = sum([c for w,c in clust_data])

                      for w,count in clust_data:
                                
                                p1 = count / clust_total_counts
                                p2 = total_count[w] / total_count_all

                                pmi = np.log(p1 / (p2 + 1e-4))
                                clust_pmis.append((w, pmi))
                      
                      clust_pmis = sorted(clust_pmis, key = lambda pair: -pair[1])
                      PMIs.append(clust_pmis)

                return PMIs


def collect_per_cluster_counts(df, environment_extracting_func, specific_POS = None):

                cluster_common_words = []
                
                for clust_id in set(df["cluster_id"].tolist()):
                        counter = Counter()
                        
                        clust_sents = []
                        relevant = df[df["cluster_id"] == clust_id]
                        for i, row in relevant.iterrows():

                              sent = row["sentence_text"].split(" ")
                              query_ind = row["word_first_index"]
                              window = environment_extracting_func(row, specific_POS)

                              clust_sents.extend([w for w in window if w not in FUNC_WORDS and w != sent[query_ind] ])
                        
                        counter = Counter(clust_sents)
                        common_words_and_counts = counter.most_common(2500)
                        #common_words, _ = list(zip(*common_words_and_counts))
                        cluster_common_words.append(common_words_and_counts)

                total_count = Counter()
                for clust_data in cluster_common_words:

                        for w,c in clust_data:

                              total_count[w] += c
                              
                
                return total_count, cluster_common_words
                              
                                             
def linear_window_environment(df_row, radius = 3, POS_to_keep = None):                       

        sent = df_row["lemma_seq"].split(" ")
        query_ind = df_row["word_first_index"]
        window = sent[max(0, query_ind - radius):min(len(sent) - 1, query_ind +radius + 1)]
        return window        

def entire_sentence_environment(df_row, radius = 3, POS_to_keep= None):                       

        sent = df_row["lemma_seq"].split(" ")
        query_ind = df_row["word_first_index"]
        window = sent[:]
        return window     

def entire_sentence_environment_per_POS(df_row, POS_to_keep):

        sent = df_row["lemma_seq"].split(" ")
        pos = df_row["pos_seq"].split(" ")
        query_ind = df_row["word_first_index"]
        window = [w for i,w in enumerate(sent) if ((POS_to_keep is None) or (pos[i] in POS_to_keep))]
        return window             

def perform_kmeans_clsutering(df, vecs,  num_clusts):

        print("Performing PCA...")
        pca = PCA(n_components = 0.9)
        vecs_pca = pca.fit_transform(vecs)
        print("Done PCA. Explained vairance: {}; num components: {}".format(np.sum(pca.explained_variance_ratio_), pca.n_components_))
        print("Performing clustering...")
        kmeans = sklearn.cluster.KMeans(n_clusters = num_clusts, random_state=0).fit(vecs_pca)
        print("Done.")
        df["cluster_id"] = kmeans.labels_


        # do pca on cluster means to get 1d ordering (to present similar clusters near each other)
        centers = kmeans.cluster_centers_
        pca = PCA(n_components = 1)
        scores = pca.fit_transform(centers)
        ordering_and_scores = sorted(zip(scores, set(kmeans.labels_.copy())), key = lambda pair: pair[0])
        _, labels_sorted = zip(*ordering_and_scores)
        #labels_sorted = np.array([x[0].item() for x in labels_sorted])
        #return labels_sorted
        return set(kmeans.labels_)
       
        

@route('/query/<query_word>')
def get_word(query_word):
        df = load_df(query_word)
        vecs = load_states(query_word)

        df, vecs = df.head(300000), vecs[:300000]
        labels_sorted = range(len(set(df["cluster_id"].tolist()))) #perform_kmeans_clsutering(df, vecs, num_clusts = 250)
        
        pmis_linear_window = calculate_pmi_for_clusters(df, entire_sentence_environment)
        _, common_nouns_linear_window = collect_per_cluster_counts(df, entire_sentence_environment_per_POS, ["NN", "NNS", "NNP", "NNPS"])
        _, common_verbs_linear_window = collect_per_cluster_counts(df, entire_sentence_environment_per_POS, ["VBD", "VBG", "VNB", "VBZ", "VB"])
        _, common_adjs_linear_window = collect_per_cluster_counts(df, entire_sentence_environment_per_POS, ["JJ", "JJR", "JJS", "CD", "CC"])
         
        clust_stats = {"pmis": pmis_linear_window, "common_nouns": common_nouns_linear_window, "common_verbs": common_verbs_linear_window, "common_adjectives": common_adjs_linear_window}

        return template('query_results.tpl', df = df, clust_stats = clust_stats, cluster_ids  = labels_sorted)


@get('/query') # or @route('/login')
def get_clusters():

    return template('results.tpl', elements_by_freq = words_by_freq, type = "words")


@route('/index.html')
@route('/')
def server_static(filename='index.html'):
    return static_file(filename, root='./')

if __name__ == '__main__':
       
        
    run(host='localhost', port=8000)

