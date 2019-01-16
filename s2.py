import s2sphere
from math import sin, cos, sqrt, atan2, radians

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
        points.append([ll.lat().degrees,ll.lng().degrees])

    return points

def getDistance(e):
    return e[2]

def sortCells(lat,lon, cells):
    for cell in cells:
        # approximate radius of earth in km
        R = 6373.0

        lat1 = radians(lat)
        lon1 = radians(lon)
        lat2 = radians(cell[0])
        lon2 = radians(cell[1])

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        cell.append(distance)

    cells.sort(key=getDistance)
    return cells

# cells = generate_cells(40.689442, -73.659372, 40.638343, -73.443533)
# sorted = sortCells(40.689442, -73.659372, cells)

# for cell in sorted:
    # print("{},{}".format(cell[0],cell[1]))

print(generate_cells(40.760001, -73.664929, 40.730215, -73.605404))
# 40.689442, -73.659372, 40.638343, -73.443533
