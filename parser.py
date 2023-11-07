from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
from datetime import datetime

with open(r'C:\Users\jljew\Jason OneDrive\OneDrive\Documents\Personal\Island AI\New data\message_1.html', encoding='utf8') as f:
    data = f.read()

soup = BeautifulSoup(data, 'lxml')
messages = []

html_classes = {'author': '_3-95 _2pim _a6-h _a6-i',
                'timestamp': '_3-94 _a6-o',
                'content': '_3-95 _a6-p',
                'message': "pam _3-95 _2ph- _a6-g uiBoxWhite noborder",
                'likers': '_a6-q'}

class Message:
    def __init__(self, message_div) -> None:
        self.author_div = message_div.find('div', class_=html_classes['author'])
        self.author = self.author_div.get_text() if self.author_div else None
        self.timestamp_div = message_div.find('div', class_=html_classes['timestamp'])
        self.timestamp = self.timestamp_div.get_text() if self.timestamp_div else None
        self.likers_list = message_div.find('ul', class_=html_classes['likers'])
        self.likers = [li.get_text(strip=True)[1:] for li in self.likers_list.find_all('li')] if self.likers_list else []
        self.content_div = message_div.find('div', class_=html_classes['content'])

        self.meta = None
        if self.content_div and self.content_div.find('img'):
            self.meta = 'image'
        elif self.content_div and self.content_div.find('audio'):
            self.meta = 'audio'

        self.image = self.content_div.find('img') if self.content_div else None
        self.audio = self.content_div.find('audio') if self.content_div else None
        self.content = [x for x in self.content_div.find_all(string=True,recursive=True) if x.parent.name != 'li'] if self.content_div else None
        self.a = message_div.find_all('a')
        # self.content = self.content[0] if self.content else None
        



message_divs = soup.find_all('div', class_="pam _3-95 _2ph- _a6-g uiBoxWhite noborder")

messages = [Message(m) for m in tqdm(message_divs)]
print([m.content for m in messages if m.content and len(m.content)>1 and m.a])
# TODO: deal with shared posts and links 

def get_content(content_div):
    pass

# for message_div in message_divs:
#     # Extract the author
#     author_div = message_div.find('div', class_='_3-95 _2pim _a6-h _a6-i')
#     author = author_div.get_text(strip=True) if author_div else None

#     # Extract the timestamp
#     timestamp_div = message_div.find('div', class_='_3-94 _a6-o')
#     timestamp = timestamp_div.get_text(strip=True) if timestamp_div else None
#     if timestamp: timestamp = datetime.strptime(timestamp, "%b %d, %Y, %I:%M %p")

#     # Extract the message content
#     content_div = message_div.find('div', class_='_3-95 _a6-p')
#     content = ''
#     if content_div:
#         print(content_div)
#         # Get all text parts, but exclude the ul element containing likers
#         text_parts = content_div.find_all(string=True, recursive=True)
#         for part in text_parts:
#             if part.parent.name != 'li':  # Ensure this text is not part of a liker's name
#                 content_part = part.strip()
#                 if content_part:
#                     content += content_part + ' '
#         content = content.strip()  # Trim any excess whitespace

#     # Extract the likers
#     likers_list = message_div.find('ul', class_='_a6-q')
#     likers = [li.get_text(strip=True)[1:] for li in likers_list.find_all('li')] if likers_list else []

#     # Append the data to the messages list
#     messages.append({
#         'author': author,
#         'timestamp': timestamp,
#         'content': content,
#         'likers': likers
#     })

# df = pd.DataFrame.from_dict(messages)
# print(df.head(10))


