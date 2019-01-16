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
        points.append({ll.lat().degrees,ll.lng().degrees})

    return points



print(generate_cells(40.689442, -73.659372, 40.638343, -73.443533))
# 40.689442, -73.659372, 40.638343, -73.443533
