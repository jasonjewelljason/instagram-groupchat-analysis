from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
from datetime import datetime
import re
import glob
import PySimpleGUI as sg
import unicodedata
import emoji

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

def parse_html_folder(path: str = 'data') -> (pd.DataFrame, pd.DataFrame):
    paths = glob.glob(f"{path}/*.html")
    paths = sorted(paths, key = lambda x : int(re.split('\_|\.', x)[-2]))
    # paths = paths[3:4] # Remove this later
    dfs = [parse_html_file(path) for path in tqdm(paths, desc='Parsing HTML files')]
    all_messages_df = pd.concat(dfs)
    all_messages_df = all_messages_df.iloc[::-1] # Reverses the df
    return separate_dfs(all_messages_df)


def clean_string(s):
    # Normalize Unicode data
    s = unicodedata.normalize('NFKD', s)
    # Remove non-printable characters and any leading special characters (e.g., emojis)
    s = ''.join(ch for ch in s if unicodedata.category(ch)[0] not in ['C', 'So'])
    # Strip leading and trailing whitespace
    s = s.strip()
    return s

def rename_author(messages_df, like_events_df, old_name, new_name):
    # Use the updated clean_string function to clean names
    old_name_clean = clean_string(old_name)
    new_name_clean = clean_string(new_name)

    # Update the author names in messages
    messages_df['author'] = messages_df['author'].apply(
        lambda x: new_name_clean if clean_string(x) == old_name_clean else x
    )

    # Update the liker names in like events
    like_events_df['liker'] = like_events_df['liker'].apply(
        lambda x: new_name_clean if clean_string(x) == old_name_clean else x
    )

    return messages_df, like_events_df


def validate(messages_df, like_events_df):
    # Choose a theme for the GUI
    sg.theme('SystemDefault1')

    # Define the layout with better spacing and alignment
    layout = [
        [sg.Text('Author Manager', font=("Helvetica", 16), justification='center', pad=((0,0), (20,10)))],
        [sg.Listbox(values=list(like_events_df['liker'].unique()), size=(30, 10), key='-AUTHOR-LIST-', enable_events=True)],
        [sg.Text('Rename selected author to:', pad=((0,0), (20,3))), sg.InputText(key='-NEW-AUTHOR-NAME-', do_not_clear=False)],
        [sg.Button('Rename Author', bind_return_key=True, pad=((0,0), (10,20)))],
        [sg.Button('Exit', pad=((0,0), (0,20)))]
    ]

    # Create the window with a nicer layout
    window = sg.Window('Author Manager', layout, element_justification='c', finalize=True)

    # Event loop
    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, 'Exit'):
            break

        if event == '-AUTHOR-LIST-':
            if values['-AUTHOR-LIST-']:
                selected_author = values['-AUTHOR-LIST-'][0]
                window['-NEW-AUTHOR-NAME-'].update(selected_author)

        elif event == 'Rename Author':
            selected_author = values['-AUTHOR-LIST-'][0] if values['-AUTHOR-LIST-'] else None
            new_author_name = values['-NEW-AUTHOR-NAME-'].strip()
            if selected_author and new_author_name and new_author_name != selected_author:
                messages_df, like_events_df = rename_author(messages_df, like_events_df, selected_author, new_author_name)
                window['-AUTHOR-LIST-'].update(list(messages_df['author'].unique()))
                sg.popup(f'Author "{selected_author}" has been renamed to "{new_author_name}"', title='Rename Successful')

    window.close()


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


def make_csvs(messages_df, likes_df, data_path: str = 'data'):
    validate(messages_df, likes_df)
    messages_df.to_csv(f"{data_path}/messages.csv")
    likes_df.to_csv(f"{data_path}/likes.csv")
    print("CSV files written!")

def load_df(path: str = 'data', dfs: list = ['messages', 'likes']):
    out = tuple(pd.read_csv(f"{path}/{df}.csv", index_col=0) for df in dfs)
    return out

if __name__ == '__main__':
    m,l = parse_html_folder()
    make_csvs(m, l)
    # m, l = load_df()
    # print(l.head())