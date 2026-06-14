import json, sys, os, shutil
from PIL import Image, ImageDraw, ImageFont

INPUT_DIR  = 'harmful_frames'
OUTPUT_DIR = 'harmful_masked_frames'
FONT_PATH  = 'PingFangSC-Semibold.ttf'

danger_labels = {'gun', 'knife'}
normal_rgba = (0x48, 0x74, 0xCB, 77)
danger_rgba = (0xC8, 0x1D, 0x31, 77)
text_color   = (0xFF, 0x00, 0x00)

font = ImageFont.truetype(FONT_PATH, 40)

def centroid(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
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

def process_one(json_path, image_path, output_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    img = Image.open(image_path).convert('RGBA')

    # step 1: composite masks
    labels = []
    for shape in data['shapes']:
        label = shape['label']
        pts = [(p[0], p[1]) for p in shape['points']]
        rgba = danger_rgba if label in danger_labels else normal_rgba
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon(pts, fill=rgba)
        img = Image.alpha_composite(img, layer)
        cx, cy = centroid(pts)
        labels.append((label, cx, cy))

    # step 2: draw text (clamped to image bounds)
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for label, cx, cy in labels:
        bbox = draw.textbbox((0, 0), label, font=font)
        x = cx - (bbox[2] + bbox[0]) / 2
        y = cy - (bbox[3] + bbox[1]) / 2
        x = max(-bbox[0], min(x, w - bbox[2]))
        y = max(-bbox[1], min(y, h - bbox[3]))
        draw.text((x, y), label, fill=text_color, font=font)

    img.convert('RGB').save(output_path, quality=95)
    return True

# ── batch ────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)

jpgs = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith('.jpg'))
total = len(jpgs)
done = 0; masked = 0; copied = 0

for jpg in jpgs:
    base = jpg.replace('.jpg', '')
    json_path = os.path.join(INPUT_DIR, base + '.json')
    jpg_path  = os.path.join(INPUT_DIR, jpg)
    out_path  = os.path.join(OUTPUT_DIR, jpg)

    if os.path.exists(json_path):
        try:
            process_one(json_path, jpg_path, out_path)
            masked += 1
        except Exception as e:
            print(f'  ERROR {jpg}: {e}')
            shutil.copy2(jpg_path, out_path)
            copied += 1
    else:
        shutil.copy2(jpg_path, out_path)
        copied += 1

    done += 1
    if done % 20 == 0 or done == total:
        print(f'  [{done}/{total}] masked={masked} copied={copied}')

print(f'\nDone. {masked} masked, {copied} original, {total} total → {OUTPUT_DIR}/')
