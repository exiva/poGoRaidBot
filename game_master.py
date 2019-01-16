import json
import difflib
import time
import requests
from pprint import pprint
from pgoapi import PGoApi
from pgoapi.hash_server import HashServer
from pgoapi.exceptions import AuthException, PgoapiError, \
    BannedAccountException, HashingQuotaExceededException, HashingOfflineException, HashingTimeoutException
from itertools import zip_longest

def chunkstring(string, length):
    return (string[0+i:length+i] for i in range(0, len(string), length))

def check():
    with open('game_master.json', 'r') as f:
        gm = json.load(f)

    api = PGoApi()
    api.activate_hash_server('8F6A0C8L1O4D6T6O1N0S')
    try:
        api.set_authentication(provider='ptc', username='TonedS1xS4w', password='TDsW?AyM2')
        api.set_position(40.707259, -73.520977, 9144.2)
        print("Logged in.")
    except AuthException:
        print("Login failed. Wrong user/pass?")

    #create empty request
    request = api.create_request()
    request.call(request)
    time.sleep(1)

    #set locale
    request = api.create_request()
    request.get_player(player_locale = {'country': 'US', 'language': 'en', 'timezone': 'America/New_York'})
    request.call(request)
    time.sleep(1)

    #download game_master
    request = api.create_request()
    request.download_item_templates()
    req = request.call(request)

    new_timestamp = req['responses']['DOWNLOAD_ITEM_TEMPLATES']['timestamp_ms']

    if int(gm['timestamp_ms']) != int(new_timestamp):
        print("Game master updated! Old timestamp {} new {}".format(gm['timestamp_ms'], new_timestamp))
        # new_game_master = json.dumps(req['responses']['DOWNLOAD_ITEM_TEMPLATES'], indent=2)
        # game_master = json.dumps(gm, indent=2)
        # diff = difflib.unified_diff(game_master.splitlines(keepends=True), new_game_master.splitlines(keepends=True))
        # diffs = ''.join(diff)
        # diffList = list(chunkstring(diffs, 1800))
        # delay = 4 if len(diffList) > 10 else 2
        # for diff in diffList:
        #     payload = {
        #         "content": f'```diff\n{diff}```'
        #         }
        #     resp = requests.post("https://discordapp.com/api/webhooks/370625263471558658/4P3ntMy1PxbCc4QGcsIjONqK701Z2rnwyIvvXTcsffVZ8j2oFehuFoIjUBC1uhgn2fS9", json=payload)
        #     print(resp.status_code)
        #
        #     time.sleep(delay)
        with open('game_master_update.json', 'w') as f:
            json.dump(req['responses']['DOWNLOAD_ITEM_TEMPLATES'], f, indent=2)

if __name__ == '__main__':
    while True:
        check()
        time.sleep(600)
