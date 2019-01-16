import datetime
import time
import random
from numpy import array_split as array_split
from queue import Queue
from poGoRaidBot import utils
from poGoRaidBot import search_worker
from poGoRaidBot import chat_worker
from threading import Thread
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError


def process_pokestop(db, pokestop_queue):
    print("Starting pokestop db worker.")
    while True:
        pokestops = pokestop_queue.get()
        # print("processing pokestop: {}".format(pokestop))
        for pokestop in pokestops:
            if not db.find_one({'id': pokestop['pokestop_id']}):
                document = {
                    'id': pokestop['pokestop_id'],
                    'added': datetime.datetime.utcnow(),
                    'name': pokestop['pokestop_name'],
                    'description': pokestop['pokestop_desc'],
                    'location': {
                        'type': 'Point',
                        'coordinates': [
                            pokestop['latitude'],
                            pokestop['longitude']
                        ]
                    }
                }
                db.insert_one(document).inserted_id
            else:
                document = {
                    'lastSeen': datetime.datetime.utcnow(),
                    'name': pokestop['pokestop_name'],
                    'description': pokestop['pokestop_desc']
                }
                db.update_one({'id': pokestop['pokestop_id']}, {'$set': document}).modified_count
        pokestop_queue.task_done()


def process_gym(db, gym_queue):
    print("Starting gym db worker.")
    while True:
        gyms = gym_queue.get()
        # print("processing gym: {}".format(gym))
        for gym in gyms:
            if not db.find_one({'id': gym['id']}):
                document = {
                    'id': gym['id'],
                    'added': datetime.datetime.utcnow(),
                    'lastSeen': datetime.datetime.utcnow(),
                    'name': gym['name'],
                    'isSponsored': gym['sponsor'],
                    'location': {
                        'type': 'Point',
                        'coordinates': [
                            gym['lat'],
                            gym['lng']
                        ]
                    }
                }
                db.insert_one(document).inserted_id
            else:
                document = {
                    'name': gym['name'],
                    'isSponsored': gym['sponsor'],
                    'lastSeen': datetime.datetime.utcnow()
                }
                db.update_one({'id': gym['id']}, {'$set': document}).modified_count
        gym_queue.task_done()


def process_raid(db, raid_queue):
    print("Starting raid db worker")
    # while True:
    #     raids = raid_queue.get()
    #     for raid in raids:
    #         if not db.find_one({'id': raid['id']})
    #         document = {
    #             'id': raid['id'],
    #             'level': raid['level'],
    #             'added': datetime.datetime.utcnow(),
    #             'spawn': datetime.datetime.fromtimestamp(raid['time_spawn']),
    #             'battle': datetime.datetime.fromtimestamp(raid['time_battle']),
    #             ''
    #         }


def overwatch(args, config):
    ''' Main overwatch thread '''
    # print(args)
    # print(config)
    accounts = Queue()
    # spiral_queue = Queue()

    msg_raid_queue = Queue()
    msg_lure_queue = Queue()
    db_raid_queue = Queue()
    db_gym_queue = Queue()
    db_pokestop_queue = Queue()

    locations = []
    # generate_search area
    if args.north:
        # for coords in utils.generate_cells(40.911430, -73.755572, 40.578110, -73.423889):
        for coords in utils.generate_cells(args.north[0], args.north[1], args.south[0], args.south[1]):
            locations.append(coords)
    else:
        for coords in utils.generate_spiral(args.latitude, args.longitude, args.step_size, args.step_limit):
            locations.append(coords)
    # for coords in utils.generate_spiral(args.latitude, args.longitude, args.step_size, args.step_limit):

        # spiral_queue.put(coords)
        # locations.append(coords)

    # Start database
    client = MongoClient(config['mongodb']['hostname'], config['mongodb']['port'])

    try:
        client.is_primary
    except ServerSelectionTimeoutError:
        print("Couldn't connect to mongoDB.")
        raise

    db = client[config['mongodb']['database']]
    # get our collections from the database.
    db_gyms = db.gyms
    db_pokestops = db.pokestops
    db_raids = db.raids

    # spin up db queue worker.
    db_pokestop_thread = Thread(target=process_pokestop, name='Pokestop-Database-Worker', args=(db_pokestops))
    db_pokestop_thread.start()

    db_gym_thread = Thread(target=process_gym, name='Gym-Database-Worker', args=(db_gyms, db_gym_queue))
    db_gym_thread.start()

    db_raid_thread = Thread(target=process_raid, name="Raid-DB-Worker", args=(db_raids, db_raid_queue))
    db_raid_thread.start()

    # bring up chat bot thread
    chat_thread = Thread(target=chat_worker.raid_chat_worker, name='ChatThread', args=(args, config, msg_raid_queue))
    chat_thread.start()

    lure_chat_thread = Thread(target=chat_worker.lure_chat_worker, name='LureChatThread', args=(args, config, msg_lure_queue))
    lure_chat_thread.start()

    # start our workers.
    for account in config['accounts']:
        accounts.put(account)

    locs = array_split(locations, len(config['accounts']))
    for i in range(len(config['accounts'])):
        # search_area = locations[i::len(config['accounts'])]
        # stagger launch
        time.sleep(random.randint(2, 10))
        search_area = locs[i]
        worker_thread = Thread(target=search_worker.search_worker, name='Search-Worker-{}'.format(i),
                               args=(args, config, accounts, search_area, db_pokestops, db_gyms, msg_raid_queue, msg_lure_queue,
                                     db_raid_queue, db_gym_queue, db_pokestop_queue))
        worker_thread.start()
