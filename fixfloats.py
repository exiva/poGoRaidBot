from pymongo import MongoClient
import csv
import datetime

# Start database
client = MongoClient('192.168.1.35', 27017)

try:
    client.is_primary
except ServerSelectionTimeoutError:
    print("Couldn't connect to mongoDB.")
    raise

db = client['data']
# get our collections from the database.
gym_db = db.gyms
db_pokestops = db.pokestops
db_raids = db.raids

docs = db.get_collection('gyms')
for doc in docs.find():
    document = {
        'location': {
            'type': 'Point',
            'coordinates': [
                float(doc['location']['coordinates'][0]),
                float(doc['location']['coordinates'][1])
            ]
        }
    }
    # print(doc['id'])
    gym_db.update_one({'id': doc['id']}, {'$set': document}).modified_count
