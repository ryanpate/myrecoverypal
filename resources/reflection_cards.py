"""Shareable image cards for the daily reflections (Pillow).

Each card shows the reading's title and its opening line (the opening
paragraph is already public on every reading page, so a card never reveals
Premium content), branded and sized for where it's going:

    og     1200 x 630   link previews (Facebook, iMessage, X, Slack)
    post   1080 x 1350  Instagram / Facebook feed
    story  1080 x 1920  Instagram / TikTok / Facebook stories

Fonts are DejaVu, which Dockerfile.railway installs (fonts-dejavu-core).
"""
import io
import os
import re

from PIL import Image, ImageDraw, ImageFont

FORMATS = {
    'og': (1200, 630),
    'post': (1080, 1350),
    'story': (1080, 1920),
}
FONT_DIRS = ('/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/dejavu',
             '/opt/homebrew/share/fonts', '/Library/Fonts')
TOP = (15, 45, 86)        # #0f2d56
BOTTOM = (30, 77, 139)    # #1e4d8b
ACCENT = (82, 183, 136)   # #52b788
SOFT = (200, 222, 240)
SITE = 'myrecoverypal.com/reflections'


def _font(name, size):
    for d in FONT_DIRS:
        path = os.path.join(d, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def opening_line(reflection, limit=210):
    """The first sentence or two of the (public) opening paragraph."""
    text = reflection.paragraphs[0].strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    out = ''
    for s in sentences:
        if out and len(out) + 1 + len(s) > limit:
            break
        out = f'{out} {s}'.strip()
    if len(out) > limit:
        out = out[:limit].rsplit(' ', 1)[0].rstrip(',;:') + '…'
    return out


def _wrap(draw, text, font, width):
    lines, line = [], ''
    for word in text.split():
        trial = f'{line} {word}'.strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _fit(draw, text, font_name, start, minimum, width, max_lines):
    """Largest font size (stepping down) at which `text` fits in max_lines."""
    size = start
    while True:
        font = _font(font_name, size)
        lines = _wrap(draw, text, font, width)
        if len(lines) <= max_lines or size <= minimum:
            return font, lines[:max_lines]
        size -= 4


def _gradient(w, h):
    img = Image.new('RGB', (w, h), TOP)
    px = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        px.line([(0, y), (w, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM)))
    return img


def render_card(reflection, fmt='post'):
    """PNG bytes for `reflection` in one of FORMATS."""
    w, h = FORMATS[fmt]
    img = _gradient(w, h)
    d = ImageDraw.Draw(img)
    wide = fmt == 'og'
    margin = round(w * (0.07 if wide else 0.09))
    text_w = w - 2 * margin
    scale = w / 1080 if not wide else 0.62

    eyebrow = _font('DejaVuSans-Bold.ttf', round(30 * scale) if not wide else 26)
    # Stories: keep clear of the app's own UI at the top and bottom (~14%).
    y = round(h * (0.16 if fmt == 'story' else 0.09))
    d.rounded_rectangle((margin, y, margin + 14, y + 14 + round(16 * scale)), radius=7, fill=ACCENT)
    d.text((margin + 30, y - 4), 'DAILY REFLECTION', font=eyebrow, fill=SOFT)
    y += round(80 * scale) if not wide else 62

    title_font, title_lines = _fit(d, reflection.title, 'DejaVuSerif-Bold.ttf',
                                   round(96 * scale) if not wide else 64, 40, text_w, 3)
    for line in title_lines:
        d.text((margin, y), line, font=title_font, fill=(255, 255, 255))
        y += round(title_font.size * 1.18)
    y += round(36 * scale) if not wide else 22

    d.line((margin, y, margin + round(120 * (scale if not wide else 0.8)), y), fill=ACCENT, width=6)
    y += round(48 * scale) if not wide else 30

    quote_max = {'og': 3, 'post': 7, 'story': 10}[fmt]
    quote_font, quote_lines = _fit(d, opening_line(reflection), 'DejaVuSerif.ttf',
                                   round(54 * scale) if not wide else 34, 26, text_w, quote_max)
    if len(_wrap(d, opening_line(reflection), quote_font, text_w)) > quote_max:
        quote_lines[-1] = quote_lines[-1].rstrip('.,;:') + '…'
    for line in quote_lines:
        d.text((margin, y), line, font=quote_font, fill=(235, 242, 250))
        y += round(quote_font.size * 1.45)

    # Footer: brand + where to read the rest.
    brand = _font('DejaVuSans-Bold.ttf', round(40 * scale) if not wide else 30)
    small = _font('DejaVuSans.ttf', round(30 * scale) if not wide else 22)
    fy = h - (round(h * 0.14) + 80 if fmt == 'story' else margin + (round(110 * scale) if not wide else 70))
    d.text((margin, fy), 'MyRecoveryPal', font=brand, fill=(255, 255, 255))
    footer = f'Read today’s at {SITE}'
    small, _ = _fit(d, footer, 'DejaVuSans.ttf', small.size, 18, text_w, 1)
    d.text((margin, fy + round(brand.size * 1.35)), footer, font=small, fill=SOFT)

    out = io.BytesIO()
    img.save(out, format='PNG', optimize=True)
    return out.getvalue()
