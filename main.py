import json
import os
import re
import sys
import pandas as pd
import random

from openai import Conversation, dalle, exec, GPT3, GPT4, remove_triple_backticks
from render import get_comments_file, get_article_file, write_article_html, write_comments, render_html, read_json, write_json
from generate import generate_headline_desc, generate_comments_and_article


model_for_headlines = GPT4 if 'gpt4' in sys.argv else GPT3
model = GPT3 if 'gpt3' in sys.argv else GPT4

headline = None

if '--stop-at-title' not in sys.argv:
    if os.path.exists('headline.json'):
        headline = read_json('headline.json')

headlines = read_json('headlines.json')

if '--redo-last' in sys.argv:
    headline = headlines[-1]

existing_titles = '\n'.join('- ' + x['headline'] for x in reversed(headlines[-30:]))

if not headline:
    print('Generating headlines...')

    chat = Conversation(model_for_headlines)
    num_headlines_to_sample = 30
    chat.say(f'Give {num_headlines_to_sample} absurd headlines parodying typical Hackernews titles in a stupidly laughable and funny way.')

    if '--just-titles' in sys.argv:
        exit(0)

    print('Picking the best headline...')
    title = chat.say(f'''
    Give me the most absurd, the most unbelievable headline of the ones you generated (just give the title, do not add any other text).

    The picked headline must NOT be similar to one of those:
    {existing_titles}
    ''', model=model)

    headline = generate_headline_desc(title)
    write_json('headline.json', headline)

print(json.dumps(headline, indent=4))

title = headline['headline']

if '--stop-at-title' in sys.argv:
    exit(0)

generate_comments_and_article(headline, model)
render_html(headlines)

if not len([h for h in headlines if h['headline'] == headline['headline']]):
    headlines.append(headline)
write_json('headlines.json', headlines)

if os.path.exists('headline.json'):
    os.unlink('headline.json')


if '--push' in sys.argv:
    exec('git', 'add', 'articles', 'comments')
    exec('git', 'commit', '-am', 'upd')
    exec('git', 'pull')
    exec('git', 'push')
