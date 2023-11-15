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

    # Total Sends: Counting the number of sends (rows) for each author in m
    total_sends = m['author'].value_counts()

    # Total Messages, Links, Images: Counting based on the 'meta' column
    total_messages = m[m['meta'] == 'message']['author'].value_counts()
    total_links = m[m['meta'] == 'link']['author'].value_counts()
    total_images = m[m['meta'] == 'image']['author'].value_counts()
    total_posts = m[m['meta'] == 'post']['author'].value_counts()
    total_videos = m[m['meta'] == 'video']['author'].value_counts()
    total_audios = m[m['meta'] == 'audio']['author'].value_counts()

    # Likes Given: Counting the number of likes given by each author in l
    likes_given = l['liker'].value_counts()

    # Likes Received: Calculating the number of likes received for each author's posts
    # Mapping post_ids in m to their corresponding likes in l
    post_likes = l['post_id'].value_counts()
    m['likes_received'] = m['post_id'].map(post_likes).fillna(0)
    likes_received = m.groupby('author')['likes_received'].sum()

    # Merging all these counts into the author_stats dataframe
    author_stats = author_stats.set_index('author')
    author_stats['total_sends'] = author_stats.index.map(total_sends)
    author_stats['total_messages'] = author_stats.index.map(total_messages)
    author_stats['total_links'] = author_stats.index.map(total_links)
    author_stats['total_images'] = author_stats.index.map(total_images)
    author_stats['total_posts'] = author_stats.index.map(total_posts)
    author_stats['total_videos'] = author_stats.index.map(total_videos)
    author_stats['total_audios'] = author_stats.index.map(total_audios)
    author_stats['likes_given'] = author_stats.index.map(likes_given)
    author_stats['likes_received'] = author_stats.index.map(likes_received)

    # Filling NaN values with 0 as they indicate no activity in that category
    author_stats.fillna(0, inplace=True)

    # Converting counts to integers
    author_stats = author_stats.astype(int)

    return author_stats

if __name__ == '__main__':
    pass