
import json
import os
import re
import sys
import pandas as pd
import random

from openai import Conversation, GPT3, dalle, remove_triple_backticks
from render import get_comments_file, get_article_file, write_article_html, write_comments


def generate_headline_desc(title):
    chat = Conversation(GPT3)
    output = chat.say(f'''I have a headline: "{title}". 
    Please invent plausible looking domain name where the article could be hosted.
    And the poster's username (it is not needed to be related to headline — only if it is a personal blog).
    And generate a short URL slug.
    I need output in JSON format (do not add any prefix/intro/disclaimer to it), like:
    ```
    {{"headline": "...", "domain": "...", "user": "...", "slug": "..."}}
    ```
    ''')
    headline = {
        **json.loads(remove_triple_backticks(output)),
        "comments": random.randint(1, 10),
        "points": random.randint(1, 256),
        "posted": str(pd.Timestamp.now() - pd.Timedelta(hours=1))
    }

    reply = chat.say('''Is this a post in a personal blog (i.e. a first person narrative) or is it a journalist piece in some media outlet?
    Reply strictly either with "personal" or "not personal" (in that exact wording), no other replies accepted.''')

    if reply.strip().lower() == 'personal':
        headline["personal"] = True

    reply = chat.say('''Is this a tutorial post or any other kind of post?
    Reply strictly either with "tutorial" or "not tutorial" (in that exact wording), no other replies accepted.''')

    if reply.strip().lower() == 'tutorial':
        headline["tutorial"] = True

    return headline


def generate_comments_and_article(headline, model):
    title = headline['headline']

    if not os.path.exists(get_comments_file(headline)) or ('--comments' in sys.argv):
        print('Generating comments...')
        chat = Conversation(model)
        comments = chat.say(f'''Generate a legitimately looking comment thread for Hackernews title "{title}".

        The thread should be in this format (do not add any prefix/intro/disclaimer), and:

        1. Instead of <usernameN> generate realistic usernames could be seen on Hackernews (some capitalized, some lowercase — mix styles).
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
        write_comments(headline, remove_triple_backticks(comments))

    if not os.path.exists(get_article_file(headline)) or ('--article' in sys.argv):
        print('Generating article HTML...')

        if headline.get('tutorial'):
            what = 'a tutorial'
        elif headline.get('personal'):
            if headline.get('tutorial'):
                what = 'a tutorial post in a personal blog'
            else:
                what = 'a personal blog post'
        else:
            what = 'a decent journalist piece'

        chat = Conversation(model)
        output = chat.say(f'''Generate {what} titled "{title}" and published on {headline['domain']}.
        Take the article title quite literally — not as a metaphor/clickbait/prank or some April fool's joke! Must report like it's really happening, no matter how absurd.
        Produce HTML output with embedded styles. Generate at most one image per article.
        In the `alt` property of the generated <img> tag (if any), put a prompt for generating the corresponding image (without any prefix, just the prompt).
        Inject meta tags for og:title and og:description (with proper description).''')

        if '</html>' not in output:
            output += chat.say('continue from the exact character you stopped at')

        def replace_img(match):
            prompt = match.group(1)
            return f'src="./img.jpg" style="object-fit: cover; width: 50%; margin: 0 auto; display: block;" alt="{prompt}"'

        output = re.sub(r'src=".+" alt="(.+)"', replace_img, remove_triple_backticks(output), count=1)

        write_article_html(headline, remove_triple_backticks(output))

    dirname = os.path.dirname(get_article_file(headline))
    if not os.path.exists(f'{dirname}/img.jpg') or ('--image' in sys.argv):
        with open(get_article_file(headline), 'r') as f:
            prompt = re.search(r'alt="(.+)"', f.read()).group(1)
        print('Generating image for ' + prompt)
        dalle(f'{prompt}, professional blog post illustration', dirname)
