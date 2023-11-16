from html_parser import load_df
import pandas as pd
from duckdb import sql

m,l = load_df()

def remove_empty_messages(df):
    return apply_sql("select * from df where meta is not null")

def apply_sql(query: str) -> pd.DataFrame:
    return sql(query).df()

def generate_author_stats(m,l) -> pd.DataFrame:

    # Initializing the dataframe with unique authors
    author_stats = pd.DataFrame(m['author'].unique(), columns=['author'])
    cols = {}

    # Total Sends: Counting the number of sends (rows) for each author in m
    cols['total_sends'] = m['author'].value_counts()

    # Total Messages, Links, Images: Counting based on the 'meta' column
    for meta in ['message', 'link', 'image', 'post', 'video', 'audio']:
        cols[f'total_{meta}s'] = m[m['meta'] == meta]['author'].value_counts()

    # Likes Given: Counting the number of likes given by each author in l
    cols['likes_given'] = l['liker'].value_counts()

    # Likes Received: Calculating the number of likes received for each author's posts
    # Mapping post_ids in m to their corresponding likes in l
    post_likes = l['post_id'].value_counts()
    m['likes_received'] = m['post_id'].map(post_likes).fillna(0)
    cols['likes_received'] = m.groupby('author')['likes_received'].sum()

    # Merging all these counts into the author_stats dataframe
    author_stats = author_stats.set_index('author')
    for k,v in cols.items():
        author_stats[k] = author_stats.index.map(v)

    # Filling NaN values with 0 as they indicate no activity in that category
    author_stats.fillna(0, inplace=True)

    # Converting counts to integers
    author_stats = author_stats.astype(int)

    return author_stats

if __name__ == '__main__':
    a = generate_author_stats(m,l)