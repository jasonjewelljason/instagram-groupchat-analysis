from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
from datetime import datetime

with open(r'C:\Users\jljew\Jason OneDrive\OneDrive\Documents\Personal\Island AI\New data\message_1.html', encoding='utf8') as f:
    data = f.read()

soup = BeautifulSoup(data, 'lxml')
messages = []

message_divs = soup.find_all('div', class_="pam _3-95 _2ph- _a6-g uiBoxWhite noborder")

for message_div in message_divs:
    # Extract the author
    author_div = message_div.find('div', class_='_3-95 _2pim _a6-h _a6-i')
    author = author_div.get_text(strip=True) if author_div else None

    # Extract the timestamp
    timestamp_div = message_div.find('div', class_='_3-94 _a6-o')
    timestamp = timestamp_div.get_text(strip=True) if timestamp_div else None
    if timestamp: timestamp = datetime.strptime(timestamp, "%b %d, %Y, %I:%M %p")

    # Extract the message content
    content_div = message_div.find('div', class_='_3-95 _a6-p')
    content = ''
    if content_div:
        # Get all text parts, but exclude the ul element containing likers
        text_parts = content_div.find_all(string=True, recursive=True)
        for part in text_parts:
            if part.parent.name != 'li':  # Ensure this text is not part of a liker's name
                content_part = part.strip()
                if content_part:
                    content += content_part + ' '
        content = content.strip()  # Trim any excess whitespace

    # Extract the likers
    likers_list = message_div.find('ul', class_='_a6-q')
    likers = [li.get_text(strip=True)[1:] for li in likers_list.find_all('li')] if likers_list else []

    # Append the data to the messages list
    messages.append({
        'author': author,
        'timestamp': timestamp,
        'content': content,
        'likers': likers
    })

df = pd.DataFrame.from_dict(messages)
print(df.head(10))
