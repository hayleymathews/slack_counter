from flask import Flask, request, jsonify
from collections import defaultdict
from pymongo import MongoClient


app = Flask(__name__)

db = MongoClient("mongodb://localhost:27017/")['counter']


@app.route('/counter', methods=['GET', 'POST'])
def counter():
    name = request.args.get('name')
    if name:
        return jsonify(db.counts.find_one({'name': name}, {'_id': 0}))
    vals = [doc for doc in db.counts.find({}, {'_id': 0})]
    return jsonify({'results': vals})

@app.route('/counter/incr', methods=['POST'])
def incr_counter():
    post_data = request.form.to_dict()
    name, val = post_data.get('text', '').split(' ')
    val = float(val)
    db.counts.update_one({'name': name}, {'$inc': {'count': val}}, upsert=True)
    new_count = db.counts.find_one({'name': name}, {'_id': 0, 'count': 1})['count']
    return jsonify({'text': '*{}* mentioned `{:.0f}` times'.format(name, new_count),
                    'mrkdwn': True})

@app.route('/counter/del', methods=['POST'])
def delete_counter():
    post_data = request.form
    name = post_data['name']
    db.counts.delete_one({'name': name})
    return jsonify({'deleted': True})


if __name__ == '__main__':
    app.run()