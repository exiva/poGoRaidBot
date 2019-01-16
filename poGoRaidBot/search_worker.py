import time
import datetime
import random
import requests
from .account import accountManager, CaptchaException
from .fort_parser import parseGym, parsePokestop
# from .conditions import weather_conditions
from geopy.distance import great_circle

# import queue
from pgoapi import utilities as util
from pgoapi.exceptions import AuthException, NotLoggedInException, BannedAccountException

# def actHuman():


def sendStatus(worker, status, config):
    if status == 0:
        content = f":white_check_mark: {worker} logged in successfully."
    elif status == 1:
        content = f":dizzy_face::hammer: {worker} was smashed with the banhammer."
    else:
        content = f":no_entry_sign::cop: {worker} was sent to reCaptcha jail!"
    payload = {
        'content': content
    }
    requests.post("https://discordapp.com/api/webhooks/{}".format(config['discord']['bot_status']), json=payload)

def search_worker(args, config, account, coords, db, gym_db, m_raid_queue, m_lure_queue, d_raid_queue, d_gym_queue, d_pokestop_queue):
    account = account.get()

    # location = None
    lastLocation = {"lat": 0, "lng": 0}
    retryCount = 1
    if args.proxy or config['proxy'].get('enabled'):
        print("*** Proxy enabled")
        proxy = config['proxy'].get('host')
        api = accountManager(username=account['username'], password=account['password'],
            hashkey=config.get('hashkey'), service=account['type'], version=config.get('version'), proxy=proxy)
    else:
        api = accountManager(username=account['username'], password=account['password'],
            hashkey=config.get('hashkey'), service=account['type'], version=config.get('version'))

    while retryCount <= 3:
        for i, coord in enumerate(coords):
            if i == 0 or great_circle((lastLocation['lat'],lastLocation['lng']),(coord['lat'],coord['lng'])).miles > 1.3:
                delay = random.randint(20,30)
                print("{} is taking a rest for {}s before searching. moved {} mi".format(account['username'], delay, great_circle((lastLocation['lat'],lastLocation['lng']),(coord['lat'],coord['lng'])).miles))
                time.sleep(delay)
            api.setPosition(coord['lat'], coord['lng'], alt=random.uniform(10.000, 10.999))
            time.sleep(random.randint(1.1,2.1))
            try:
                if api.isLoggedin():
                    retryCount = 1 #We're logged in. Reset our counter.
                    fort_count = 0
                    pokestop_count = 0
                    gym_count = 0
                    map_retry = 1
                    forts = []
                    gyms = []
                    pokestops = []
                    raids = []
                    lures= []
                    cell_ids = util.get_cell_ids(coord['lat'], coord['lng'], radius=765)
                    timestamps = [0,] * len(cell_ids)
                    success = False
                    # condition = weather_conditions

                    while not success and map_retry < 2:
                        # currentWeather = []
                        map_objects = api.request(lambda req: req.get_map_objects(
                            latitude = coord['lat'],
                            longitude = coord['lng'],
                            since_timestamp_ms = timestamps,
                            cell_id = cell_ids))
                        if not map_objects['GET_MAP_OBJECTS'].get('map_cells', None):
                            if config['discord']['enabled']:
                                sendStatus(account['username'], 1, config)
                                raise BannedAccountException
                        # for weather in map_objects['GET_MAP_OBJECTS'].get('client_weather', {}):
                        #     active_alert = weather.get('alerts', {})
                        #     weatherItem = {
                        #         "display": condition[weather['gameplay_weather'].get('gameplay_condition')],
                        #         "alert": active_alert
                        #         }
                        #     currentWeather.append(weatherItem)
                        for i, cell in enumerate(map_objects['GET_MAP_OBJECTS']['map_cells']):
                            fort = cell.get('forts', None)
                            if fort:
                                forts += fort
                                fort_count += len(fort)

                        success = True
                    # print("Found {} forts. Got {} forts".format(fort_count, len(forts)))
                    # print("Got {} forts".format(len(forts)))
                    # print("Scanned forts: {}".format(forts))

                    for f in forts:
                        f_type = f.get('type', 0)
                        f_raid = f.get('raid_info', None)
                        f_id = f['id']
                        f_lat = f['latitude']
                        f_lng = f['longitude']
                        # if f_type == 0 and (f_raid or not gym_db.find_one({'id': f_id})): # Gym
                        if f_type == 0 and (f_raid or not gym_db.find_one({'id': f_id})): # Gym
                            gym_count += 1
                            # print("fort {} is a gym".format(f_id))
                            r_gym = api.request(lambda req: req.gym_get_info(
                                                gym_id=f_id,
                                                player_lat_degrees=coord['lat'],
                                                player_lng_degrees=coord['lng'],
                                                gym_lat_degrees = f_lat,
                                                gym_lng_degrees = f_lng
                                            ))
                            if r_gym['GYM_GET_INFO'].get('gym_status_and_defenders'):
                                gym, raid = parseGym(r_gym.get('GYM_GET_INFO'))
                                if raid:
                                    gym['raid'] = raid
                                    # print("raid info: {}".format(raid))
                                    raids.append(gym)
                                # print("overall gym info: {}".format(gym))
                                gyms.append(gym)
                            else:
                                print("Likely too far away from gym {}".format(f_id))
                        elif gym_db.find_one({'id': f_id}):
                            gym_db.update_one({'id': f_id},
                                            {'$set': {'lastSeen': datetime.datetime.utcnow()}
                                            }).modified_count
                        elif f_type == 1: # Pokestop
                            # print("fort {} is a pokestop".format(f_id))
                            pokestop_count += 1
                            f_modifier = f.get('active_fort_modifier', None) # look for a lure
                            if f_modifier or not db.find_one({'id': f_id}):
                                r_pokestop = api.request(lambda req: req.fort_details(
                                                        fort_id = f_id,
                                                        latitude = f_lat,
                                                        longitude = f_lng
                                                    ))
                                pokestop = parsePokestop(r_pokestop.get('FORT_DETAILS', None))
                                # print("pokestop info: {}".format(pokestop))
                                pokestops.append(pokestop)
                                if f_modifier:
                                    lures.append(pokestop)
                            elif db.find_one({'id': f_id}):
                                gym_db.update_one({'id': f_id},
                                                {'$set': {'lastSeen': datetime.datetime.utcnow()}
                                                }).modified_count
                    print("Scanned {},{} with {}. Found Forts: {} [Gyms: {} (Parsed: {} Raids: {}) Pokestops: {} (Lures: {})] Weather: {}"
                            .format(coord['lat'], coord['lng'], account['username'],
                                    fort_count, gym_count, len(gyms), len(raids), pokestop_count, len(lures),
                                    ))
                    # print("-----------------------------------------------------")
                    # push results to queues.
                    d_gym_queue.put(gyms)

                    d_pokestop_queue.put(pokestops)
                    if raids:
                        m_raid_queue.put(raids)
                        d_raid_queue.put(raids)
                    if lures:
                        m_lure_queue.put(lures)


                    lastLocation = coord
                    time.sleep(random.randint(5,10))
                else:
                    print(f"{account['username']} failed to login. Sleeping 30s.")
                    time.sleep(30)
                    raise AuthException
            except (AuthException, NotLoggedInException):
                print("Lost our auth token. Trying to login again. {} of 3 retries.".format(retryCount))
                retryCount = retryCount+1
                if args.proxy or config['proxy'].get('enabled'):
                    print("*** Proxy enabled")
                    proxy = config['proxy'].get('host')
                    api = accountManager(username=account['username'], password=account['password'],
                        hashkey=config.get('hashkey'), service=account['type'], version=config.get('version'), proxy=proxy)
                else:
                    api = accountManager(username=account['username'], password=account['password'],
                        hashkey=config.get('hashkey'), service=account['type'], version=config.get('version'))
                api.setPosition(coord['lat'], coord['lng'], alt=random.uniform(10.000, 10.999))
                time.sleep(random.uniform(30,60))
            except CaptchaException:
                if config['discord']['enabled']:
                    sendStatus(account['username'], 2, config)
                raise CaptchaException
