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


with open('ingress.csv', 'r') as f:
    # str = portalGuid + ",\"" + str + "\"," + url + "," + lat + "," + lng
    fields = ["external_id","name","url","lat","lon"]
    dialect = csv.Sniffer().sniff(f.read(1024))
    reader = csv.DictReader(f, fieldnames=fields, dialect=dialect)
    f.seek(0)
    for row in reader:
        gym = gym_db.find_one({'id': row['external_id']})
        pokestop = db_pokestops.find_one({'id': row['external_id']})
        if gym and gym['name'] == "Unknown Gym Name":
            print(f"Updating {row['name']}")
            document = {
                'name': row['name'],
                'image': row['url'],
            }
            gym_db.update_one({'id': row['external_id']}, {'$set': document}).modified_count

        if pokestop and pokestop['name'] is None:
            print(f"Updating {row['name']}")
            document = {
                'name': row['name'],
                'image': row['url'],
            }
            db_pokestops.update_one({'id': row['external_id']}, {'$set': document}).modified_count
