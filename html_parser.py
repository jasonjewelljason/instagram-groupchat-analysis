from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
from datetime import datetime
import re
import glob
import emoji
from os import makedirs

HTML_CLASSES = {'author': '_3-95 _2pim _a6-h _a6-i',
                'timestamp': '_3-94 _a6-o',
                'content': '_3-95 _a6-p',
                'message': "pam _3-95 _2ph- _a6-g uiBoxWhite noborder",
                'likers': '_a6-q'}
DEPRECATED_LIKE_PATTERN = re.compile('^\S+ liked a message')

def remove_first_emoji(s):
    # Find all emojis in the string
    all_emojis = emoji.emoji_list(s)
    # If the string starts with an emoji, remove it
    if all_emojis and all_emojis[0]['match_start'] == 0:
        # Remove the first emoji by slicing the string from the end of the emoji
        return s[all_emojis[0]['match_end']:]
    return s

class GroupChat:
    def __init__(self, messages, likes, title) -> None:
        self.messages = messages
        self.likes = likes
        self.title = title
        self.authors = self.messages['author'].unique()
    
    def __str__(self) -> str:
        return f"GroupChat({self.title})"

    def __len__(self) -> int:
        return len(self.messages)

    def rename_author(self, old_name, new_name):
        # Check if the old name exists in the authors list
        if old_name not in self.authors:
            print(old_name, self.authors)
            raise ValueError(f'Author "{old_name}" not found in authors list')

        # Rename the author in the messages df
        self.messages.loc[self.messages['author'] == old_name, 'author'] = new_name

        # Rename the author in the likes df
        self.likes.loc[self.likes['liker'] == old_name, 'liker'] = new_name

        # Update the authors list
        self.authors = self.messages['author'].unique()

class Message:
    def __init__(self, message_div) -> None:
        self.author_div = message_div.find('div', class_=HTML_CLASSES['author'])
        self.author = self.author_div.get_text() if self.author_div else None
        self.timestamp_div = message_div.find('div', class_=HTML_CLASSES['timestamp'])
        self.timestamp = self.timestamp_div.get_text() if self.timestamp_div else None
        self.timestamp = pd.to_datetime(self.timestamp)
        self.likers_list = message_div.find('ul', class_=HTML_CLASSES['likers'])
        self.likers = [remove_first_emoji(li.get_text(strip=True)) for li in self.likers_list.find_all('li')] if self.likers_list else []
        self.content_div = message_div.find('div', class_=HTML_CLASSES['content'])

        self.meta = None
        if self.content_div and self.content_div.find('img'):
            self.meta = 'image'
        elif self.content_div and self.content_div.find('audio'):
            self.meta = 'audio'
        elif self.content_div and self.content_div.find('video'):
            self.meta = 'video'

        self.image = self.content_div.find('img') if self.content_div else None
        self.audio = self.content_div.find('audio') if self.content_div else None
        self.video = self.content_div.find('video') if self.content_div else None

        self.content = [x for x in self.content_div.find_all(string=True,recursive=True) if x.parent.name not in ['li', 'a']] if self.content_div and not self.meta else None
        self.a = message_div.find_all('a')
        self.links = list(set([a.get('href') for a in self.a])) if self.meta not in ['image', 'audio', 'video'] else []
        if any([x.startswith('https://www.instagram.com') for x in self.links]):
            self.meta = 'post'
            self.content = None
        elif self.links:
            self.meta = 'link'
            self.content = None

        if self.content: 
            self.content = '\n'.join(self.content)
            self.meta = 'message'
            if DEPRECATED_LIKE_PATTERN.match(self.content): 
                self.meta = 'deprecated_like'
                self.content = None

def parse_html_file(path: str) -> (pd.DataFrame, str):
    # Parse a single HTML file and return a df of messages and the title of the chat
    with open(path, encoding='utf8') as f:
        data = f.read()
    soup = BeautifulSoup(data, 'lxml')

    message_divs = soup.find_all('div', class_=HTML_CLASSES['message'])
    messages = [Message(m) for m in tqdm(message_divs, desc='Parsing messages', leave=False)]
    title = soup.find('title').get_text()
    message_dicts = []
    for m in messages:
        d = {'meta': m.meta,
        'author': m.author,
        'timestamp': m.timestamp,
        'content': m.content,
        'likers': m.likers}
        message_dicts.append(d)
    df = pd.DataFrame.from_dict([m for m in message_dicts if not str(m['timestamp']) == 'NaT'])
    return df, title

def parse_html_folder(path: str = 'data') -> GroupChat:
    # Parse all HTML files in a folder and return a df of messages, a df of likes, and the title of the chat
    paths = glob.glob(f"{path}/*.html")
    paths = sorted(paths, key = lambda x : int(re.split('\_|\.', x)[-2]))
    paths = paths[:1]
    data = [parse_html_file(path) for path in tqdm(paths, desc='Parsing HTML files')]
    dfs = [d[0] for d in data]
    titles = [d[1] for d in data]
    most_common_title = max(set(titles), key=titles.count)
    all_messages_df = pd.concat(dfs)
    all_messages_df = all_messages_df.iloc[::-1] # Reverses the df
    messages_df, likes_df = separate_dfs(all_messages_df)
    return GroupChat(messages_df, likes_df, most_common_title)


def separate_dfs(df):
    # Takes in a df of all messages, and separates it into two messages and like events dfs

    df = df.reset_index(drop=True)

    messages = df.drop(columns=['likers']).reset_index(drop=True)
    messages['post_id'] = messages.index  # Assign a new post_id based on the index

    like_events_data = []
    for index, row in tqdm(df.iterrows(), desc='Collecting like event data'):
        for liker in row['likers']:
            like_events_data.append({'post_id': index, 'liker': liker})

    like_events = pd.DataFrame(like_events_data)
    
    return messages, like_events


def make_csvs(groupchat, data_path: str = 'parsed_data'):
    # Saves groupchat info to CSV files in the data_path folder
    makedirs(data_path, exist_ok=True)
    messages_df = groupchat.messages
    likes_df = groupchat.likes
    title = groupchat.title
    messages_df.to_csv(f"{data_path}/messages.csv")
    likes_df.to_csv(f"{data_path}/likes.csv")
    with open(f"{data_path}/title.txt", 'w') as f:
        f.write(title)
    print("CSV files written!")

def load_df(path: str = 'data', dfs: list = ['messages', 'likes']) -> GroupChat:
    # Loads a groupchat from CSV files, returns a GroupChat object
    m, l = tuple(pd.read_csv(f"{path}/{df}.csv", index_col=0) for df in dfs)
    title = open(f"{path}/title.txt").read()
    return GroupChat(m, l, title)

if __name__ == '__main__':
    groupchat = parse_html_folder()
    make_csvs(groupchat)