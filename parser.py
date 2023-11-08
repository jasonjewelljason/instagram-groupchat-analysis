from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
from datetime import datetime
import re
import glob

HTML_CLASSES = {'author': '_3-95 _2pim _a6-h _a6-i',
                'timestamp': '_3-94 _a6-o',
                'content': '_3-95 _a6-p',
                'message': "pam _3-95 _2ph- _a6-g uiBoxWhite noborder",
                'likers': '_a6-q'}
DEPRECATED_LIKE_PATTERN = re.compile('^\S+ liked a message')

class Message:
    def __init__(self, message_div) -> None:
        self.author_div = message_div.find('div', class_=HTML_CLASSES['author'])
        self.author = self.author_div.get_text() if self.author_div else None
        self.timestamp_div = message_div.find('div', class_=HTML_CLASSES['timestamp'])
        self.timestamp = self.timestamp_div.get_text() if self.timestamp_div else None
        self.timestamp = pd.to_datetime(self.timestamp)
        self.likers_list = message_div.find('ul', class_=HTML_CLASSES['likers'])
        self.likers = [li.get_text(strip=True)[1:] for li in self.likers_list.find_all('li')] if self.likers_list else []
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

def parse_html_file(path: str) -> pd.DataFrame:

    with open(path, encoding='utf8') as f:
        data = f.read()
    soup = BeautifulSoup(data, 'lxml')

    message_divs = soup.find_all('div', class_=HTML_CLASSES['message'])
    messages = [Message(m) for m in tqdm(message_divs, desc='Parsing messages', leave=False)]
    message_dicts = []
    for m in messages:
        d = {'meta': m.meta,
        'author': m.author,
        'timestamp': m.timestamp,
        'content': m.content,
        'likers': m.likers}
        message_dicts.append(d)
    df = pd.DataFrame.from_dict([m for m in message_dicts if not str(m['timestamp']) == 'NaT'])
    return df

def parse_html_folder(path: str = 'data') -> pd.DataFrame:
    paths = glob.glob(f"{path}/*.html")
    paths = sorted(paths, key = lambda x : int(re.split('\_|\.', x)[-2]))
    dfs = [parse_html_file(path) for path in tqdm(paths, desc='Parsing HTML files')]
    return dfs

def make_csv(data_path: str = 'data'):
    csv_path = f"{data_path}/messages.csv"
    dfs = parse_html_folder(data_path)
    all_messages_df = pd.concat(dfs)
    all_messages_df = all_messages_df.iloc[::-1] # Reverses the df
    all_messages_df.to_csv(csv_path)

if __name__ == '__main__':
    make_csv()