from html_parser import load_df
import pandas as pd
from duckdb import sql

m,l = load_df()

def remove_empty_messages(df):
    return apply_sql("select * from df where meta is not null")

def apply_sql(query: str) -> pd.DataFrame:
    return sql(query).df()

def generate_author_stats(m,l) -> pd.DataFrame:

    author_df = pd.DataFrame(m['author'].unique(), columns=['author'])

    for type in ['message', 'image', 'post', 'audio', 'link']:
        temp_df = m[m['meta'] == type].groupby('author').size().reset_index(name=f'total_{type}s')
        author_df = pd.merge(author_df, temp_df, on='author', how='left')
        author_df[f'total_{type}s'] = author_df[f'total_{type}s'].fillna(0).astype(int)

    return author_df
