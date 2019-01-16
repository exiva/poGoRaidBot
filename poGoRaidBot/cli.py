# -*- coding: utf-8 -*-

"""Console script for poGoRaidBot."""

import click
import json
import csv
from collections import namedtuple
from poGoRaidBot import overwatch as overwatch
from poGoRaidBot import utils
from threading import Thread

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--config', '-c', type=click.File('r'), help='Location of Config file')
@click.option('--accounts', '-a', type=click.File('r'), help='Account CSV list')
@click.option('--proxy', '-p', help='Socks Proxy URL', default=False)
@click.option('--dump_coords', '-d', help='Dump results to CSV file', type=click.File('w'))
@click.pass_context
def cli(ctx, config, accounts, proxy, dump_coords):
    ctx.obj = {}
    ctx.obj['proxy'] = proxy
    ctx.obj['dump_coords'] = dump_coords
    if config:
        ctx.obj['config'] = json.load(config)
    if accounts:
        ctx.obj['config']['accounts'] = [] #override or create accounts list
        fields = ['username', 'password', 'type']
        dialect = csv.Sniffer().sniff(accounts.read(1024))
        reader = csv.DictReader(accounts, fieldnames=fields, dialect=dialect)
        accounts.seek(0)
        for row in reader:
            if row['type'] is None: # default to ptc account type
                row['type'] = 'ptc'
            ctx.obj['config']['accounts'].append(dict(row)) # append accounts to config
    pass

@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option('--latitude', '-lat', help='Starting latitude', type=click.FLOAT)
@click.option('--longitude', '-lng', help='Starting longitude', type=click.FLOAT)
@click.option('--step_size', '-st', help='Step Size', default=0.0082, type=click.FLOAT)
@click.option('--step_limit', '-sl', help='Step Limit', default=10, type=click.INT)
@click.pass_context
def spiral(ctx, latitude, longitude, step_size, step_limit):
    args = namedtuple('args', 'proxy latitude longitude step_size step_limit north south cellsize')
    cmdargs = args(ctx.obj['proxy'], latitude, longitude, step_size, step_limit, None, None, None)
    print(cmdargs)
    if not ctx.obj['dump_coords']:
        overwatch_thread = Thread(target=overwatch.overwatch, name='Overwatch', args=(cmdargs, ctx.obj['config']))
        overwatch_thread.start()
    else:
        writer = csv.DictWriter(ctx.obj['dump_coords'], fieldnames=['lat', 'lng'])
        writer.writeheader()
        for coords in utils.generate_spiral(latitude, longitude, step_size, step_limit):
            writer.writerow(coords)
    pass

@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option('--north', '-nc', help='Starting corner of search square (lat lng)', type=(float, float))
@click.option('--south', '-sc', help='Ending corner of search square (lat lng)', type=(float, float))
@click.option('--cellsize', '-cs', help='S2 cell size', default=13, type=click.INT)
@click.pass_context
def s2(ctx, north, south, cellsize):
    args = namedtuple('args', 'proxy latitude longitude step_size step_limit north south cellsize')
    cmdargs = args(ctx.obj['proxy'], None, None, None, None, north, south, cellsize)
    overwatch_thread = Thread(target=overwatch.overwatch, name='Overwatch', args=(cmdargs, ctx.obj['config']))
    overwatch_thread.start()
    pass

# def main():
#     parser = argparse.ArgumentParser(description='Search for Raids in Pokemon Go')
#     parser.add_argument('-lat', '--latitude', help='Starting latitude', type=float, required=True)
#     parser.add_argument('-lng', '--longitude', help='Starting longitude', type=float, required=True)
#     parser.add_argument('-st', '--step_size', help='Step Size', default=0.0082, type=float)
#     parser.add_argument('-sl', '--step_limit', help='Step Limit', default=10, type=int)
#     parser.add_argument('-p', '--proxy', help='Socks Proxy URL')
#     parser.add_argument('-a', '--accounts', help='Accounts CSV file')
#     parser.add_argument('-d', '--dump_coords', nargs='?', help='Dump Coordinates to CSV', type=argparse.FileType('w'))
#     cmdargs = parser.parse_args()
#
#     try:
#         with open('config.json') as config_file:
#             config = json.load(config_file)
#     except FileNotFoundError:
#         print("Couldn't find config file.")
#
#     if cmdargs.dump_coords:
#         writer = csv.DictWriter(cmdargs.dump_coords, fieldnames=['lat', 'lng'])
#         writer.writeheader()
#         for coords in utils.generate_spiral(cmdargs.latitude, cmdargs.longitude, cmdargs.step_size, cmdargs.step_limit):
#             writer.writerow(coords)
#     else:
#         if cmdargs.accounts:
#             config['accounts'] = [] # override config, or create empty list.
#             try:
#                 with open(cmdargs.accounts, newline='') as csv_accounts:
#                     fields = ['username', 'password', 'type']
#                     dialect = csv.Sniffer().sniff(csv_accounts.read(1024))
#                     reader = csv.DictReader(csv_accounts, fieldnames=fields, dialect=dialect)
#                     csv_accounts.seek(0)
#                     for row in reader:
#                         if row['type'] is None: # default to ptc account type
#                             row['type'] = 'ptc'
#                         config['accounts'].append(dict(row)) # append accounts to config
#             except FileNotFoundError:
#                 print("Accounts CSV missing.")
#
#         overwatch_thread = Thread(target=overwatch.overwatch, name='Overwatch', args=(cmdargs, config))
#         overwatch_thread.start()

# @click.command()
# @click.option('--position', '-pos', nargs=2, type=float, required=)
# @click.option('--step_size', '-st', type=float)
# # @click.command()
# # def main(args=None):
# #     """Console script for poGoRaidBot."""
# #     click.echo("Replace this message by putting your code into "
# #                "poGoRaidBot.cli.main")
# #     click.echo("See click documentation at http://click.pocoo.org/")
# #
# #
# # if __name__ == "__main__":
# #     main()
