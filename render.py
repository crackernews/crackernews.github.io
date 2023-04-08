
import os
import html
import json
import re
import random
import pandas as pd


def read_json(file):
    with open(file, 'r') as f:
        return json.load(f)


def write_json(file, obj):
    with open(file, 'w') as f:
        json.dump(obj, f, indent=4)


def plural(str, count):
    return f"{str}{'s'[:count^1]}"


def render_ago(ts):
    age = pd.Timestamp.now() - pd.Timestamp(ts)
    minutes = max(1, age.seconds // 60)
    hours = age.seconds // 3600
    ago = ''
    if age.days: ago = str(age.days) + f' {plural("day", age.days)}'
    elif hours: ago = str(hours) + f' {plural("hour", hours)}'
    elif minutes: ago = str(minutes) + f' {plural("minute", minutes)}'
    return ago


def render_headline(rank, headline, slug, domain, user, points, comments, posted, personal=False, tutorial=False):
    return f'''<tr class="athing">
    <td align="right" valign="top" class="title"><span class="rank">{rank}.</span></td>      <td valign="top" class="votelinks"><center><a href="javascript:void(0)"><div class="votearrow" title="upvote"></div></a></center></td><td class="title"><span class="titleline"><a href="/articles/{domain}-{slug}/">{headline}</a><span class="sitebit comhead"> (<a href="https://{domain}"><span class="sitestr">{domain}</span></a>)</span></span></td></tr><tr><td colspan="2"></td><td class="subtext"><span class="subline">
        <span class="score">{points} {plural("points", points)}</span> by <a href="https://news.ycombinator.com/user?id={user}" class="hnuser">{user}</a> <span class="age" title="{posted}"><a href="javascript:void(0)">{render_ago(posted)} ago</a></span> <span></span> | <a href="./comments/{domain}-{slug}/">{comments}&nbsp;{plural("comment", comments)}</a>        </span>
    </td></tr>
    <tr class="spacer" style="height:5px"></tr>
    '''


def parse_comments(item, gpt_comments):
    lines = gpt_comments.split('\n')
    since = 1
    for line in lines:
        if not line.strip(): continue
        since = random.randint(since, 60)
        posted = pd.Timestamp(item['posted']) + pd.Timedelta(minutes=since)
        indent, user, text = re.match(r'^(\s*)([^:]+): (.+)$', line).groups()
        yield dict(indent=len(indent) // 4, user=user, text=text, posted=str(posted))


def render_comment(indent, user, text, posted):
    return f'''<tr class="athing comtr"><td><table border="0">  <tbody><tr>    <td class="ind" indent="1"><img src="./comments.template_files/s.gif" height="1" width="{indent * 40}"></td><td valign="top" class="votelinks">
      <center><a href="javascript:void(0)"><div class="votearrow" title="upvote"></div></a></center>    </td><td class="default"><div style="margin-top:2px; margin-bottom:-10px;"><span class="comhead">
          <a href="https://news.ycombinator.com/user?id={user}" class="hnuser">{user}</a> <span class="age" title="{posted}"><a href="javascript:void(0)">{render_ago(posted)} ago</a></span> <span></span>          <span class="navs">
             | <a href="javascript:void(0)" class="clicky" aria-hidden="true">parent</a> | <a href="javascript:void(0)" class="clicky" aria-hidden="true">next</a> <a class="togg clicky" href="javascript:void(0)">[–]</a><span class="onstory"></span>          </span>
                  </span></div><br><div class="comment">
                  <span class="commtext c00">{html.escape(text)}</span>
              <div class="reply">        <p><font size="1">
                      <u><a href="javascript:void(0)">reply</a></u>
                  </font>
      </p></div></div></td></tr>
        </tbody></table></td></tr>'''


def render_comments_headline(headline, slug, domain, user, points, comments, posted, personal=False, tutorial=False):
    return f'''<tr class="athing">
      <td align="right" valign="top" class="title"><span class="rank"></span></td>      <td valign="top" class="votelinks"><center><a href="javascript:void(0)"><div class="votearrow" title="upvote"></div></a></center></td><td class="title"><span class="titleline"><a href="/articles/{domain}-{slug}/">{headline}</a><span class="sitebit comhead"> (<a href="https://{domain}"><span class="sitestr">{domain}</span></a>)</span></span></td></tr><tr><td colspan="2"></td><td class="subtext"><span class="subline">
          <span class="score">{plural("point", points)}</span> by <a href="https://news.ycombinator.com/user?id={user}" class="hnuser">{user}</a> <span class="age" title="{posted}"><a href="javascript:void(0)">{render_ago(posted)} ago</a></span> <span></span> | <a href="javascript:void(0)" class="hnpast">past</a> | <a href="javascript:void(0)">favorite</a> | <a href="javascript:void(0)">{comments}&nbsp;comments</a>        </span>
              </td></tr>'''


def get_dirname(item):
    return item['domain'] + '-' + item['slug']


def get_dir(item, dir, mkdir=False):
    folder = dir + '/' + get_dirname(item)
    if mkdir:
        os.makedirs(folder, exist_ok=True)
    return folder


def get_comments_file(item, mkdir=False):
    return get_dir(item, 'comments', mkdir) + '/comments.json'


def get_article_file(item, mkdir=False):
    return get_dir(item, 'articles', mkdir) + '/index.html'


def write_article_html(item, html):
    with open(get_article_file(item, mkdir=True), 'w') as f:
        f.write(html)


def write_comments(item, gpt_comments):
    comments = [*parse_comments(item, gpt_comments)]
    item['comments'] = len(comments)
    write_json(get_comments_file(item, mkdir=True), comments)


def render_html(headlines):
    with open('index.template.html', 'r') as f:
        template = f.read()
        template = template.replace('$HERE', '\n'.join(render_headline(i + 1, **item) for i, item in enumerate(reversed(headlines))))
        with open('index.html', 'w') as f:
            f.write(template)

    for item in headlines:
        comments = read_json(get_comments_file(item))
        with open('comments.template.html', 'r') as f:
            template = f.read()
            template = template.replace('$TITLE', html.escape(item['headline']))
            template = template.replace('$HEADLINE', render_comments_headline(**item))
            template = template.replace('$COMMENTS', '\n'.join(render_comment(**c) for c in comments))
            with open(get_dir(item, 'comments') + '/index.html', 'w') as f:
                f.write(template)