import json
import os
import re
import sys
import requests
import pandas as pd
import random

from openai import Conversation, dalle
from render import get_comments_file, get_article_file, write_article_html, write_comments, render_html, read_json, write_json

GPT3 = 'text-davinci-002-render-sha'
GPT4 = 'gpt-4'

model_for_headlines = GPT4 if 'gpt-4' in sys.argv else GPT3
model = GPT4

headline = None

if not '--stop-at-title' in sys.argv:
    if os.path.exists('headline.json'):
        headline = read_json('headline.json')

def remove_triple_backticks(txt):
    found = re.search(r'```.*\n((.|\n)+)```', txt) or re.search(r'```((.|\n)+)```', txt)
    if found:
        return found.group(1)
    return txt

headlines = read_json('headlines.json')

existing_titles = '\n'.join('- ' + x['headline'] for x in reversed(headlines[-30:]))

headline = headlines[-1]

if not headline:
    print('Generating headlines...')

    chat = Conversation(model_for_headlines)
    num_headlines_to_sample = 30
    print(chat.say(f'Give {num_headlines_to_sample} absurd headlines parodying typical Hackernews titles in a stupidly laughable and funny way.'))

    print('Picking the best headline...')
    output = chat.say(f'''
    Give me the most stupid, most laughable and unexpected headline of the ones you generated. Also please invent plausible looking domain name where the article could be hosted. And the poster's username. And generate a short URL slug. I need output in JSON format, like:
    ```
    {{"headline": "...", "domain": "...", "user": "...", "slug": "..."}}
    ```
    There must be exacly one object, made out of one of the headlines you generated previously.
    The picked headline must NOT be similar to one of those:

    {existing_titles}
    ''', model=model)
    print(output)
    headline = {
        **json.loads(remove_triple_backticks(output)),
        "comments": random.randint(1, 10),
        "points": random.randint(1, 256),
        "posted": str(pd.Timestamp.now() - pd.Timedelta(hours=1))
    }
    write_json('headline.json', headline)

print(json.dumps(headline, indent=4))

title = headline['headline']

if '--stop-at-title' in sys.argv:
    exit(0)

if not os.path.exists(get_comments_file(headline)):
    print('Generating comments...')
    chat = Conversation(model)
    comments = chat.say(f'''Generate a legitimately looking comment thread for Hackernews title "{title}".

    The thread should be in this format, and:

    1. Instead of <usernameN> generate realistic usernames could be seen on Hackernews (use various styles — snake_case, CamelCase, all-lowercase, all-uppercase, weird mixes and abbreviations, etc.)
    2. Instead of <reply> generate what would they really have replied.
    3. Indentation denotes the comment depth.

    Other rules:

    1. Commenters must NOT be aware of that is a parody website, they must converse like they're on the real Hackernews.
    2. Commenters must try to be funny, must entertain the audience.

    ```
    <username1>: <reply>
        <username2>: <reply>
            <username3>: <reply>
    <username4>: <reply>
    ```
    ''')

    print(comments)
    write_comments(headline, remove_triple_backticks(comments))

if not os.path.exists(get_article_file(headline)):
    print('Generating article HTML...')
    chat = Conversation(model)
    output = chat.say(f'''Generate an article with title "{title}" published on {headline['domain']}.
    Produce HTML output with embedded styles. Generate at most one image per article.
    In the `alt` property of the generated <img> tag (if any), put a prompt for generating the corresponding image (without any prefix, just the prompt).''')
    print(output)

    def replace_prompt_with_image(match):
        prompt = match.group(1)
        print('Generating image for ' + prompt)
        url = dalle(prompt)
        return f'src="{url}" style="object-fit: cover; width: 50%; margin: 0 auto; display: block;" alt="{prompt}"'

    output = re.sub(r'src=".+" alt="(.+)"', replace_prompt_with_image, remove_triple_backticks(output), count=1)

    write_article_html(headline, remove_triple_backticks(output))

# headlines.append(headline)
render_html(headlines)
if os.path.exists('headline.json'):
    os.unlink('headline.json')
write_json('headlines.json', headlines)
