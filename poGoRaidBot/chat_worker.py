import queue
import pendulum
import time
import requests
import geocoder

import telegram
from telegram import ParseMode
from .pkmn import pkmn_names
from .forms import pkmn_form
from json import JSONDecodeError
from requests import RequestException


def make_googl(key, url):
    apiUrl = 'https://www.googleapis.com/urlshortener/v1/url?key={}'.format(key)
    data = {'longUrl': url}
    r = requests.post(apiUrl, json=data)
    success = False
    while not success:
        try:
            googl = r.json().get('id', "")
            success = True
            return googl
        except JSONDecodeError as e:
            time.sleep(5)
            continue

def getCity(lat, lng, key):
    city = geocoder.google([lat, lng], method='reverse', key=key).city
    if not city:
        return ''
    else:
        return f'({city})'


def raid_chat_worker(args, config, db, regions, raids):
    if config['telegram']['enabled']:
        bot = telegram.Bot(config['telegram']['api_key'])

    if config['discord']['enabled']:
        raid_hook = config['discord']['raid_webhook']
        egg_hook = config['discord']['egg_webhook']
        exclusive_hook = config['discord']['exclusive_webhook']
        sponsor_hook = config['discord']['sponsor_webhook']

    pkmn_name = pkmn_names

    teams = {
        0: ('Gym Unclaimed', 'http://exiva.net/gym_unclaimed.png'),
        1: ('Controlled by Mystic', 'http://exiva.net/gym_mystic.png'),
        2: ('Controlled by Valor', 'http://exiva.net/gym_valor.png'),
        3: ('Controlled by Instinct', 'http://exiva.net/gym_instinct.png')
    }

    r_tiers = {
        1: (0xF994A6, 'http://exiva.net/pinkegg.png'),
        2: (0xF994A6, 'http://exiva.net/pinkegg.png'),
        3: (0xFCE407, 'http://exiva.net/goldegg.png'),
        4: (0xFCE407, 'http://exiva.net/goldegg.png'),
        5: (0x867DBF, 'http://exiva.net/legendegg.png'),
    }

    egg_sent = []
    raid_sent = []
    started_raids = []
    gym_cities = {}  # todo: fix this hack.
    while True:
        try:
            r_gyms = raids.get()
            # print("Incoming gyms with raids: {}".format(r_gyms))
            for r_gym in r_gyms:
                # print("Gym: {}".format(r_gym))
                raid = r_gym.get('raid')
                r_boss = raid.get('boss', None)

                db_raid = db.find_one({'raid_id': raid['id']})
                db_raid_id = None
                db_raid_boss = None
                if db_raid:
                    db_raid_id = db_raid.get('raid_id', None)
                    db_raid_boss = db_raid.get('pokemon_id', None)

                if (r_boss and raid['id'] not in started_raids) or (raid['id'] not in raid_sent):
                        # print(raid)
                        g_team, g_team_icon = teams.get(r_gym['team'])
                        g_mapUrl = f"http://maps.google.com/maps?q={r_gym['lat']},{r_gym['lng']}"
                        g_mapImg = f"https://maps.googleapis.com/maps/api/staticmap?center={r_gym['lat']},{r_gym['lng']}&zoom=15&size=400x200&key={config['discord']['gmaps']}&markers=anchor:31,39%7Cicon:{g_team_icon}%7C{r_gym['lat']},{r_gym['lng']}"
                        g_navGoogle = make_googl(config['googl_key'], f"https://google.com/maps/dir/?api=1&destination={r_gym['lat']},{r_gym['lng']}")
                        g_navApple = make_googl(config['googl_key'], f"http://maps.apple.com/maps?saddr=Current%20Location&daddr={r_gym['lat']},{r_gym['lng']}")
                        g_navWaze = make_googl(config['googl_key'], f"http://exiva.net/waze-redirect.html?ll={r_gym['lat']},{r_gym['lng']}")
                        r_gym['name'] = " ".join(r_gym['name'].split())
                        region = regions.find_one({'geometry':{
                            "$geoIntersects": {
                                "$geometry": { 'type': "Point", "coordinates": [ r_gym['lng'], r_gym['lat']]}
                            }}})
                        # print(region['region_name'])
                        # db.regions.find({ geometry: { $geoIntersects: { $geometry: { type: "Point", coordinates: [ -73.578019,40.733076  ] } } } })
                        if not gym_cities.get(r_gym['id']):  # create a cache todo: move to database
                            r_city = getCity(r_gym['lat'], r_gym['lng'], key=config['geocoder'])
                            gym_cities[r_gym['id']] = r_city  # store the city in local cache
                        else:
                            r_city = gym_cities.get(r_gym['id'])  # retrieve city from cache

                        r_spawn = pendulum.from_timestamp(raid['time_spawn'], tz='US/Eastern').strftime("%I:%M %p")
                        r_start = pendulum.from_timestamp(raid['time_battle'], tz='US/Eastern').strftime("%I:%M %p")
                        r_end = pendulum.from_timestamp(raid['time_end'], tz='US/Eastern').strftime("%I:%M %p")
                        r_color, r_egg = r_tiers.get(raid['level'])
                        r_exclusive = 'Exclusive ' if raid['exclusive'] else ''
                        ex_raid = "\n\n**Gym is EX Raid Eligible**" if r_gym['isExRaidEligible'] else ''

                        if not r_boss:  # Boss hasn't spawned yet.
                            # message = '{}: Level {} raid at {} (Gym controlled by {}) hatching at {}'.format(r_city, raid['level'], gym['name'], g_team, r_start)
                            title = f"{r_city} {r_gym['name']}: {r_exclusive}level {raid['level']} egg hatching soon"
                            message = f"{r_exclusive}Level {raid['level']} raid egg at {r_gym['name']} {r_city}. ({g_team}) Hatches at {r_start}.{ex_raid}"
                            img = r_egg
                        else:
                            # message = '{}: Level {} {} {} CP raid at {} (gym controlled by {}) started! Ending at {}'.format(r_city, raid['level'], pkmn_name[r_boss_pkmn], r_boss['pokemon_cp'], gym['name'], g_team, r_end)
                            r_boss_pkmn = r_boss.get('pokemon_id', None)
                            r_boss_pkmn_form = r_boss.get('pokemon_form', None)
                            r_boss_gamepress = make_googl(config['googl_key'], f"https://pokemongo.gamepress.gg/pokemon/{r_boss_pkmn}#raid-boss-counters")

                            form_name = pkmn_form[r_boss_pkmn_form].name+' ' if pkmn_form[r_boss_pkmn_form] else ''

                            if pkmn_form[r_boss_pkmn_form].name == "Alolan":
                                img = "http://assets.pokemon.com/assets/cms2/img/pokedex/full/{:03}_f2.png".format(r_boss_pkmn)
                            else:
                                img = "http://assets.pokemon.com/assets/cms2/img/pokedex/full/{:03}.png".format(r_boss_pkmn)

                            title = f"{r_city} {r_gym['name']}: {r_exclusive}level {raid['level']} {form_name}{pkmn_name[r_boss_pkmn].name} raid started"
                            message = f"{r_exclusive}Level {raid['level']} {form_name}{pkmn_name[r_boss_pkmn].name} raid started at {r_gym['name']} {r_city}. Starts at {r_start}, Ends at {r_end}.\n\nSuggested counters: <{r_boss_gamepress}>{ex_raid}"
                            started_raids.append(raid['id'])

                        if config['telegram']['enabled']:
                            update = bot.sendMessage(chat_id=config['telegram']['channel_id'], parse_mode=ParseMode.MARKDOWN, text=f"{title}\n\n{message}")
                            bot.sendLocation(chat_id=config['telegram']['channel_id'], latitude=r_gym['lat'], longitude=r_gym['lng'], reply_to_message_id=update.message_id, disable_notification=True)

                        if config['discord']['enabled']:
                            payload = {
                                "username": config['discord']['username'],
                                "avatar_url": config['discord']['avatar'],
                                "embeds": [{
                                    "title": title,
                                    "description": f'{message}\n\nNavigate with [Google Maps]({g_navGoogle}) | [Apple Maps]({g_navApple}) | [Waze]({g_navWaze})',
                                    "url": g_mapUrl,
                                    "color": r_color,
                                    "thumbnail": {
                                        "url": img,
                                        "height": 170, "width": 170
                                    },
                                    "image": {
                                        "url": g_mapImg
                                    },
                                    "footer": {
                                        "text": region['region_name']
                                    }
                                }],
                                "content": f'{message}\n\nNavigate with Google Maps <{g_navGoogle}> | Apple Maps <{g_navApple}> | Waze <{g_navWaze}>',
                            }
                            success = False
                            while not success:
                                try:
                                    if raid['exclusive']:
                                        resp = requests.post("https://discordapp.com/api/webhooks/{}".format(exclusive_hook), json=payload)

                                    if r_gym['sponsor']:
                                        resp = requests.post("https://discordapp.com/api/webhooks/{}".format(sponsor_hook), json=payload)

                                    if not r_boss:
                                        resp = requests.post("https://discordapp.com/api/webhooks/{}".format(egg_hook), json=payload)
                                    else:
                                        resp = requests.post("https://discordapp.com/api/webhooks/{}".format(raid_hook), json=payload)
                                    if resp.status_code == 204:
                                        raid_sent.append(raid['id'])
                                        success = True
                                        time.sleep(1)
                                    else:
                                        print(f"raid webhook failed: {resp.status_code}.")
                                        print(f"payload: {payload}")
                                        time.sleep(4)
                                except RequestException as e:
                                    time.sleep(3)
                                    continue
                # print("Raids sent: {}".format(raid_sent))
        except queue.Empty as e:
            continue
        time.sleep(1)


def lure_chat_worker(args, config, lures):
    # if config['telegram']['enabled']:
        # bot = telegram.Bot(config['telegram']['api_key'])

    if config['discord']['enabled']:
        lure_hook = config['discord']['lure_webhook']

    posted_lures = []
    while True:
        try:
            l_forts = lures.get()
            for lure in l_forts:
                if lure['modifier_expire']:
                    l_end = pendulum.from_timestamp(lure['modifier_expire'], tz='US/Eastern').strftime("%I:%M %p")
                else:
                    l_end = "MissingNo."
                l_type = "Lure module" if lure['modifier'] == 501 else "Missingno. module"

                if lure['modifier_expire'] not in posted_lures:
                    if (config['discord']['enabled']) and (config['discord']['lure_webhook']):
                        l_city = getCity(lure['latitude'], lure['longitude'], key=config['geocoder'])
                        payload = {
                            "username": config['discord']['username'],
                            "avatar_url": config['discord']['avatar'],
                            "embeds": [
                                {
                                    "title": f"{l_city} {l_type} installed at {lure['pokestop_name']}",
                                    "url": f"http://maps.google.com/maps?q={lure['latitude']},{lure['longitude']}",
                                    "thumbnail": {
                                        "url": "http://exiva.net/lure.png",
                                        "height": 170,
                                        "width": 170
                                    },
                                    "image": {
                                        "url": f"https://maps.googleapis.com/maps/api/staticmap?center={lure['latitude']},{lure['longitude']}&zoom=15&size=400x200&key={config['discord']['gmaps']}&markers=anchor:23,45%7Cicon:http://exiva.net/lured_pokestop.png%7C{lure['latitude']},{lure['longitude']}"
                                    },
                                    "color": 0xF915C7,
                                    "description": f"{l_type} installed at {lure['pokestop_name']}! {l_city} Expires at {l_end}"
                                }
                            ]
                        }
                        success = False
                        while not success:
                            try:
                                resp = requests.post("https://discordapp.com/api/webhooks/{}".format(lure_hook), json=payload)
                                if resp.status_code == 204:
                                    posted_lures.append(lure['modifier_expire'])
                                    success = True
                                    time.sleep(1)
                                else:
                                    print(f"lure webhook failed: {resp.status_code}.")
                                    time.sleep(4)
                            except RequestException as e:
                                time.sleep(3)
                                continue
        except queue.Empty as e:
            continue
        time.sleep(1)
