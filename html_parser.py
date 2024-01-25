from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
from datetime import datetime
import re
import glob
import unicodedata
import emoji
import tkinter as tk
from tkinter import messagebox, ttk
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

def parse_html_folder(path: str = 'data') -> (pd.DataFrame, pd.DataFrame, str):
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
    return messages_df, likes_df, most_common_title


def clean_string(s):
    # Normalize Unicode data
    s = unicodedata.normalize('NFKD', s)
    # Remove non-printable characters and any leading special characters (e.g., emojis)
    s = ''.join(ch for ch in s if unicodedata.category(ch)[0] not in ['C', 'So'])
    # Strip leading and trailing whitespace
    s = s.strip()
    return s



from PySide6.QtWidgets import QApplication, QMainWindow, QListWidget, QPushButton, QVBoxLayout, QWidget, QLineEdit, QLabel, QMessageBox
from PySide6.QtCore import Qt
import sys

class MainWindow(QMainWindow):
    def __init__(self, messages_df, like_events_df):
        super(MainWindow, self).__init__()

        self.messages_df = messages_df
        self.like_events_df = like_events_df

        self.setWindowTitle('Author Manager')

        self.listbox = QListWidget()
        self.listbox.addItems(self.like_events_df['liker'].unique())
        self.listbox.itemSelectionChanged.connect(self.on_listbox_select)

        self.label = QLabel('Rename selected author to:')
        self.entry = QLineEdit()

        self.rename_button = QPushButton('Rename Author')
        self.rename_button.clicked.connect(self.rename_author_inner)

        self.finished_button = QPushButton('Finished')
        self.finished_button.clicked.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(self.listbox)
        layout.addWidget(self.label)
        layout.addWidget(self.entry)
        layout.addWidget(self.rename_button)
        layout.addWidget(self.finished_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def rename_author_inner(self):
        selected_author = self.listbox.currentItem().text()
        new_author_name = self.entry.text().strip()
        if selected_author and new_author_name and new_author_name != selected_author:
            self.messages_df, self.like_events_df = rename_author(self.messages_df, self.like_events_df, selected_author, new_author_name)
            self.listbox.clear()
            self.listbox.addItems(self.like_events_df['liker'].unique())
            QMessageBox.information(self, 'Rename Successful', f'Author "{selected_author}" has been renamed to "{new_author_name}"')

    def on_listbox_select(self):
        selected_author = self.listbox.currentItem().text()
        self.entry.setText(selected_author)

def validate(messages_df, like_events_df):
    app = QApplication(sys.argv)

    window = MainWindow(messages_df, like_events_df)
    window.show()

    sys.exit(app.exec_())

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


def make_csvs(messages_df, likes_df, title, data_path: str = 'parsed_data'):
    makedirs(data_path, exist_ok=True)
    # validate(messages_df, likes_df)
    messages_df.to_csv(f"{data_path}/messages.csv")
    likes_df.to_csv(f"{data_path}/likes.csv")
    with open(f"{data_path}/title.txt", 'w') as f:
        f.write(title)
    print("CSV files written!")

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

def load_df(path: str = 'data', dfs: list = ['messages', 'likes']):
    m, l = tuple(pd.read_csv(f"{path}/{df}.csv", index_col=0) for df in dfs)
    title = open(f"{path}/title.txt").read()
    return GroupChat(m, l, title)

if __name__ == '__main__':
    m, l, title = parse_html_folder()
    make_csvs(m, l, title, data_path='datatest2')
    # m, l = load_df()
    # print(l.head())