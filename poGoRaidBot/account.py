import random
import time
import hashlib
from pgoapi import PGoApi
from pgoapi.exceptions import AuthException, NotLoggedInException, PgoapiError, \
    NoPlayerPositionSetException, NoHashKeyException, BannedAccountException, \
    NianticOfflineException, NianticThrottlingException, \
    HashingQuotaExceededException, HashingOfflineException, HashingTimeoutException


class CaptchaException(Exception):
    """Any custom exception in this module"""


class accountManager(object):
    def __init__(self, username, password, hashkey, service, version, proxy=None):
        self.username = username
        self.password = password
        self.service = service
        self.hashkey = hashkey
        self.proxy = proxy
        self.version = version

        self.captcha = None
        self.isBanned = False

        self._api = PGoApi(device_info=self._generate_device_info())
        self._lastTimestamp = 0
        self._settingsHash = None
        self._playerLevel = 1
        self._mapRefresh = None

    def isLoggedin(self):
        # check if we've logged in by checking if set provider & has a ticket
        if self._api.get_auth_provider() and self._api.get_auth_provider().has_ticket():
            return True

        if self.proxy:
            self._api.set_proxy({'http': self.proxy, 'https': self.proxy})

        self._api.activate_hash_server(self.hashkey)

        # not logged in, so lets do it.
        try:
            if self.proxy:
                self._api.set_authentication(provider=self.service, username=self.username, password=self.password, proxy_config={'http': self.proxy, 'https': self.proxy})
            else:
                self._api.set_authentication(provider=self.service, username=self.username, password=self.password)
        except AuthException:
            print("Login failed. Wrong user/pass?")
            return False
        except PgoapiError:
            print("API Errored out. Trying again.")
            time.sleep(5)
            self.isLoggedin()
        except NoPlayerPositionSetException:
            print("Set a location first.")
            return False
        except NoHashKeyException:
            print("Set a hash key.")
            return False

        self._fullLogin()
        return True

    def setPosition(self, lat, lng, alt):
        self._api.set_position(lat, lng, alt)

    def get_gym_info(self, g_id, p_lat, p_lng, g_lat, g_lng):
        return self._api.request(lambda req: req.get_gym_info(
            gym_id=g_id,
            player_lat_degrees=p_lat,
            player_lng_degrees=p_lng,
            gym_lat_degrees=g_lat,
            gym_lng_degrees=g_lng
        ))

    def spin_pokestop(self, f_id, p_lat, p_lng, f_lat, f_lng):
        self.request(lambda req: req.fort_search(
            fort_id=f_id,
            fort_latitude=f_lat,
            fort_longitude=f_lng,
            player_latitude=p_lat,
            player_longitude=p_lng
        ), walked=True, inbox=True)

    def dump_items(self, itemid, drop):
        self.request(lambda req: req.recycle_inventory_items(
            item_id=itemid, count=drop), walked=True, inbox=True)

    def request(self, reqType, walked=False, inbox=False):
        request = self._api.create_request()

        # Insert our request.
        reqType(request)

        # default requests
        request.check_challenge()  # no longer used
        request.get_hatched_eggs()
        request.get_holo_inventory(last_timestamp_ms=self._lastTimestamp)
        request.check_awarded_badges()

        if self._settingsHash:
            request.download_settings(hash=self._settingsHash)
        else:
            request.download_settings()

        if walked:
            request.get_buddy_walked()

        if inbox:
            request.get_inbox(is_history=True)

        return self._sendRequest(request)

    def solveCaptcha(self, challenge_token):
        request = self._api.create_request()
        request.verify_challenge(token=challenge_token)
        response = self._sendRequest(request)

        if 'VERIFY_CHALLENGE' in response:
            if response['VERIFY_CHALLENGE']['success']:
                return True
            else:
                return False
        else:
            return False

    def _fullLogin(self):
        # from https://raw.githubusercontent.com/sLoPPydrive/MrMime/master/research/login_flow.txt
        # empty request
        request = self._api.create_request()
        self._sendRequest(request)

        # get player
        request = self._api.create_request()
        request.get_player(player_locale={'country': 'US', 'language': 'en', 'timezone': 'America/New_York'})
        self._sendRequest(request)

        # download_remote_config_version
        self.request(lambda req: req.download_remote_config_version(platform=1, app_version=self.version))

        # get_player_profile
        self.request(lambda req: req.get_player_profile(), walked=True)

        # level_up_rewards
        self.request(lambda req: req.level_up_rewards(), walked=True)

    def _sendRequest(self, request):
        # Make API request. retry if hashing service is fucked.
        success = False
        while not success:
            try:
                time.sleep(random.uniform(0.4, 0.9))
                response = request.call()
                success = True
            except (HashingOfflineException, HashingTimeoutException, NianticOfflineException):
                print("Hash service down. Sleeping for a bit and trying again.")
                time.sleep(5)
            except HashingQuotaExceededException:
                print("Exceeded hash per minute quota. Trying again.")
                time.sleep(random.uniform(40, 50))
            except NianticThrottlingException:
                print("We went over 88mph.")
                time.sleep(3)
            except KeyError:
                print("Encounterd a KeyError. Retrying.")
                time.sleep(3)

        return self._parseResponse(response['responses'])

    def _parseResponse(self, response):

        # claen up the shit we don't care about.
        if 'LEVEL_UP_REWARDS' in response:
            del response['LEVEL_UP_REWARDS']
        if 'GET_HATCHED_EGGS' in response:
            del response['GET_HATCHED_EGGS']
        if 'CHECK_AWARDED_BADGES' in response:
            del response['CHECK_AWARDED_BADGES']
        if 'GET_BUDDY_WALKED' in response:
            del response['GET_BUDDY_WALKED']

        # Grab info we care about before deleting it.
        if 'CHECK_CHALLENGE' in response:
            challenge_url = response['CHECK_CHALLENGE'].get('challenge_url')
            if int(len(challenge_url)) > 1:
                print(challenge_url)
                self.captcha = challenge_url
                raise CaptchaException
            else:
                self.captcha = None
            del response['CHECK_CHALLENGE']

        if 'GET_HOLO_INVENTORY' in response:
            inventory = response['GET_HOLO_INVENTORY'].get('inventory_delta')

            self._lastTimestamp = inventory.get('new_timestamp_ms')

            for item in inventory.get('inventory_items', {}):
                if 'player_stats' in item['inventory_item_data']:
                    stats = item.get('inventory_item_data', {}).get('player_stats')
                    self._playerLevel = stats.get('level')

            del response['GET_HOLO_INVENTORY']

        if 'DOWNLOAD_SETTINGS' in response:
            self._settingsHash = response['DOWNLOAD_SETTINGS'].get('hash')
            if response['DOWNLOAD_SETTINGS'].get('settings'):
                settings = response['DOWNLOAD_SETTINGS'].get('settings')
                self._mapRefresh = settings['map_settings'].get('get_map_objects_min_refresh_seconds')
            del response['DOWNLOAD_SETTINGS']

        return response
        # print(response)

    # Borrowed from MrMime/mrmime/pogoaccount.py
    def _generate_device_info(self):
        identifier = self.username + self.password
        md5 = hashlib.md5()
        md5.update(identifier.encode('utf-8'))
        pick_hash = int(md5.hexdigest(), 16)

        iphones = {
            'iPhone6,1': 'N51AP',
            'iPhone6,2': 'N53AP',
            'iPhone7,1': 'N56AP',
            'iPhone7,2': 'N61AP',
            'iPhone8,1': 'N71AP',
            'iPhone8,2': 'N66AP',
            'iPhone8,4': 'N69AP',
            'iPhone9,1': 'D10AP',
            'iPhone9,2': 'D11AP',
            'iPhone9,3': 'D101AP',
            'iPhone9,4': 'D111AP'
        }

        ios9 = ('9.0', '9.0.1', '9.0.2', '9.1', '9.2', '9.2.1',
                '9.3', '9.3.1', '9.3.2', '9.3.3', '9.3.4', '9.3.5')
        ios10 = ('10.0', '10.0.1', '10.0.2', '10.0.3', '10.1', '10.1.1',
                 '10.2', '10.2.1', '10.3', '10.3.1', '10.3.2', '10.3.3')
        ios11 = ('11.0', '11.0.1', '11.0.2', '11.0.3', '11.1', '11.1.1',
                 '11.1.2', '11.2')

        device_info = {
            'device_brand': 'Apple',
            'device_model': 'iPhone',
            'hardware_manufacturer': 'Apple',
            'firmware_brand': 'iPhone OS'
        }

        devices = tuple(iphones.keys())
        device = devices[pick_hash % len(devices)]
        device_info['device_model_boot'] = device
        device_info['hardware_model'] = iphones[device]
        device_info['device_id'] = md5.hexdigest()

        if device.startswith('iPhone9'):
            ios_pool = ios10 + ios11
        else:
            ios_pool = ios9 + ios10 + ios11
        device_info['firmware_type'] = ios_pool[pick_hash % len(ios_pool)]

        print("{} Using an {} on iOS {} with device ID {}".format(self.username, device,
              device_info['firmware_type'], device_info['device_id']))

        return device_info
