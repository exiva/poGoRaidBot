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


with open('pokestops.csv', 'r') as f:
    fields = ["name","url","external_id","lat","lon"]
    dialect = csv.Sniffer().sniff(f.read(1024))
    reader = csv.DictReader(f, fieldnames=fields, dialect=dialect)
    f.seek(0)
    for row in reader:
        if not db_pokestops.find_one({'id': row['external_id']}):
            print(f"{row['name']} is new. Adding to DB.")
            document = {
                'id': row['external_id'],
                'added': datetime.datetime.utcnow(),
                'lastSeen': datetime.datetime.utcnow(),
                'name': row['name'],
                'image': row['url'],
                'location': {
                    'type': 'Point',
                    'coordinates': [
                        row['lat'],
                        row['lon']
                    ]
                }
            }
            db_pokestops.insert_one(document).inserted_id
        else:
            print(f"Updating {row['name']}")
            document = {
                'name': row['name'],
                'image': row['url'],
                'lastSeen': datetime.datetime.utcnow()
            }
            db_pokestops.update_one({'id': row['external_id']}, {'$set': document}).modified_count
