from .protos.pogoprotos.enums.team_color_pb2 import _TEAMCOLOR
from .protos.pogoprotos.enums.pokemon_id_pb2 import _POKEMONID
from .protos.pogoprotos.enums.pokemon_move_pb2 import _POKEMONMOVE
from .protos.pogoprotos.enums.raid_level_pb2 import _RAIDLEVEL
from .protos.pogoprotos.enums.form_pb2 import _FORM
from .protos.pogoprotos.enums.weather_condition_pb2 import _WEATHERCONDITION

def parseGym(gymData, gymDBDetails):
    try:
        raid = None
        # gym = gymData['gym_status_and_defenders']
        # gym_status = gym.get('pokemon_fort_proto', {})
        # gym_defenders = gym.get('gym_defender', {})
        # print("Gym: {}".format(gymData['name']))
        gym_raid = gymData.get('raidInfo', {})
        if gymDBDetails is not None:
            g_name = gymDBDetails.get('name', 'Unknown Gym Name')
        else:
            g_name = "Unknown Gym Name"

        g_id = gymData['id']
        g_lat = gymData['latitude']
        g_lon = gymData['longitude']
        g_team = _TEAMCOLOR.values_by_name[gymData.get('ownedByTeam', 'NEUTRAL')].number
        g_sponsor = gymData.get('sponsor', None)
        g_exraid = gymData.get('isExRaidEligible', False)
        # g_defenders = []
        # for defender in gym_defenders:
        #     gd_pkmn = defender['motivated_pokemon']
        #     gd_pkmn_stats = gd_pkmn['pokemon']
        #
        #     d_trainer = gd_pkmn_stats['owner_name']
        #     d_pkmn_cp = gd_pkmn['cp_when_deployed']
        #     d_pkmn_id = gd_pkmn_stats['pokemon_id']
        #     d_pkmn_move_fast = gd_pkmn_stats['move_1']
        #     d_pkmn_move_chrg = gd_pkmn_stats['move_2']
        #     d_pkmn_ball = gd_pkmn_stats.get('pokeball', 0)
        #     defender = {'trainer': d_trainer, 'pokemon_id': d_pkmn_id, 'pokemon_cp': d_pkmn_cp, 'pokemon_move_fast': d_pkmn_move_fast, 'pokemon_move_charge': d_pkmn_move_chrg, 'pokemon_caught': d_pkmn_ball}
        #     g_defenders.append(defender)
            # print("{} has a {} CP {} ({})".format(d_trainer, d_pkmn_cp, d_pkmn_id, d_pkmn_id))
        # print("gym {} at {},{} owned by {} last modified at {}".format(g_name, g_lat, g_lon, g_team, g_modified))
        gym = {
            'id': g_id,
            'name': g_name,
            'lat': g_lat,
            'lng': g_lon,
            'sponsor': g_sponsor,
            'isExRaidEligible': g_exraid,
            'team': g_team,
        }

        if gym_raid:
            r_spawn = float(gym_raid['raidSpawnMs']) / 1000.0
            r_battle = float(gym_raid['raidBattleMs']) / 1000.0
            r_end = float(gym_raid['raidEndMs']) / 1000.0
            r_id = gym_raid['raidSeed']
            r_level = _RAIDLEVEL.values_by_name[gym_raid['raidLevel']].number
            r_exclusive = gym_raid.get('isExclusive', False)
            r_boss = gym_raid.get('raidPokemon', None)  # optional

            # print("Found raid: {} level {} spawning at {} ({}) battle begins {} battle ends {}".format(r_id, r_level, r_spawn, g_team, r_battle, r_end))
            raid = {
                'id': r_id,
                'level': r_level,
                'time_spawn': r_spawn,
                'time_battle': r_battle,
                'time_end': r_end,
                'exclusive': r_exclusive,
            }

            if r_boss:
                rb_pkmn_id = _POKEMONID.values_by_name[r_boss['pokemonId']].number
                rb_pkmn_cp = r_boss['cp']
                rb_pkmn_move_fast = _POKEMONMOVE.values_by_name[r_boss['move1']].number
                rb_pkmn_move_chrg = _POKEMONMOVE.values_by_name[r_boss['move2']].number
                rb_pkmn_form = _FORM.values_by_name[r_boss['pokemonDisplay'].get('form', 'FORM_UNSET')].number
                if rb_pkmn_form == 0:
                    rb_pkmn_form = None

                # print("Raid boss: {} ({}) fast {} charge {} cp: {}".format(rb_pkmn_id, rb_pkmn_id, rb_pkmn_cp, rb_pkmn_move_fast, rb_pkmn_move_chrg))
                raid_boss = {
                    'pokemon_id': rb_pkmn_id,
                    'pokemon_form': rb_pkmn_form,
                    'pokemon_cp': rb_pkmn_cp,
                    'pokemon_move_fast': rb_pkmn_move_fast,
                    'pokemon_move_charge': rb_pkmn_move_chrg
                }
                raid['boss'] = raid_boss  # append the boss dictionary to raid.
    except KeyError as e:
        log.exception(f"Caught Exception: {e}")
        log.exception("Data: {}".format(gymData))
        return None, None
        pass
    return gym, raid


def parsePokestop(pokestopData):
        # print("pokestop: {}".format(pokestopData))
        ps_id = pokestopData['fort_id']
        ps_name = pokestopData['name']
        ps_desc = pokestopData.get('description', '')
        ps_lat = pokestopData['latitude']
        ps_lon = pokestopData['longitude']
        ps_modifier = pokestopData.get('modifiers', None)
        ps_modifier_type = None
        ps_modifier_expire = None
        if ps_modifier:
            ps_modifier_type = ps_modifier[0]['item_id']
            ps_modifier_expire = ps_modifier[0]['expiration_timestamp_ms'] / 1000.0
        # print("Pokestop found: id {}: {} {} at {},{}".format(ps_id, ps_name, ps_desc, ps_lat, ps_lon))
        pokestop = {'pokestop_id': ps_id, 'pokestop_name': ps_name, 'pokestop_desc': ps_desc, 'latitude': ps_lat, 'longitude': ps_lon, 'modifier': ps_modifier_type, 'modifier_expire': ps_modifier_expire}
        return pokestop
