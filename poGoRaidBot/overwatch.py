import logging
import datetime
import time
import random
from numpy import array_split as array_split
from queue import Queue
from poGoRaidBot import utils
from poGoRaidBot.search_worker import SearchWorker
from poGoRaidBot import chat_worker
from threading import Thread
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

log = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '[%(levelname)s] %(asctime)s [%(threadName)s] %(message)s',
    "%m/%d %I:%M:%S %p")
handler.setFormatter(formatter)
log.addHandler(handler)

log.setLevel(logging.INFO)

#Quiet some logging.
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('geocoder').setLevel(logging.ERROR)

msg_raid_queue = Queue()
msg_lure_queue = Queue()
db_raid_queue = Queue()
db_gym_queue = Queue()
db_pokestop_queue = Queue()

def process_pokestop(db, pokestop_queue):
    log.info("Starting pokestop db worker.")
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
                            pokestop['longitude'],
                            pokestop['latitude']
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
    log.info("Starting gym db worker.")
    while True:
        gyms = gym_queue.get()
        for gym in gyms:
            if not db.find_one({'id': gym['id']}):
                log.info(f"Adding new gym: {gym['id']}")
                document = {
                    'id': gym['id'],
                    'added': datetime.datetime.utcnow(),
                    'lastSeen': datetime.datetime.utcnow(),
                    'name': gym['name'],
                    'isSponsored': gym['sponsor'],
                    'isExRaidEligible': gym.get('isExRaidEligible', False),
                    'location': {
                        'type': 'Point',
                        'coordinates': [
                            gym['lng'],
                            gym['lat']
                        ]
                    }
                }
                db.insert_one(document).inserted_id
            else:
                document = {
                    'name': gym['name'],
                    'isSponsored': gym['sponsor'],
                    'lastSeen': datetime.datetime.utcnow(),
                    'isExRaidEligible': gym.get('isExRaidEligible', False),
                }
                db.update_one({'id': gym['id']}, {'$set': document}).modified_count
        gym_queue.task_done()

def process_raid(db, raid_queue):
    log.info("Starting raid db worker")
    while True:
        raids = raid_queue.get()
        for raid in raids:
            boss = raid['raid'].get('boss', {})
            pkmnid = boss.get('pokemon_id', None),
            if not db.find_one({'raid_id': raid['raid']['id']}):
                document = {
                    'raid_id': raid['raid']['id'],
                    'gym_id': raid['id'],
                    'level': raid['raid']['level'],
                    'added': datetime.datetime.utcnow(),
                    'spawn': datetime.datetime.fromtimestamp(raid['raid']['time_spawn']),
                    'battle': datetime.datetime.fromtimestamp(raid['raid']['time_battle']),
                    'end': datetime.datetime.fromtimestamp(raid['raid']['time_end']),
                    'pokemon_id': boss.get('pokemon_id', None),
                    'pokemon_form': boss.get('pokemon_form', None),
                    'pokemon_fast': boss.get('pokemon_move_fast', None),
                    'pokemon_charge': boss.get('pokemon_move_charge', None)
                }
                db.insert_one(document).inserted_id
            else:
                document = {
                    'pokemon_id': boss.get('pokemon_id', None),
                    'pokemon_form': boss.get('pokemon_form', None),
                    'pokemon_fast': boss.get('pokemon_move_fast', None),
                    'pokemon_charge': boss.get('pokemon_move_charge', None)
                }
                db.update_one({'raid_id': raid['raid']['id']}, {'$set': document}).modified_count
        raid_queue.task_done()


def overwatch(args, config):
    ''' Main overwatch thread '''

    log.debug(f"args {args}")
    log.debug(f"config {config}")
    accounts = Queue()

    global db_raid_queue
    global db_gym_queue
    global db_pokestop_queue

    locations = []
    # generate_search area
    if args.north: #create search area from s2 cells
        for coords in utils.generate_cells(args.north[0], args.north[1], args.south[0], args.south[1], args.level):
            locations.append(coords)
    elif args.latitude: #create search area from spiral
        for coords in utils.generate_spiral(args.latitude, args.longitude, args.step_size, args.step_limit):
            locations.append(coords)
    else: #load area from CSV
        locations = args.area

    # Start database
    client = MongoClient(config['mongodb']['hostname'], config['mongodb']['port'])

    try:
        client.is_primary
    except ServerSelectionTimeoutError:
        log.error("Couldn't connect to mongoDB.")
        raise

    db = client[config['mongodb']['database']]
    # get our collections from the database.
    db_gyms = db.gyms
    db_pokestops = db.pokestops
    db_raids = db.raids
    db_regions = db.regions

    # spin up db queue worker.
    db_pokestop_thread = Thread(target=process_pokestop, name='Pokestop-Database-Worker', args=(db_pokestops, db_pokestop_queue))
    db_pokestop_thread.start()

    db_gym_thread = Thread(target=process_gym, name='Gym-Database-Worker', args=(db_gyms, db_gym_queue))
    db_gym_thread.daemon = True
    db_gym_thread.start()

    db_raid_thread = Thread(target=process_raid, name="Raid-DB-Worker", args=(db_raids, db_raid_queue))
    db_raid_thread.start()

    # bring up chat bot thread
    chat_thread = Thread(target=chat_worker.raid_chat_worker, name='ChatThread', args=(args, config, db_raids, db_regions, msg_raid_queue))
    chat_thread.start()
    #
    # lure_chat_thread = Thread(target=chat_worker.lure_chat_worker, name='LureChatThread', args=(args, config, msg_lure_queue))
    # lure_chat_thread.start()

    # start search thread
    # search_area = array_split(locations, len(config['devices']))
    # search_thread = Thread(target=search_worker.search_worker, name='Search-Worker',
    #                        args=(args, config, search_area, db_pokestops, db_gyms, msg_raid_queue, msg_lure_queue,
    #                              db_raid_queue, db_gym_queue, db_pokestop_queue))
    # search_thread.start()
    #

    #args=(args, config, search_area, db_pokestops, db_gyms, msg_raid_queue, msg_lure_queue,
    # db_raid_queue, db_gym_queue, db_pokestop_queue))
    locs = array_split(locations, len(config['devices']))

    devices = {}

    for i, device in enumerate(config['devices']):
        devices[device['uuid']] = {
            'identifier': device['identifer'],
            'locations': locs[i].tolist(),
            'position': 0,
            'emptyScan': 0,
            'lastscan': datetime.datetime.now().timestamp()
        }

    log.info(f"{len(config['devices'])} devices configured with {len(locs[0])} locations each.")

    server = SearchWorker(config=config, devices=devices, pokestop_db=db_pokestops,
        gym_db=db_gyms, raid_queue=msg_raid_queue, gym_db_queue=db_gym_queue,
        pokestop_db_queue=db_pokestop_queue, raid_db_queue=db_raid_queue
        )
    log.info(f"Starting server at http://{config['server']['host']}:{config['server']['port']}")

    server.run(threaded=True, use_reloader=False, debug=False,
                host=config['server']['host'], port=config['server']['port'])
