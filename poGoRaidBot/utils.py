import math
import random
import geopy
import s2sphere


def generate_cells(nLat, nLng, sLat, sLng, cell_size=13):
    points = []
    area = s2sphere.LatLngRect.from_point_pair(
            s2sphere.LatLng.from_degrees(nLat, nLng),
            s2sphere.LatLng.from_degrees(sLat, sLng)
        )

    r = s2sphere.RegionCoverer()
    r.min_level = cell_size
    r.max_level = cell_size

    cells = r.get_covering(area)

    for cell in cells:
        c = s2sphere.Cell(cell.parent(cell_size))
        ll = s2sphere.LatLng.from_point(c.get_center())
        points.append({'lat': ll.lat().degrees, 'lng': ll.lng().degrees})

    return points


def generate_spiral(starting_lat, starting_lng, step_size, step_limit):
    coords = [{'lat': starting_lat, 'lng': starting_lng}]
    steps, x, y, d, m = 1, 0, 0, 1, 1
    rlow = 0.0
    rhigh = 0.0005

    while steps < step_limit:
        while 2 * x * d < m and steps < step_limit:
            x = x + d
            steps += 1
            lat = x * step_size + starting_lat + random.uniform(rlow, rhigh)
            lng = y * step_size + starting_lng + random.uniform(rlow, rhigh)
            coords.append({'lat': lat, 'lng': lng})
        while 2 * y * d < m and steps < step_limit:
            y = y + d
            steps += 1
            lat = x * step_size + starting_lat + random.uniform(rlow, rhigh)
            lng = y * step_size + starting_lng + random.uniform(rlow, rhigh)
            coords.append({'lat': lat, 'lng': lng})

        d = -1 * d
        m = m + 1
    return coords


# Borrowed from RocketMap
# Returns destination coords given origin coords, distance (Ms) and bearing.
# This version is less precise and almost 1 order of magnitude faster than
# using geopy.
def fast_get_new_coords(origin, distance, bearing):
    R = 6371009  # IUGG mean earth radius in kilometers.

    oLat = math.radians(origin[0])
    oLon = math.radians(origin[1])
    b = math.radians(bearing)

    Lat = math.asin(
        math.sin(oLat) * math.cos(distance / R) +
        math.cos(oLat) * math.sin(distance / R) * math.cos(b))

    Lon = oLon + math.atan2(
        math.sin(bearing) * math.sin(distance / R) * math.cos(oLat),
        math.cos(distance / R) - math.sin(oLat) * math.sin(Lat))

    return math.degrees(Lat), math.degrees(Lon)


# Apply a location jitter.
def jitter_location(location=None, max_meters=5):
    origin = geopy.Point(location[0], location[1])
    bearing = random.randint(0, 360)
    distance = math.sqrt(random.random()) * (float(max_meters))
    destination = fast_get_new_coords(origin, distance, bearing)
    return (destination[0], destination[1])
