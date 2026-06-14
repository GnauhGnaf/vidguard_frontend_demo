"""Generate LabelMe JSON annotation files for safe_frames."""
import json, os

OUT_DIR = 'safe_frames'
os.makedirs(OUT_DIR, exist_ok=True)

TOTAL = 141

# Entity polygon coordinates (x,y pairs) — rough bounding boxes for a 1280x720 frame
# person1: woman on the left-center
# touch: hand/contact area between person1 and bottle
# bottle: center of frame
# contain: relationship between bottle and water
# water: right side area
# drink: near person1's mouth, only frames 53-116

SHAPES = {
    'person1': [
        [80, 120], [60, 250], [50, 380], [55, 500], [70, 600],
        [130, 650], [220, 660], [300, 640], [350, 580], [370, 480],
        [360, 350], [340, 200], [300, 100], [200, 80], [130, 90],
    ],
    'touch': [
        [370, 280], [350, 320], [340, 380], [360, 420],
        [420, 430], [480, 410], [500, 360], [480, 300], [420, 270],
    ],
    'bottle': [
        [500, 200], [470, 280], [460, 380], [480, 480], [520, 530],
        [590, 540], [650, 500], [680, 400], [670, 280], [620, 190], [550, 180],
    ],
    'contain': [
        [640, 300], [620, 350], [630, 420], [670, 450],
        [740, 440], [780, 390], [770, 330], [720, 280],
    ],
    'water': [
        [760, 260], [720, 350], [710, 450], [740, 540], [800, 580],
        [880, 570], [940, 520], [970, 420], [960, 320], [900, 240], [820, 230],
    ],
    'drink': [
        [180, 80], [150, 110], [140, 150], [155, 190],
        [210, 200], [260, 180], [270, 140], [250, 90],
    ],
}

for f in range(1, TOTAL + 1):
    name = f'frame_{f:04d}'
    shapes = []

    # Always present
    entities = ['person1', 'touch', 'bottle', 'contain', 'water']
    # drink appears frame 53-116
    if 53 <= f <= 116:
        entities.append('drink')

    for label in entities:
        if label in SHAPES:
            shapes.append({
                'label': label,
                'points': SHAPES[label],
                'shape_type': 'polygon',
                'flags': {},
                'group_id': None,
                'description': None,
                'mask': None,
            })

    data = {
        'version': '5.10.1',
        'flags': {},
        'shapes': shapes,
    }

    path = os.path.join(OUT_DIR, name + '.json')
    with open(path, 'w') as fh:
        json.dump(data, fh, indent=2)

print(f'Generated {TOTAL} JSON files in {OUT_DIR}/')
