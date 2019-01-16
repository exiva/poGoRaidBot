from pymongo import MongoClient
import json

client = MongoClient('192.168.1.35', 27017)
db = client['data']
db_pokestops = db.pokestops
query = db_pokestops.find({}, {'_id': 0, 'id': 0, 'added': 0, 'lastSeen': 0, 'description': 0})
pokestops = []
for doc in query:
  pokestops.append(doc)

with open('pokestops.json', 'w') as fp:
    json.dump(pokestops, fp)
