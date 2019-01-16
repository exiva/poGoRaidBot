from pymongo import MongoClient
import json

# Start database
client = MongoClient('192.168.1.35', 27017)

try:
    client.is_primary
except ServerSelectionTimeoutError:
    print("Couldn't connect to mongoDB.")
    raise

db = client['data']
# get our collections from the database.
db_regions = db.regions


with open('vs-lynbrook.geojson', 'r') as f:
    region = json.load(f)

    document = {
        'channel_id': 477520130310668288,
        'region_name': 'vs-lynbrook',
        'geometry' : region['features'][0]['geometry']
    }
    db_regions.insert_one(document)

#
# with open('gyms.csv', 'r') as f:
#     fields = ["name","url","external_id","lat","lon"]
#     dialect = csv.Sniffer().sniff(f.read(1024))
#     reader = csv.DictReader(f, fieldnames=fields, dialect=dialect)
#     f.seek(0)
#     for row in reader:
#         if not gym_db.find_one({'id': row['external_id']}):
#             print(f"{row['name']} is new. Adding to DB.")
#             document = {
#                 'id': row['external_id'],
#                 'added': datetime.datetime.utcnow(),
#                 'lastSeen': datetime.datetime.utcnow(),
#                 'name': row['name'],
#                 'isSponsored': False,
#                 'image': row['url'],
#                 'location': {
#                     'type': 'Point',
#                     'coordinates': [
#                         row['lat'],
#                         row['lon']
#                     ]
#                 }
#             }
#             gym_db.insert_one(document).inserted_id
#         else:
#             print(f"Updating {row['name']}")
#             document = {
#                 'name': row['name'],
#                 'image': row['url'],
#                 'lastSeen': datetime.datetime.utcnow()
#             }
#             gym_db.update_one({'id': row['external_id']}, {'$set': document}).modified_count
