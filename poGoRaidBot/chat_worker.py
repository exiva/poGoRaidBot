import logging
import queue
import pendulum
import time
import requests
import geocoder
import urllib

import telegram
from telegram import ParseMode
from .pkmn import pkmn_names
from .forms import pkmn_form
from .conditions import weather_conditions
from json import JSONDecodeError
from requests import RequestException

from .protos.pogoprotos.enums.weather_condition_pb2 import _WEATHERCONDITION

log = logging.getLogger(__name__)


def make_googl(key, url):
    apiUrl = f"https://www.googleapis.com/urlshortener/v1/url?key={key}"
    data = {'longUrl': url}
    r = requests.post(apiUrl, json=data)
    success = False
    while not success:
        try:
            googl = r.json().get('id', "")
            success = True
            return googl
        except JSONDecodeError as e:
            log.error(f"googl shortner exception {e}")
            time.sleep(5)
            continue


def getCity(lat, lng, key):
    city = geocoder.mapbox([lat, lng], method='reverse', key=key).city
    if not city:
        return ''
    else:
        return f'({city})'


def raid_chat_worker(args, config, db, regions, raids):
    log.info("Starting chat worker")
    if config['telegram']['enabled']:
        log.info("Telegram enabled")
        bot = telegram.Bot(config['telegram']['api_key'])

    if config['discord']['enabled']:
        log.info("Discord webhooks enabled")
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
        1: (0xF994A6, 'http://exiva.net/pink.png'),
        2: (0xF994A6, 'http://exiva.net/pink.png'),
        3: (0xFCE407, 'http://exiva.net/gold.png'),
        4: (0xFCE407, 'http://exiva.net/gold.png'),
        5: (0x867DBF, 'http://exiva.net/legend.png'),
    }

    genders = {
        0: ('', ''),
        1: ('(Male)', '\u2642'),
        2: ('(Female)', '\u2640'),
        3: ('', '')
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
                # print("Gym details: {}".format(r_gym))
                raid = r_gym.get('raid')
                r_boss = raid.get('boss', None)
                weather = r_gym.get('weather')

                db_raid = db.find_one({'raid_id': raid['id']})
                db_raid_id = None
                db_raid_boss = None
                if db_raid:
                    db_raid_id = db_raid.get('raid_id', None)
                    db_raid_boss = db_raid.get('pokemon_id', None)

                if (r_boss and raid['id'] not in started_raids) or (raid['id'] not in raid_sent):
                    log.debug(f"Processing raid {raid['id']}")
                    # print(raid)
                    g_team, g_team_icon = teams.get(r_gym['team'])
                    g_mapUrl = f"http://maps.google.com/maps?q={r_gym['lat']},{r_gym['lng']}"
                    #g_mapImg = f"https://api.mapbox.com/styles/v1/mapbox/streets-v10/static/url-{urllib.parse.quote_plus(g_team_icon)}({r_gym['lng']},{r_gym['lat']})/{r_gym['lng']},{r_gym['lat']},16/500x300?access_token={config['discord']['gmaps']}"
                    g_navGoogle = make_googl(config['googl_key'], f"https://google.com/maps/dir/?api=1&destination={r_gym['lat']},{r_gym['lng']}")
                    g_navApple = make_googl(config['googl_key'], f"http://maps.apple.com/maps?saddr=Current%20Location&daddr={r_gym['lat']},{r_gym['lng']}")
                    g_navWaze = make_googl(config['googl_key'], f"http://exiva.net/waze-redirect.html?ll={r_gym['lat']},{r_gym['lng']}")
                    r_gym['name'] = " ".join(r_gym['name'].split())
                    region = regions.find_one({'geometry': {
                        "$geoIntersects": {
                            "$geometry": {'type': "Point", "coordinates": [r_gym['lng'], r_gym['lat']]}
                        }}})

                    if region:
                        r_region = region['region_name']
                    else:
                        r_region = f"{r_gym['lat']},{r_gym['lng']}"

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
                        r_boss_types = pkmn_name[r_boss_pkmn].types
                        r_boss_gender = genders.get(r_boss.get('pokemon_gender'))
                        form_name = pkmn_form[r_boss_pkmn_form].name+' ' if pkmn_form[r_boss_pkmn_form] else ''

                        if pkmn_form[r_boss_pkmn_form] and pkmn_form[r_boss_pkmn_form].name == "Alolan":
                            img = "http://assets.pokemon.com/assets/cms2/img/pokedex/full/{:03}_f2.png".format(r_boss_pkmn)
                        else:
                            img = "http://assets.pokemon.com/assets/cms2/img/pokedex/full/{:03}.png".format(r_boss_pkmn)
                        r_boss_boost = ''

                        if weather:
                            w = _WEATHERCONDITION.values_by_name[weather[0]].number
                            conditions = weather_conditions[w]
                            for type in r_boss_types:
                                if type in conditions[1]:
                                    r_boss_boost = f"\n\n*{conditions[0]} Weather Boost Active*"

                        title = f"{r_city} {r_gym['name']}: {r_exclusive}level {raid['level']} {form_name}{pkmn_name[r_boss_pkmn].name} {r_boss_gender[1]} raid started"
                        message = f"{r_exclusive}Level {raid['level']} {form_name}{pkmn_name[r_boss_pkmn].name} {r_boss_gender[0]} raid started at {r_gym['name']} {r_city}. Starts at {r_start}, Ends at {r_end}.{r_boss_boost}{ex_raid}"
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
                                # "image": {
                                #     "url": g_mapImg
                                # },
                                "footer": {
                                    "text": r_region
                                }
                            }],
                            "content": f'{message}\n\nNavigate with Google Maps <{g_navGoogle}> | Apple Maps <{g_navApple}> | Waze <{g_navWaze}>',
                        }
                        success = False
                        log.debug(f"webhook: {payload}")
                        while not success:
                            try:
                                # if raid['exclusive']:
                                #     resp = requests.post("https://discordapp.com/api/webhooks/{}".format(exclusive_hook), json=payload)
                                #
                                # if r_gym['sponsor']:
                                #     resp = requests.post("https://discordapp.com/api/webhooks/{}".format(sponsor_hook), json=payload)
                                #
                                if not r_boss:
                                    resp = requests.post("https://discordapp.com/api/webhooks/{}".format(egg_hook), json=payload)
                                else:
                                    resp = requests.post("https://discordapp.com/api/webhooks/{}".format(raid_hook), json=payload)
                                if resp.status_code == 204:
                                    log.debug(f"Posted webhook {resp.text}")
                                    raid_sent.append(raid['id'])
                                    success = True
                                else:
                                    log.error(f"raid webhook failed: {resp.status_code}.")
                                    time.sleep(5)
                            except RequestException as e:
                                log.error(f"raid webhook failed to send {e}")
                                time.sleep(1)
                                continue
                # print("Raids sent: {}".format(raid_sent))
        except queue.Empty:
            continue

def lure_chat_worker(args, config, lures):
    # if config['telegram']['enabled']:
    #     bot = telegram.Bot(config['telegram']['api_key'])

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
                            except RequestException:
                                time.sleep(3)
                                continue
        except queue.Empty:
            continue
        time.sleep(1)
