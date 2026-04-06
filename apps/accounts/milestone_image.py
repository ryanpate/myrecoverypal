"""Generate shareable milestone images using Pillow."""
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.cache import cache


FONT_PATH = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Inter-Bold.ttf')
BG_DIR = os.path.join(settings.BASE_DIR, 'static', 'images', 'milestones')

MILESTONE_NAMES = {
    1: '1 Day', 7: '1 Week', 14: '2 Weeks', 30: '1 Month',
    60: '2 Months', 90: '90 Days', 180: '6 Months', 365: '1 Year',
    730: '2 Years', 1095: '3 Years', 1825: '5 Years', 3650: '10 Years',
}


def get_milestone_label(days):
    if days in MILESTONE_NAMES:
        return MILESTONE_NAMES[days]
    if days >= 365:
        years = days // 365
        return f'{years} Year{"s" if years != 1 else ""}'
    if days >= 30:
        months = days // 30
        return f'{months} Month{"s" if months != 1 else ""}'
    return f'{days} Day{"s" if days != 1 else ""}'


def get_bg_tier(days):
    if days < 30:
        return 'early'
    if days < 180:
        return 'mid'
    return 'long'


def generate_milestone_image(days, fmt='story'):
    cache_key = f'milestone_img_{days}_{fmt}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    tier = get_bg_tier(days)
    bg_path = os.path.join(BG_DIR, f'bg-{tier}-{fmt}.png')
    if os.path.exists(bg_path):
        img = Image.open(bg_path).copy()
    else:
        size = (1080, 1920) if fmt == 'story' else (1080, 1080)
        img = Image.new('RGB', size, (30, 77, 139))

    draw = ImageDraw.Draw(img)
    w, h = img.size

    try:
        font_large = ImageFont.truetype(FONT_PATH, 120)
        font_medium = ImageFont.truetype(FONT_PATH, 48)
        font_small = ImageFont.truetype(FONT_PATH, 32)
    except OSError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Main text
    main_text = f'{days:,} Days Sober'
    bbox = draw.textbbox((0, 0), main_text, font=font_large)
    text_w = bbox[2] - bbox[0]
    x = (w - text_w) // 2
    y = h // 2 - 100
    draw.text((x + 3, y + 3), main_text, fill=(0, 0, 0, 80), font=font_large)
    draw.text((x, y), main_text, fill='white', font=font_large)

    # Milestone label
    label = get_milestone_label(days)
    bbox = draw.textbbox((0, 0), label, font=font_medium)
    text_w = bbox[2] - bbox[0]
    x = (w - text_w) // 2
    draw.text((x, y + 140), label, fill=(255, 255, 255, 200), font=font_medium)

    # Watermark
    watermark = 'MyRecoveryPal.com'
    bbox = draw.textbbox((0, 0), watermark, font=font_small)
    text_w = bbox[2] - bbox[0]
    x = (w - text_w) // 2
    draw.text((x, h - 80), watermark, fill=(255, 255, 255, 150), font=font_small)

    buffer = BytesIO()
    img.save(buffer, 'PNG', optimize=True)
    img_bytes = buffer.getvalue()

    cache.set(cache_key, img_bytes, 86400)
    return img_bytes
