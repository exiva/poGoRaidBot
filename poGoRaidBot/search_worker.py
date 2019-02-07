import logging
import time
import datetime
import random
import requests
import s2sphere
import ctypes
from .fort_parser import parseGym, parsePokestop
from geopy.distance import great_circle
from flask import Flask, jsonify, request, make_response, json
from flask.json import JSONEncoder
from base64 import b64decode
from poGoRaidBot import utils

from threading import Thread
from queue import Queue

from google.protobuf.json_format import MessageToJson
from .protos.pogoprotos.networking.responses.fort_search_response_pb2 import FortSearchResponse
from .protos.pogoprotos.networking.responses.get_map_objects_response_pb2 import GetMapObjectsResponse
from .protos.pogoprotos.networking.responses.gym_get_info_response_pb2 import GymGetInfoResponse
from .protos.pogoprotos.networking.responses.fort_details_response_pb2 import FortDetailsResponse

log = logging.getLogger(__name__)

class SearchWorker(Flask):
    def __init__(self, *args, **kwargs):
        if not args:
            kwargs.setdefault('import_name',__name__)

        #get args
        self.config = kwargs.get('config')
        self.devices = kwargs.get('devices')
        self.pokestop_db = kwargs.get('pokestop_db')
        self.gym_db = kwargs.get('gym_db')
        self.raid_queue = kwargs.get('raid_queue')
        self.gym_db_queue = kwargs.get('gym_db_queue')
        self.pokestop_db_queue = kwargs.get('pokestop_db_queue')
        self.raid_db_queue = kwargs.get('raid_db_queue')
        self.weatherConditions = {}

        self.process_queue = Queue()

        #clear kwargs
        kwargs.pop('config')
        kwargs.pop('devices')
        kwargs.pop('pokestop_db')
        kwargs.pop('gym_db')
        kwargs.pop('raid_queue')
        kwargs.pop('gym_db_queue')
        kwargs.pop('pokestop_db_queue')
        kwargs.pop('raid_db_queue')

        # self.args = kwargs.get('args')
        # kwargs.pop('args')
        super(SearchWorker, self).__init__(*args, **kwargs)

        # start data worker thread
        self.processThread = Thread(target=self.parseData, name='HTTP-Data-Process', args=(self, self.process_queue))
        self.processThread.start()

        #define routes
        self.route("/", methods=['GET'])(self.index)
        self.route("/loc", methods=['POST'])(self.getLocation)
        self.route("/data", methods=['POST'])(self.getData)
        self.route("/status", methods=['GET'])(self.status)

    def index(self):
        return "A Wild MissingNo. Appeared!"

    def parseData(self, *args):
        log.info('Starting Data processing thread')
        while True:
            try:
                map_objects = self.process_queue.get()
                #decode b64 delivered message from ++
                response = b64decode(map_objects)
                #decde raw protos to JSON
                gmo = GetMapObjectsResponse()
                gmo.ParseFromString(response)
                gmo_response = json.loads(MessageToJson(gmo))
            except:
                log.error("Caught exception decoding message.")
                continue

            try:
                weather = gmo_response['clientWeather']
                for cell in weather:
                    alerts = None
                    for alert in cell.get("alerts", {}):
                        alert = alert.get("severity", None)
                    self.weatherConditions.update({cell['s2CellId']:
                        (cell['gameplayWeather']['gameplayCondition'], alerts)})
            except KeyError:
                weather = None

            fort_count = 0
            pokestop_count = 0
            gym_count = 0
            forts = []
            gyms = []
            pokestops = []
            raids = []
            lures = []

            # grab all the forts we got from the GMO request
            # as we don't care about spawns
            for i, cell in enumerate(gmo_response['mapCells']):
                fort = cell.get('forts', None)
                if fort:
                    forts += fort
                    fort_count += len(fort)

            # iterate over our forts and handle them
            for f in forts:
                f_type = f.get('type', 0)
                f_raid = f.get('raidInfo', None)
                f_id = f['id']
                f_lat = f['latitude']
                f_lng = f['longitude']

                #get lv10 s2 cell for weather
                p = s2sphere.LatLng.from_degrees(f_lat, f_lng)
                cell = s2sphere.CellId().from_lat_lng(p).parent(10)
                cellid = ctypes.c_int64(cell.id()).value

                # parse gym info from the map
                if f_type == 0 and (f_raid or not self.gym_db.find_one({'id': f_id})):
                    gym_count += 1
                    gym_details = self.gym_db.find_one({'id': f_id})
                    gym, raid = parseGym(f, gym_details)
                    gym['weather'] = self.weatherConditions.get(str(cellid), None)
                    # log.info(f"Found gym {gym_details['name']}")
                    if raid:
                        gym['raid'] = raid
                        raids.append(gym)
                    gyms.append(gym)
                elif self.gym_db.find_one({'id': f_id}):
                    gym_count += 1
                    # gym_details = self.gym_db.find_one({'id': f_id})
                    # log.info(f"Found gym {gym_details['name']}")

                    self.gym_db.update_one({'id': f_id},
                        {'$set': {'lastSeen': datetime.datetime.utcnow()}
                        }).modified_count
                #parse pokestop details
                elif f_type == 'CHECKPOINT':
                    pokestop_count += 1
                    if not self.pokestop_db.find_one({'id': f_id}):
                        log.info(f"Discovered new pokestop {f_id}")
                        doc = {
                            'id': f_id,
                            'added': datetime.datetime.utcnow(),
                            'name': None,
                            'location': {
                                'type': 'Point',
                                'coordinates': [
                                    f_lng,
                                    f_lat
                                ]
                            }
                        }
                        self.pokestop_db.insert_one(doc).inserted_id
            # pos = device['position']
            log.info(f"Found {fort_count} forts. {gym_count} Gyms {pokestop_count} Pokestops {len(raids)} Raids")
            # push our results to their queues.
            if gyms:
                self.gym_db_queue.put(gyms)
            # self.pokestop_db.put(pokestops)
            if raids:
                self.raid_queue.put(raids)
                self.raid_db_queue.put(raids)

    def getData(self):
        map_objects = request.get_json()
        if map_objects.get('uuid') in self.devices:
            device = self.devices[map_objects.get('uuid')]
            proto_responses = map_objects.get('protos', None)
            device['lastscan'] = datetime.datetime.now().timestamp()
            fort_count = 0
            for proto in proto_responses:
                if proto.get('GetMapObjects', None):
                    #put response into Queue and move on. let thread process it
                    response = b64decode(proto.get('GetMapObjects'))
                    #decde raw protos to JSON
                    gmo = GetMapObjectsResponse()
                    gmo.ParseFromString(response)
                    gmo_response = json.loads(MessageToJson(gmo))
                    for i, cell in enumerate(gmo_response['mapCells']):
                        if cell.get('forts'):
                            fort_count += len(cell.get('forts', {}))

                    if fort_count > 0:
                        self.process_queue.put(proto.get('GetMapObjects', {}))

            #we had 3 empty scans. delete this area.
            if device['emptyScan'] == 3:
                log.warn(f"Nothing was found at {device['locations'][device['position']]} for 3 GMOs. Removing from search list.")
                # device['locations'].pop(device['position'])

            if fort_count > 0 or device['emptyScan'] == 3:
                device['emptyScan'] = 0
                if device['position'] >= len(device['locations']) - 1:
                    device['position'] = 0
                else:
                    device['position'] += 1
            elif fort_count > 0 and gym_count == 0:
                log.warn(f"Found forts, but no Gyms. We don't need to be here. {device['locations'][device['position']]}")
                device['locations'].pop(device['position'])
                device['emptyScan'] == 3
            else:
                device['emptyScan'] += 1
                log.warn(f"No forts found. Got caught speeding? Attempt {device['emptyScan']} of 3")
        else:
            log.warn("Unknown device UUID {}".format(map_objects.get('uuid')))
        return 'Okay', 200

    def getLocation(self):
        req = request.get_json()
        if req.get('uuid') in self.devices:
            device = self.devices[req.get('uuid')]
            try:
                position = device['position']
                d = {}
                d['latitude'] = device['locations'][position]['lat']
                d['longitude'] = device['locations'][position]['lng']

                return jsonify(d)
            except IndexError:
                d = {}
                d['latitude'] = device['locations'][0]['lat']
                d['longitude'] = device['locations'][0]['lng']
                return jsonify(d)
        else:
            log.warn("Unknown device UUID {}".format(req.get('uuid')))
        return "okay", 200

    def status(self):
        status = []
        for dev in self.devices:
            device = {
                'name': self.devices[dev]['identifier'],
                'position': self.devices[dev]['position'],
                'lastscan': self.devices[dev]['lastscan'],
                'lastseen': [
                    self.devices[dev]['locations'][self.devices[dev]['position']]
                ],
                'locations': len(self.devices[dev]['locations'])
            }
            status.append(device)

        return jsonify(status)
