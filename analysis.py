from html_parser import load_df
import pandas as pd
from duckdb import sql
import matplotlib.pyplot as plt
import numpy as np
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

m,l = load_df()

def remove_empty_messages(df):
    return apply_sql("select * from df where meta is not null")

def apply_sql(query: str) -> pd.DataFrame:
    return sql(query).df()

def count_words(t):
    if isinstance(t, str):
        return len(t.split())
    else:
        return 0

def generate_author_stats(m,l) -> pd.DataFrame:

    # Initializing the dataframe with unique authors
    author_stats = pd.DataFrame(m['author'].unique(), columns=['author'])
    cols = {}

    # Total Sends: Counting the number of sends (rows) for each author in m
    cols['total_sends'] = m['author'].value_counts()

    # Aggregating total message types by counting on the 'meta' column of m
    for meta in ['message', 'link', 'image', 'post', 'video', 'audio']:
        cols[f'total_{meta}s'] = m[m['meta'] == meta]['author'].value_counts()

    # Likes Given: Counting the number of likes given by each author in l
    cols['likes_given'] = l['liker'].value_counts()

    # Likes Received: Calculating the number of likes received for each author's posts
    # Mapping post_ids in m to their corresponding likes in l
    post_likes = l['post_id'].value_counts()
    m['likes_received'] = m['post_id'].map(post_likes).fillna(0)
    cols['likes_received'] = m.groupby('author')['likes_received'].sum()

    # Word count
    m['word_count'] = m['content'].apply(count_words)
    cols['total_words'] = m.groupby('author')['word_count'].sum()

    # Average sentiment
    cols['average_sentiment'] = m.groupby('author')['sentiment_score'].mean()

    # Merging all these counts into the author_stats dataframe
    author_stats = author_stats.set_index('author')
    for k,v in cols.items():
        author_stats[k] = author_stats.index.map(v)

    # Filling NaN values with 0 as they indicate no activity in that category
    author_stats.fillna(0, inplace=True)

    # Converting counts to integers
    author_stats = author_stats.astype(int)

    return author_stats

def activity_over_time(m, period='M'):
    m['timestamp'] = pd.to_datetime(m['timestamp'])
    activity = m.set_index('timestamp').groupby([pd.Grouper(freq=period), 'author']).count()['content']
    return activity.unstack().fillna(0).astype(int)

def detect_time_period(index):
    """
    Detects the time period (daily, monthly, etc.) of the provided datetime index.
    """
    if len(index) < 2:
        return None

    delta = index[1] - index[0]
    if delta.days >= 28 and delta.days <= 31:
        return 'M'  # Monthly
    elif delta.days >= 7 and delta.days <= 7:
        return 'W'  # Weekly
    elif delta.days == 1:
        return 'D'  # Daily
    else:
        return None  # Undefined or irregular period

def format_x_labels_universal(index, period):
    """
    Formats the x-axis labels for all periods (daily, weekly, monthly, yearly).
    """
    if period == 'M':
        labels = [label.strftime('%b %Y') for label in index]
    elif period == 'W':
        labels = [label.strftime('%b %d, %Y') for label in index]
    elif period == 'D':
        labels = [label.strftime('%b %d, %Y') for label in index]
    elif period == 'Y':
        labels = [label.strftime('%Y') for label in index]
    else:
        # Default to monthly if period is undefined
        labels = [label.strftime('%b %Y') for label in index]

    return labels

def plot_activity_over_time(activity_data, authors=None, label_frequency=4):
    if authors == 'all':
        data_to_plot = activity_data.sum(axis=1)
    elif authors is not None:
        data_to_plot = activity_data[authors]
    else:
        data_to_plot = activity_data

    period = detect_time_period(data_to_plot.index)
    labels = format_x_labels_universal(index=data_to_plot.index, period=period)

    # Reducing the frequency of labels to avoid crowding
    for i in range(len(labels)):
        if i % label_frequency != 0 and period != 'Y':
            labels[i] = ''

    data_to_plot.plot(kind='bar', figsize=(15, 7))
    plt.title('Activity Over Time')
    plt.xlabel('Time Period')
    plt.ylabel('Number of Messages')

    # Set the custom labels with reduced frequency
    plt.xticks(ticks=range(len(labels)), labels=labels, rotation=45)

    if authors != 'all':
        plt.legend(title='Authors')

    plt.tight_layout()
    plt.show()

def sentiment_analysis(m):
    # Adds sentiment score column to m
    nltk.download('vader_lexicon')
    sia = SentimentIntensityAnalyzer()
    def get_sentiment_score(message):
        if pd.isna(message):
            return None
        return sia.polarity_scores(message)['compound']
    m['sentiment_score'] = m['content'].apply(get_sentiment_score)


if __name__ == '__main__':
    # activity_data = activity_over_time(m, 'Y')
    # plot_activity_over_time(activity_data, authors=['Jason Jewell', 'Matthew Eshaya'])
    pass