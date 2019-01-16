import time
import json
from pgoapi import PGoApi
from pgoapi.hash_server import HashServer
from pgoapi.exceptions import AuthException

def checkAccounts():
    api = PGoApi()
    api.activate_hash_server('')
    bannedAccounts = []
    goodAccounts = []
    with open('accounts.json', 'r') as accountlist:
        accounts = json.load(accountlist)

    for account in accounts:
        print(f"Checking {account['username']}...")
        try:
            api.set_authentication(provider=account['type'],
                                   username=account['username'],
                                   password=account['password'])
            api.set_position(40.707259, -73.520977, 144.3)
            request = api.create_request()
            request.call(request)
            time.sleep(1)
            request = api.create_request()
            request.get_player(player_locale = {'country': 'US', 'language': 'en', 'timezone': 'America/New_York'})
            request.call(request)
            time.sleep(1)
            request = api.create_request()
            request.download_remote_config_version(platform=1, app_version=7903)
            request.check_challenge()
            request.get_hatched_eggs()
            request.get_inventory(last_timestamp_ms=0)
            request.check_awarded_badges()
            request.download_settings()
            resp = request.call(request)
            # print(resp)
            if not resp['responses'].get('GET_INVENTORY'):
                bannedAccounts.append(account)
                print("\rbanned.")
            else:
                goodAccounts.append(account)
                print("Good")
        except AuthException:
            bannedAccounts.append(account)
        time.sleep(10)

    print(f"found {len(bannedAccounts)} banned accounts and {len(goodAccounts)} unbanned accounts.")
    with open('banned.json', 'w') as bf:
        json.dump(bannedAccounts, bf)
    with open('good.json', 'w') as gf:
        json.dump(goodAccounts, gf)

if __name__ == '__main__':
    checkAccounts()
