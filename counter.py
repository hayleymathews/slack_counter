import os
import time
import shlex
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

    if name:
        rec = db[team].counts.find_one(
            {'name': name}, {'_id': 0, 'count': 1, 'log': 1})

        if not rec:
            return jsonify({'text': '{} counter does not exist'.format(name),
                            'mrkdwn': True})

        count = rec['count']
        last_updates = '\n'.join(['`{:+.0f}` by <@{}> {}'.format(dtls['val'], dtls['user'], format_date(date))
                                  for date, dtls in sorted(rec['log'].items(), reverse=True)[:5]])
        return jsonify({'text': '*{}* count: `{:.0f}`  \n {}'.format(name, count, last_updates),
                        'mrkdwn': True})

    if private_channel:
        recs = db[team].counts.find({'$or': [{'hidden': {'$ne': True}},
                                             {'creator': user}]},
                                    {'name': 1, 'hidden': 1})
    else:
        recs = db[team].counts.find({'hidden': {'$ne': True}},
                                    {'name': 1})
    return jsonify({'text': '\n'.join(['*{}*'.format(rec['name']) if not rec.get('hidden') else '_{}_'.format(rec['name']) for rec in recs]),
                    'mrkdwn': True})


@app.route('/counter/incr', methods=['POST'])
def incr_counter():
    post_data = request.form.to_dict()
    team, user = post_data.get('team_id'), post_data['user_id']
    text = shlex.split(post_data.get('text', ''))
    name = text[0]
    val = float(try_index(text, 1, 1))
    hidden = try_index(text, 2, False) == 'hidden'
    locked = try_index(text, 3, False) == 'locked'

    rec = db[team].counts.find_one(
        {'name': name}, {'_id': 0, 'creator': 1, 'locked': 1})
    if rec and rec.get('locked') and rec['creator'] != user:
        return jsonify({'text': 'Can not increment a locked counter you do not own',
                        'mrkdwn': True})

    db[team].counts.update_one({'name': name},
                               {'$inc': {'count': val},
                                '$set': {'log.' + str(int(time.time() * 1000)): {'user': user, 'val': val}},
                                '$setOnInsert': {'creator': user, 'hidden': hidden, 'locked': locked}},
                               upsert=True)

    new_count = db[team].counts.find_one({'name': name}, {'_id': 0, 'count': 1})['count']
    return jsonify({'text': '`{:+.0f}` for: *{}* \n *{}* count: `{:.0f}`'.format(val, name, name, new_count),
                    'mrkdwn': True})


@app.route('/counter/del', methods=['POST'])
def delete_counter():
    post_data = request.form.to_dict()
    team, user = post_data.get('team_id'), post_data['user_id']
    name = post_data.get('text')

    rec = db[team].counts.find_one({'name': name}, {'_id': 0, 'creator': 1})
    if rec['creator'] != user:
        return jsonify({'text': 'Can not delete a counter you did not create',
                        'mrkdwn': True})

    db[team].counts.delete_one({'name': name})
    return jsonify({'text': '{} counter deleted'.format(name),
                    'mrkdwn': True})


if __name__ == '__main__':
    app.run()
