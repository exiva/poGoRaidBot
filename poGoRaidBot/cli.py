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
@click.option('--config', '-c', help='Location of Config file', type=click.File('r'), required=True)
@click.option('--host', '-lh', help='Address for HTTP server to listen on', default='127.0.0.1')
@click.option('--port', '-p', help='Port for HTTP server to listen on', default=5000)
@click.option('--devices', '-d', help='CSV of device UUIDs (identifer, UUID)', type=click.File('r'))
@click.option('--dump_coords', '-dc', help='Dump results to CSV file', type=click.File('w'))
@click.pass_context
def cli(ctx, config, host, port, devices, dump_coords):
    ctx.obj = {}
    ctx.obj['dump_coords'] = dump_coords
    ctx.obj['config'] = json.load(config)
    if devices:
        ctx.obj['config']['devices'] = []
        fields = ['identifer', 'uuid']
        dialect = csv.Sniffer().sniff(devices.read(1024))
        reader = csv.DictReader(devices, fieldnames=fields, dialect=dialect)
        devices.seek(0)
        for row in reader:
            ctx.obj['config']['devices'].append(dict(row))
    pass


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option('--latitude', '-lat', help='Starting latitude', type=click.FLOAT, required=True)
@click.option('--longitude', '-lng', help='Starting longitude', type=click.FLOAT, required=True)
@click.option('--step_size', '-st', help='Step Size', default=0.0082, type=click.FLOAT)
@click.option('--step_limit', '-sl', help='Step Limit', default=10, type=click.INT)
@click.pass_context
def spiral(ctx, latitude, longitude, step_size, step_limit):
    args = namedtuple('args', 'latitude longitude step_size step_limit north south cellsize area')
    cmdargs = args(latitude, longitude, step_size, step_limit, None, None, None, None)
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
@click.option('--north', '-nc', help='Starting corner of search square (lat lng)', type=(float, float), required=True)
@click.option('--south', '-sc', help='Ending corner of search square (lat lng)', type=(float, float), required=True)
@click.option('--level', '-lv', help='S2 cell level 1-30', default=13, type=click.IntRange(1, 30))
@click.pass_context
def s2(ctx, north, south, level):
    if not ctx.obj['dump_coords']:
        args = namedtuple('args', 'latitude longitude step_size step_limit north south level area')
        cmdargs = args(None, None, None, None, north, south, level, None)
        overwatch_thread = Thread(target=overwatch.overwatch, name='Overwatch', args=(cmdargs, ctx.obj['config']))
        overwatch_thread.start()
    else:
        writer = csv.DictWriter(ctx.obj['dump_coords'], fieldnames=['lat', 'lng'])
        writer.writeheader()
        for coords in utils.generate_cells(north[0], north[1], south[0], south[1], level):
            writer.writerow(coords)
    pass


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option('-f', help='CSV coordinates (Lat, LNG)', type=click.File('r'), required=True)
@click.pass_context
def csvfile(ctx, f):
    fields = ["lat", "lon"]
    dialect = csv.Sniffer().sniff(f.read(1024))
    f.seek(0)
    reader = csv.DictReader(f, fieldnames=fields, dialect=dialect)

    area = []
    for point in reader:
        area.append({'lat': point['lat'], 'lng': point['lon']})

    args = namedtuple('args', 'latitude longitude step_size step_limit north south cellsize area')
    cmdargs = args(None, None, None, None, None, None, None, area)
    overwatch_thread = Thread(target=overwatch.overwatch, name='Overwatch', args=(cmdargs, ctx.obj['config']))
    overwatch_thread.start()
