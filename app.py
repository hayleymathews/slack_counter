import os
import time
import shlex
import requests
from datetime import datetime
from collections import defaultdict
from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

mongo_url = os.environ.get('MONGODB_URI', "mongodb://localhost:27017/")
db = MongoClient(mongo_url)


def format_date(timestamp_string):
    return datetime.fromtimestamp(int(timestamp_string) / 1000.).strftime("%b %d %Y %I:%M%p")


def try_index(listy, index, default=None):
    try:
        return listy[index]
    except:
        return default


@app.route('/counter', methods=['GET', 'POST'])
def counter():
    post_data = request.form.to_dict()
    team, user = post_data.get('team_id'), post_data['user_id']
    name = post_data.get('text')
    private_channel = post_data.get('channel_name') == 'directmessage'
    response_url = post_data['response_url']

    if name:
        rec = db['counter_db'].counts.find_one({'name': name, 'team': team}, {'_id': 0, 'count': 1, 'log': 1})

        if not rec:
            payload = {'text': '*{}* counter does not exist'.format(name),
                       'response_type': 'in_channel',
                       'mrkdwn': True}
            return requests.post(response_url, json=payload)

        payload = {'text': '*{}* count: `{:.0f}`  \n {}'.format(name, rec['count'], last_updates),
                   'response_type': 'in_channel',
                   'attachments': [{'text': '`{:+.0f}` by <@{}> {}'.format(dtls['val'], dtls['user'], format_date(date))}
                                   for date, dtls in sorted(rec['log'].items(), reverse=True)[:5]],
                   'mrkdwn': True}
                   return requests.post(response_url, json=payload)

    if private_channel:
        recs = list(db['counter_db'].counts.find({'$or': [{'hidden': {'$ne': True}},
                                                          {'creator': user}],
                                                  'team': team},
                                                 {'name': 1, 'hidden': 1}))
    else:
        recs = list(db['counter_db'].counts.find({'hidden': {'$ne': True}, 'team': team}, {'name': 1}))

    if not recs:
        payload = {'text': 'No counters created yet',
                   'response_type': 'in_channel',
                   'mrkdwn': True}
        return requests.post(response_url, json=payload)
    
    payload = {'text': '\n'.join(['*{}*'.format(rec['name']) if not rec.get('hidden') else '_{}_'.format(rec['name']) for rec in recs]),
               'response_type': 'in_channel',
               'mrkdwn': True}
    return requests.post(response_url, json=payload)


@app.route('/counter/incr', methods=['POST'])
def incr_counter():
    post_data = request.form.to_dict()
    team, user = post_data.get('team_id'), post_data['user_id']
    text = shlex.split(post_data.get('text', ''))
    name = text[0]
    val = float(try_index(text, 1, 1))
    hidden = try_index(text, 2, False) == 'hidden'
    locked = try_index(text, 3, False) == 'locked'
    response_url = post_data['response_url']

    rec = db['counter_db'].counts.find_one({'name': name, 'team': team}, {'_id': 0, 'creator': 1, 'locked': 1})
    if rec and rec.get('locked') and rec['creator'] != user:
        payload = {'text': 'Can not increment a locked counter you do not own',
                   'response_type': 'in_channel',
                   'mrkdwn': True}
        return requests.post(response_url, json=payload)

    db['counter_db'].counts.update_one({'name': name, 'team': team},
                                       {'$inc': {'count': val},
                                        '$set': {'log.' + str(int(time.time() * 1000)): {'user': user, 'val': val}},
                                        '$setOnInsert': {'creator': user, 'hidden': hidden, 'locked': locked, 'team': team}},
                                       upsert=True)

    new_count = db['counter_db'].counts.find_one({'name': name, 'team': team}, {'_id': 0, 'count': 1})['count']
    payload = {'text': '`{:+.0f}` for: *{}* \n *{}* count: `{:.0f}`'.format(val, name, name, new_count),
               'response_type': 'in_channel',
               'mrkdwn': True}
    return requests.post(response_url, json=payload)


@app.route('/counter/del', methods=['POST'])
def delete_counter():
    post_data = request.form.to_dict()
    team, user = post_data.get('team_id'), post_data['user_id']
    name = post_data.get('text')
    response_url = post_data['response_url']

    rec = db['counter_db'].counts.find_one(
        {'name': name, 'team': team}, {'_id': 0, 'creator': 1})
    if rec['creator'] != user:
        payload = {'text': 'Can not delete a counter you did not create',
                   'response_type': 'in_channel',
                   'mrkdwn': True}
        return requests.post(response_url, json=payload)

    db['counter_db'].counts.delete_one({'name': name, 'team': team})
    payload = {'text': '*{}* counter deleted'.format(name),
               'response_type': 'in_channel',
               'mrkdwn': True}
    return requests.post(response_url, json=payload)


if __name__ == '__main__':
    app.run()
