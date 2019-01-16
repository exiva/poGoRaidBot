import random
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
        c = s2sphere.Cell(cell.parent(13))
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
