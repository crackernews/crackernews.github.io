
import json
import requests
from uuid import uuid4

requests.adapters.DEFAULT_RETRIES = 1


class Conversation:
    def __init__(self, model='text-davinci-002-render-sha'):
        self.model = model
        self.conversation_id = None
        self.last_message_id = None
            
    def say(self, text, model=None):
        payload = {
            "action":"next",
            "messages":[
                {
                    "id": str(uuid4()),
                    "author": {"role":"user"},
                    "content": {
                        "content_type":"text",
                        "parts":[text]
                    }
                }
            ],
            "parent_message_id": str(uuid4()),
            "model": model or self.model,
            "timezone_offset_min":-180,
        }
        if self.conversation_id:
            payload['conversation_id'] = self.conversation_id
            payload['parent_message_id'] = self.last_message_id
        payload = json.dumps(payload)
        with open('token', 'r') as f:
            token = f.read()
        with open('cookie', 'r') as f:
            cookie = f.read()
        headers = {
            'accept': 'text/event-stream',
            'authorization': f'Bearer {token}',
            'content-length': str(len(payload)),
            'content-type': 'application/json',
            'origin': 'https://chat.openai.com',
            'referer': 'https://chat.openai.com/chat',
            'cookie': cookie,
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        }
        response = requests.post(
            'https://chat.openai.com/backend-api/conversation',
            headers=headers,
            data=payload
        )
        if response.status_code != 200:
            print(response)
            print(response.text)
            response.raise_for_status()

        last_one = [x for x in response.text.split('\n') if x][-2]
        last_one = last_one[len('data: '):]
        last_one = json.loads(last_one)

        if last_one['error']:
            raise ValueError(last_one['error'])
        
        self.conversation_id = last_one['conversation_id']
        self.last_message_id = last_one['message']['id']

        content = last_one['message']['content']
        if content['content_type'] != 'text' or len(content['parts']) != 1:
            print('Unusual response!')
            print(content)
            raise ValueError('unusual response')
        return content['parts'][0]


def dalle(prompt):
    with open('apikey', 'r') as f:
        key = f.read()
    response = requests.post(
        'https://api.openai.com/v1/images/generations',
        headers={
            "Content-Type": "application/json",
            "Authorization": f'Bearer {key}'
        },
        json=dict(
            prompt=prompt,
            size="1024x1024",
            n=1
        )
    )
    print(response)
    print(response.text)
    if response.status_code != 200:
        response.raise_for_status()
    return response.json()['data'][0]['url']
