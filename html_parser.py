# I did a lot of work on this code mainly for a personal project, so AI was used a lot and I didn't really keep track of sources on stuff.

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
    # Create the main window
    root = tk.Tk()
    root.title('Author Manager')

    # Modern styling
    style = ttk.Style()
    style.theme_use('clam')  # Using 'clam' for a more modern look

    # Configure the style of widgets for a modern appearance
    style.configure('TButton', font=('Helvetica', 12, 'bold'), borderwidth='4')
    style.configure('TLabel', font=('Helvetica', 12, 'bold'))
    style.configure('TEntry', font=('Helvetica', 12, 'normal'))
    style.configure('TListbox', font=('Helvetica', 12, 'normal'))
    style.configure('TFrame', background='light grey')

    # Create the listbox to display authors
    lb_frame = ttk.Frame(root, padding="10 10 10 10", style='TFrame')
    lb_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    scrollbar = ttk.Scrollbar(lb_frame, orient="vertical")
    listbox = tk.Listbox(lb_frame, exportselection=0, yscrollcommand=scrollbar.set, font=('Helvetica', 12), relief=tk.FLAT)
    scrollbar.config(command=listbox.yview)
    scrollbar.pack(side="right", fill="y")
    listbox.pack(side="left", fill="both", expand=True)

    # Populate the listbox with authors
    for author in like_events_df['liker'].unique():
        listbox.insert(tk.END, author)

    # Create the label and entry for the new author name
    entry_frame = ttk.Frame(root, padding="10 10 10 10", style='TFrame')
    entry_frame.pack(padx=10, pady=10)
    label = ttk.Label(entry_frame, text='Rename selected author to:')
    label.pack(side="left", padx=5)
    entry = ttk.Entry(entry_frame, width=30)
    entry.pack(side="left", padx=5)

    # Function to handle the renaming
    def rename_author_inner():
        selected_author = listbox.get(listbox.curselection())
        new_author_name = entry.get().strip()
        if selected_author and new_author_name and new_author_name != selected_author:
            nonlocal messages_df, like_events_df
            messages_df, like_events_df = rename_author(messages_df, like_events_df, selected_author, new_author_name)
            # Update the listbox
            listbox.delete(0, tk.END)
            for author in like_events_df['liker'].unique():
                listbox.insert(tk.END, author)
            messagebox.showinfo('Rename Successful', f'Author "{selected_author}" has been renamed to "{new_author_name}"')

    # Update the entry with the selected author's name
    def on_listbox_select(event):
        selected_author = listbox.get(listbox.curselection())
        entry.delete(0, tk.END)
        entry.insert(0, selected_author)

    # Bind the listbox selection event
    listbox.bind('<<ListboxSelect>>', on_listbox_select)

    # Create the rename button
    rename_button = ttk.Button(root, text="Rename Author", command=rename_author_inner)
    rename_button.pack(padx=10, pady=5)

    # Create the 'Finished' button to exit the GUI
    def close_gui():
        root.destroy()

    finished_button = ttk.Button(root, text="Finished", command=close_gui)
    finished_button.pack(padx=10, pady=10)

    # Start the event loop
    root.mainloop()

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
    make_csvs(m, l, data_path='datatest')
    # m, l = load_df()
    # print(l.head())