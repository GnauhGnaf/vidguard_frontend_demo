"""
Generate complete scene graph data for the safe case.
Visual graph: person1 -> touch -> bottle -> contain -> water
              person1 -> drink -> water  (drink appears frames 53-116)
"""
import json, os

INPUT_DIR = 'safe_frames'
TOTAL_FRAMES = 141
IMG_W, IMG_H = 1280, 720


def centroid(pts):
    """Compute polygon centroid."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    n = len(pts)
    area = 0.0; cx = 0.0; cy = 0.0
    for i in range(n):
        x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        area += cross; cx += (x0 + x1) * cross; cy += (y0 + y1) * cross
    area *= 0.5
    if abs(area) < 1e-6:
        return sum(xs) / n, sum(ys) / n
    return cx / (6 * area), cy / (6 * area)


def load_all_frames():
    """Load entity centroids for all frames from LabelMe JSONs."""
    frame_entities = {}
    for f in range(1, TOTAL_FRAMES + 1):
        path = os.path.join(INPUT_DIR, f'frame_{f:04d}.json')
        with open(path, 'r') as fh:
            data = json.load(fh)
        entities = {}
        for shape in data['shapes']:
            label = shape['label']
            cx, cy = centroid(shape['points'])
            entities[label] = {'cx': cx, 'cy': cy}
        frame_entities[f] = entities
    return frame_entities


def make_scene_graph(frame_num, frame_entities):
    """Generate nodes and arrows for a given frame."""
    entities = frame_entities.get(frame_num, {})

    nodes = {}
    arrows = []

    # Real entities from annotations
    p1 = entities.get('person1')
    bt = entities.get('bottle')
    wa = entities.get('water')

    if not (p1 and bt and wa):
        return {'nodes': nodes, 'arrows': arrows}

    # Add real entities
    for name in ['person1', 'bottle', 'water']:
        e = entities[name]
        nodes[name] = {'label': name, 'type': 'entity',
                       'cx': e['cx'] / IMG_W, 'cy': e['cy'] / IMG_H}

    # Compute abstract nodes from real positions
    touch_cx = (p1['cx'] + bt['cx']) / 2
    touch_cy = (p1['cy'] + bt['cy']) / 2
    nodes['touch'] = {'label': 'touch', 'type': 'action',
                      'cx': touch_cx / IMG_W, 'cy': touch_cy / IMG_H}

    contain_cx = (bt['cx'] + wa['cx']) / 2
    contain_cy = (bt['cy'] + wa['cy']) / 2
    nodes['contain'] = {'label': 'contain', 'type': 'action',
                        'cx': contain_cx / IMG_W, 'cy': contain_cy / IMG_H}

    # drink: above person1 (near head), appears frames 53-116
    if 53 <= frame_num <= 116:
        drink_cx = p1['cx']
        drink_cy = p1['cy'] - (p1['cy'] * 0.6)
        nodes['drink'] = {'label': 'drink', 'type': 'action',
                          'cx': drink_cx / IMG_W, 'cy': max(0.05, drink_cy / IMG_H)}

    # Arrows: person1 -> touch -> bottle -> contain -> water
    for a, b in [('person1', 'touch'), ('touch', 'bottle'), ('bottle', 'contain'), ('contain', 'water')]:
        if a in nodes and b in nodes:
            arrows.append({'from': a, 'to': b})

    # drink arrows
    if 'drink' in nodes:
        arrows.append({'from': 'person1', 'to': 'drink'})
        arrows.append({'from': 'drink', 'to': 'water'})

    return {'nodes': nodes, 'arrows': arrows}


# Load all frame data
frame_entities = load_all_frames()

# Generate per-frame scene data
scene_data = {}
for f in range(1, TOTAL_FRAMES + 1):
    scene_data[f] = make_scene_graph(f, frame_entities)

# Cumulative: always show current state (drink appears at 53)
cumulative_data = {}
for f in range(1, TOTAL_FRAMES + 1):
    cumulative_data[f] = make_scene_graph(f, frame_entities)

# Frame annotations (which entities appear in each frame)
frame_annotations = {}
for f in range(1, TOTAL_FRAMES + 1):
    entities = frame_entities.get(f, {})
    frame_annotations[f] = sorted(entities.keys())

# Output as JS file
js_lines = [
    '// Auto-generated scene graph data for safe case',
    f'export const TOTAL_FRAMES = {TOTAL_FRAMES};',
    'export const IMG_W = 1280;',
    'export const IMG_H = 720;',
    '',
]

js_lines.append('export const frameAnnotations = ' + json.dumps(frame_annotations, indent=2) + ';')
js_lines.append('')
js_lines.append('export const sceneData = ' + json.dumps(scene_data, indent=2) + ';')
js_lines.append('')
js_lines.append('export const cumulativeData = ' + json.dumps(cumulative_data, indent=2) + ';')

with open('safe_scene_graph.js', 'w') as f:
    f.write('\n'.join(js_lines))

print(f'Generated scene graph data for {TOTAL_FRAMES} frames')
print(f'Frames with drink: {sum(1 for f in range(1, TOTAL_FRAMES+1) if "drink" in frame_entities.get(f, {}))}')
print('Saved to safe_scene_graph.js')
