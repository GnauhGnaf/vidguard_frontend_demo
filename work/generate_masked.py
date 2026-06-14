import json, sys
from PIL import Image, ImageDraw, ImageFont

def process(json_path, image_path, output_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    img = Image.open(image_path).convert('RGBA')
    font = ImageFont.truetype('PingFangSC-Semibold.ttf', 40)
    normal_rgba = (0x48, 0x74, 0xCB, 77)   # #4874CB at 70% transparency
    danger_rgba = (0xC8, 0x1D, 0x31, 77)   # #C81D31 at 70% transparency
    danger_labels = {'gun', 'knife'}
    text_color = (0xFF, 0x00, 0x00)

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
        # center on the actual glyph, not the full box
        x = cx - (bbox[2] + bbox[0]) / 2
        y = cy - (bbox[3] + bbox[1]) / 2
        # clamp so that actual glyph stays inside image
        x = max(-bbox[0], min(x, w - bbox[2]))
        y = max(-bbox[1], min(y, h - bbox[3]))
        draw.text((x, y), label, fill=text_color, font=font)

    img.convert('RGB').save(output_path, quality=95)
    print(f'done: {output_path}')

# ── batch ────────────────────────────────────────────────
if len(sys.argv) > 1:
    # usage: python generate_masked.py json image output
    process(sys.argv[1], sys.argv[2], sys.argv[3])
else:
    # default: safe video
    process('safe_middle_frame.json', 'safe_middle_frame.jpg', 'safe_middle_frame_masked.jpg')
