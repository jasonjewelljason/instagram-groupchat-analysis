from html_parser import load_df
import pandas as pd
from duckdb import sql
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.corpus import cmudict
from nltk.tokenize import WhitespaceTokenizer
import string
from spellchecker import SpellChecker
from itertools import product as itertools_product
from tqdm import tqdm


def remove_empty_messages(df):
    return apply_sql("select * from df where meta is not null")

def apply_sql(query: str) -> pd.DataFrame:
    return sql(query).df()

def count_words(t):
    if isinstance(t, str):
        return len(t.split())
    else:
        return 0

def generate_author_stats(groupchat, columns: list) -> pd.DataFrame:

    m = groupchat.messages
    l = groupchat.likes
    authors = groupchat.authors

    # Initializing the dataframe with unique authors
    author_stats = pd.DataFrame(authors, columns=['author'])
    cols = {}

    # Total Sends: Counting the number of sends (rows) for each author in m
    if "Total sends" in columns:
        cols['total_sends'] = m['author'].value_counts()

    # Aggregating total message types by counting on the 'meta' column of m
    for meta in ['message', 'link', 'image', 'post', 'video', 'audio']:
        if f'Total {meta}s' in columns:
            cols[f'total_{meta}s'] = m[m['meta'] == meta]['author'].value_counts().fillna(0).astype(int)

    # Likes Given: Counting the number of likes given by each author in l
    if 'Likes given' in columns:
        cols['likes_given'] = l['liker'].value_counts().fillna(0).astype(int)

    # Likes Received: Calculating the number of likes received for each author's posts
    # Mapping post_ids in m to their corresponding likes in l
    if 'Likes received' in columns:
        post_likes = l['post_id'].value_counts()
        m['likes_received'] = m['post_id'].map(post_likes).fillna(0)
        cols['likes_received'] = m.groupby('author')['likes_received'].sum().astype(int)

    # Word count
    if 'Word count' in columns:
        m['word_count'] = m['content'].apply(count_words)
        cols['total_words'] = m.groupby('author')['word_count'].sum().astype(int)

    # Average sentiment
    if 'Average sentiment' in columns:
        perform_sentiment_analysis(groupchat)
        cols['average_sentiment'] = m.groupby('author')['sentiment_score'].mean()

    # Run data
    if 'Total runs' in columns or 'Longest run' in columns or 'Average run length' in columns:
        runs_data = make_runs_data(groupchat)
        if 'Total runs' in columns:
            cols['total_runs'] = {author: data['total_runs'] for author, data in runs_data.items()}
        if 'Longest run' in columns:
            cols['longest_run'] = {author: data['longest_run'] for author, data in runs_data.items()}
        if 'Average run length' in columns:
            cols['average_run_length'] = {author: data['average_run_length'] for author, data in runs_data.items()}

    # Merging all these counts into the author_stats dataframe
    author_stats = author_stats.set_index('author')
    for k, v in cols.items():
        if k in ['total_sends', 'likes_given', 'likes_received', 'total_words', 'total_messages', 'total_links', 'total_images', 'total_posts', 'total_videos', 'total_audios', 'total_runs', 'longest_run']:
            author_stats[k] = author_stats.index.map(v).fillna(0).astype(int)
        else:
            author_stats[k] = author_stats.index.map(v).fillna(0)

    # Filling NaN values with 0 as they indicate no activity in that category
    author_stats.fillna(0, inplace=True)

    return author_stats


# Activity over time
def activity_over_time(groupchat, period='M'):
    m = groupchat.messages
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


def perform_sentiment_analysis(groupchat) -> None:
    # Adds sentiment score column to m.
    m = groupchat.messages
    if 'sentiment_score' in m: return

    nltk.download('vader_lexicon')
    sia = SentimentIntensityAnalyzer()
    def get_sentiment_score(message):
        if pd.isna(message):
            return None
        return sia.polarity_scores(message)['compound']
    tqdm.pandas(desc="Analyzing sentiment")
    m['sentiment_score'] = m['content'].progress_apply(get_sentiment_score)


def my_tokenize(message, tokenizer, spellchecker=None) -> list:
    tokens = tokenizer.tokenize(message)
    tokens = [t.strip(string.punctuation).lower() for t in tokens if t.strip(string.punctuation)]
    if spellchecker:
        words_to_check = [t for t in tokens if len(t) > 2 and len(t) < 15 and t.isalpha()]
        misspelled = set(spellchecker.unknown(words_to_check))
        corrected_tokens = [spellchecker.correction(token) if token in misspelled else token for token in tokens]
        return corrected_tokens
    else:
        return tokens


def perform_iambic_pentameter(groupchat, check_spelling=False) -> None:
    """
    Adds an "is_iambic_pentameter" column to m. Setting check_spelling to True corrects misspellings, but is extremely slow and not recommended.
    """
    m = groupchat.messages
    def is_iambic_pentameter(message, cmu, tokenizer, spellchecker=None) -> bool:
        """
        Returns if a message follows iambic pentameter.

        Parameters:
            message (str)
            cmu (dict): cmudict containing pronunciation information
            tokenizer (WhitespaceTokenizer): Tokenizer object
            spellchecker (SpellChecker or None): Optional spellchecker for input message
        """
        if not isinstance(message, str):
            return False

        def cmu_to_stress(word):
            # Turns cmu data for a word into a list of possible stress patterns
            out = set()
            is_one_syllable = None
            for pronunciation in word:
                stress = ''
                for phoneme in pronunciation:
                    if '0' in phoneme or '1' in phoneme:
                        stress += phoneme[-1]
                    elif '2' in phoneme:
                        stress += '1'
                out.add(stress)
                if len(pronunciation) == 1:
                    is_one_syllable = True
            if is_one_syllable:
                out.add('1')
                out.add('0')
            return list(out)
        
        def combine_lists(lists):
            # Combines words into all possible combinations of each word's stress patterns
            combined = [''.join(items) for items in itertools_product(*lists)]
            return combined
        
        def possible_stress_patterns(stresses):
            return set(combine_lists(stresses))

        text = my_tokenize(message, tokenizer, spellchecker)
        if len(text) > 10:
            return False
        try:
            text_pronunciation = [cmu[x] for x in text]
        except:
            return False
        stresses = [cmu_to_stress(x) for x in text_pronunciation]
        possible_patterns = possible_stress_patterns(stresses)
        if '0101010101' in possible_patterns:
            return True
        else: 
            return False

    nltk.download('cmudict') 
    nltk.download('punkt')
    cmu = cmudict.dict()
    spellchecker = SpellChecker() if check_spelling else None
    tokenizer = WhitespaceTokenizer()
    tqdm.pandas(desc='Checking for iambic pentameter')
    m['is_iambic_pentameter'] = m['content'].progress_apply(lambda message: is_iambic_pentameter(message, cmu, tokenizer, spellchecker))


def count_words_by_author(groupchat, words) -> pd.DataFrame:
    # Given a messages df and list of words, returns a df with counts of how many times each author sent that word
    m = groupchat.messages
    m['content'] = m['content'].fillna('')
    m['message_lower'] = m['content'].str.lower()

    # Initialize the DataFrame with zeros
    unique_authors = m['author'].unique()
    word_counts_df = pd.DataFrame(index=unique_authors, columns=words).fillna(0)

    # Using vectorized operations for counting
    for word in words:
        word_lower = word.lower()
        # Create a temporary DataFrame with counts of each word for each author
        temp_df = m[m['message_lower'].str.contains(word_lower)].groupby('author')['message_lower'].apply(
            lambda x: x.str.count(word_lower).sum()).reset_index(name='count')

        # Update the counts in the main DataFrame
        for row in temp_df.itertuples(index=False):
            word_counts_df.at[row.author, word] = row.count

    return word_counts_df

def make_repliers_dict(groupchat) -> dict:
    # Given a messages df, returns a dictionary with each author as a key and a dictionary of repliers as the value
    m = groupchat.messages
    messages = m[m['meta'] == 'message']

    authors = groupchat.authors
    repliers_dict = {author: {a: 0 for a in authors} for author in authors}

    for i in range(1, len(messages)):
        current_message = messages.iloc[i]
        previous_message = messages.iloc[i - 1]

        if current_message['author'] != previous_message['author']:
            repliers_dict[previous_message['author']][current_message['author']] += 1

    return repliers_dict

def make_runs_data(groupchat) -> dict:
    # Given a messages df, returns a dictionary with each author as a key and a dictionary of runs data as the value
    m = groupchat.messages
    runs_data = {}
    previous_author = None
    current_run_length = 0

    for index, row in m.iterrows():
        author = row['author']
        if author == previous_author:
            current_run_length += 1
        else:
            if previous_author is not None:
                if previous_author not in runs_data:
                    runs_data[previous_author] = {'total_runs': 0, 'total_messages_in_runs': 0, 'longest_run': 0}
                
                runs_data[previous_author]['total_runs'] += 1
                runs_data[previous_author]['total_messages_in_runs'] += current_run_length
                runs_data[previous_author]['longest_run'] = max(runs_data[previous_author]['longest_run'], current_run_length)

            previous_author = author
            current_run_length = 1

    # Adding the last author's run data
    if previous_author is not None:
        if previous_author not in runs_data:
            runs_data[previous_author] = {'total_runs': 0, 'total_messages_in_runs': 0, 'longest_run': 0}

        runs_data[previous_author]['total_runs'] += 1
        runs_data[previous_author]['total_messages_in_runs'] += current_run_length
        runs_data[previous_author]['longest_run'] = max(runs_data[previous_author]['longest_run'], current_run_length)

    for author in runs_data:
        runs_data[author]['average_run_length'] = runs_data[author]['total_messages_in_runs'] / runs_data[author]['total_runs']

    return runs_data

def activity_heatmap(groupchat):
    # Given a groupchat, plots a heatmap of activity by day of week and hour of day
    m = groupchat.messages

    # Convert 'timestamp' to datetime
    m['timestamp'] = pd.to_datetime(m['timestamp'])

    # Extract day of week and hour from 'timestamp'
    m['day_of_week'] = m['timestamp'].dt.dayofweek
    m['hour_of_day'] = m['timestamp'].dt.hour

    # Prepare data for heatmap
    # Group the data by day of week and hour of day and count the messages
    heatmap_data = m.groupby(['day_of_week', 'hour_of_day']).size().unstack(fill_value=0)

    # Create the heatmap
    plt.figure(figsize=(15, 8))
    sns.heatmap(heatmap_data, cmap='YlGnBu', annot=False)
    plt.title('Activity Heatmap of Group Chat')
    plt.xlabel('Hour of Day')
    plt.ylabel('Day of Week (0: Monday - 6: Sunday)')
    plt.show()


if __name__ == '__main__':
    pass

groupchat = load_df('datatest')
