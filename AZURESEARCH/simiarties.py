from sentence_transformers import SentenceTransformer

import pandas as pd

import numpy as np

df = pd.read_csv("C:/Users/ravichandrav/Downloads/food-price-index-september-2023-index-numbers.csv")

print(df)

model = SentenceTransformer("paraphrase-MiniLM-L6-v2")

input_text = "the fox crossed the road"

text_embedd = model.encode(input_text)

print(text_embedd)

def get_embedding(x):

 x_embedd = model.encode(x)

   
 return x_embedd

  

def cosine_similarity(vec_a, vec_b):

   
# Normalize the vectors

    vec_a = vec_a / np.linalg.norm(vec_a)

    vec_b = vec_b / np.linalg.norm(vec_b)

   
# Calculate the cosine similarity

    similarity  = np.dot(vec_a,vec_b)

   
    return similarity

  

df["embedding"] = df["text"].apply(
lambda
 x: get_embedding(x))

df.to_csv("C:/Users/nigelc/Downloads/word_embeddings.csv")

print(df)


search_term = input("Enter a search term: ")

search_term_vector = get_embedding(search_term)

df["similarities"]=df["embedding"].apply(
lambda
 x: cosine_similarity(x, search_term_vector))

df.sort_values("similarities", ascending=False).head(20)