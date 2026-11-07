"""Small stdlib-only source and stationary parking audit. Never imports bpy."""
import ast
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
contract = json.loads((ROOT / 'evidence/hotel_site_contract.json').read_text())
vehicle = json.loads((ROOT / 'evidence/vehicle_reference_dimensions.json').read_text())
sources = {}
for name in ['build_hotel.py', 'render_site_massing.py', 'check_export_bounds.py']:
    text = (ROOT / 'source' / name).read_text()
    ast.parse(text)
    sources[name] = hashlib.sha256(text.encode()).hexdigest()

build = (ROOT / 'source/build_hotel.py').read_text()
render = (ROOT / 'source/render_site_massing.py').read_text()
assert 'def frontwindow(x,y,z,w=2.2,facing=1):' in build
assert 'frontwindow(x,y,-12.09,facing=-1)' in build
assert 'z+.05*facing' in build and 'z+.06*facing' in build
assert "loading=contract['loading_rect_xz']" in render
assert "contract['parking_design']['preview_parked_cars_x_z_yaw']" in render
assert contract['loading_rect_xz'] == [-31, -23, -10, -2]

parking = contract['parking_design']
width, depth = parking['space_size']
centers = parking['bay_centers_x']
rows = parking['stall_rows_z']
assert sum(len(row) for row in parking['active_bay_centers_by_row']) == parking['spaces'] == 14
assert all(abs(x - (-11.2 + (i + .5) * width)) < 1e-8 for i, x in enumerate(centers))
assert abs(rows[1][0] - rows[0][1] - parking['two_row_aisle_width']) < 1e-8
assert all(abs(high - low - depth) < 1e-8 for low, high in rows)
lot = contract['opposite_parking_rect_xz']
assert centers[0] - width / 2 >= lot[0] and centers[-1] + width / 2 <= lot[1]
assert rows[0][0] >= lot[2] and rows[-1][1] <= lot[3]

cars = []
for x, z, yaw in parking['preview_parked_cars_x_z_yaw']:
    assert any(abs(x - center) < 1e-8 for center in centers)
    corners = []
    for px in [vehicle['minimum'][0], vehicle['maximum'][0]]:
        for pz in [vehicle['minimum'][2], vehicle['maximum'][2]]:
            corners.append((x + px * math.cos(yaw) + pz * math.sin(yaw),
                            z - px * math.sin(yaw) + pz * math.cos(yaw)))
    low_x, high_x = min(p[0] for p in corners), max(p[0] for p in corners)
    low_z, high_z = min(p[1] for p in corners), max(p[1] for p in corners)
    row = next((r for r in rows if low_z >= r[0] and high_z <= r[1]), None)
    assert row is not None
    assert any(abs(x-center)<1e-8 for center in parking['active_bay_centers_by_row'][rows.index(row)])
    corridor=parking['pedestrian_corridor_rect_xz']
    assert high_x <= corridor[0] or low_x >= corridor[1] or high_z <= corridor[2] or low_z >= corridor[3]
    assert low_x >= x - width / 2 and high_x <= x + width / 2
    cars.append({'root_x_z_yaw': [x, z, yaw], 'visual_xz_bounds': [low_x, low_z, high_x, high_z],
                 'bay_side_clearances_m': [low_x - (x-width/2), (x+width/2)-high_x],
                 'row_end_clearances_m': [low_z-row[0], row[1]-high_z]})

# Scale-only forecourt car must remain clear of the hotel-side x +/-2.5 m walk.
ref=parking['forecourt_scale_reference_x_z_yaw']
assert ref[0] - max(abs(vehicle['minimum'][2]),abs(vehicle['maximum'][2])) > 2.5
assert ref[0] + max(abs(vehicle['minimum'][2]),abs(vehicle['maximum'][2])) < 13

report = {
    'status': 'PASS_PREPARED_SOURCE_AND_STATIC_BAY_DIMENSIONS_ONLY',
    'scope': 'Syntax/source wiring and transformed inherited blue-car AABB within design bays. Does not validate hotel exports, render, engine, swept path, pedestrian or driving acceptance.',
    'source_sha256': sources,
    'contract_sha256': hashlib.sha256((ROOT/'evidence/hotel_site_contract.json').read_bytes()).hexdigest(),
    'blue_reference_sha256': hashlib.sha256((ROOT/'models/current_blue_rally_reference.glb').read_bytes()).hexdigest(),
    'lot_width_depth_m': [lot[1]-lot[0], lot[3]-lot[2]],
    'bay_count': 14, 'row_bay_width_m': 8*width, 'two_rows_plus_aisle_m': 2*depth+parking['two_row_aisle_width'],
    'parked_visual_car_checks': cars,
    'unresolved': ['Further rear-row pedestrian routing and central-aisle conflicts', 'Second current car dimensions and swept paths', 'Frozen road and proposed extension adoption', 'Actual v3 export and independent import/weather/collision tests'],
}
(ROOT/'evidence/prepared_source_parking_audit.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'status': report['status'], 'bay_count': 14, 'checked_parked_car_poses': len(cars)}))
