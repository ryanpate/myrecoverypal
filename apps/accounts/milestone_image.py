"""Generate shareable milestone badge images using badge PNG templates."""
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.cache import cache


FONT_PATH = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Inter-Bold.ttf')
BADGE_DIR = os.path.join(settings.BASE_DIR, 'static', 'images', 'badges')

BADGE_STYLES = {
    'celebration': {
        'file': 'badge-celebration.png',
        'label': 'Celebration',
        # Text goes between "MILESTONE ACHIEVED!" and "www.myrecoverypal.com"
        'time_y': 900,
        'name_y': 945,
        'time_color': (140, 110, 50, 255),
        'name_color': (120, 95, 45, 230),
        'shadow_color': (60, 45, 20, 120),
        'max_time_font': 54,
        'max_name_font': 28,
    },
    'athletic': {
        'file': 'badge-athletic.png',
        'label': 'Athletic',
        # Text goes below "MILESTONE ACHIEVED!" near the bottom
        'time_y': 900,
        'name_y': 945,
        'time_color': (200, 190, 160, 255),
        'name_color': (180, 170, 140, 230),
        'shadow_color': (20, 20, 20, 150),
        'max_time_font': 54,
        'max_name_font': 28,
    },
    'elegant': {
        'file': 'badge-elegant.png',
        'label': 'Elegant',
        # Text below "MILESTONE ACHIEVED!" at the bottom of the medal
        'time_y': 880,
        'name_y': 925,
        'time_color': (180, 160, 100, 255),
        'name_color': (160, 140, 90, 230),
        'shadow_color': (30, 25, 15, 120),
        'max_time_font': 56,
        'max_name_font': 30,
    },
    'vintage': {
        'file': 'badge-vintage.png',
        'label': 'Vintage',
        # Text below "MILESTONE ACHIEVED!" on the worn bronze medal
        'time_y': 880,
        'name_y': 925,
        'time_color': (200, 185, 140, 255),
        'name_color': (180, 165, 120, 230),
        'shadow_color': (30, 25, 15, 150),
        'max_time_font': 56,
        'max_name_font': 30,
    },
}

TIME_FORMATS = {
    'auto': 'Auto (best fit)',
    'days': 'Days only',
    'months': 'Months & days',
    'years': 'Years & months',
    'full': 'Years, months & days',
}


def format_sobriety_time(days, fmt='auto'):
    """Format sobriety time based on user's chosen format."""
    years = days // 365
    remaining_after_years = days % 365
    months = remaining_after_years // 30
    remaining_days = remaining_after_years % 30

    if fmt == 'days':
        return f'{days:,} Day{"s" if days != 1 else ""}'

    if fmt == 'months':
        total_months = days // 30
        d = days % 30
        parts = []
        if total_months > 0:
            parts.append(f'{total_months} Month{"s" if total_months != 1 else ""}')
        if d > 0 or not parts:
            parts.append(f'{d} Day{"s" if d != 1 else ""}')
        return ', '.join(parts)

    if fmt == 'years':
        parts = []
        if years > 0:
            parts.append(f'{years} Year{"s" if years != 1 else ""}')
        if months > 0 or not parts:
            parts.append(f'{months} Month{"s" if months != 1 else ""}')
        return ', '.join(parts)

    if fmt == 'full':
        parts = []
        if years > 0:
            parts.append(f'{years} Year{"s" if years != 1 else ""}')
        if months > 0:
            parts.append(f'{months} Month{"s" if months != 1 else ""}')
        if remaining_days > 0 or not parts:
            parts.append(f'{remaining_days} Day{"s" if remaining_days != 1 else ""}')
        return ', '.join(parts)

    # auto — pick the most natural representation
    if days < 30:
        return f'{days} Day{"s" if days != 1 else ""}'
    if days < 365:
        if remaining_days > 0:
            return f'{months} Month{"s" if months != 1 else ""}, {remaining_days} Day{"s" if remaining_days != 1 else ""}'
        return f'{months} Month{"s" if months != 1 else ""}'
    if months > 0:
        return f'{years} Year{"s" if years != 1 else ""}, {months} Month{"s" if months != 1 else ""}'
    return f'{years} Year{"s" if years != 1 else ""}'


def generate_milestone_image(days, style='celebration', name='', time_format='auto'):
    """Generate a personalized milestone badge image.

    Args:
        days: Number of days sober.
        style: Badge style key from BADGE_STYLES.
        name: Optional display name to include on the badge.
        time_format: How to display sobriety time (auto/days/months/years/full).

    Returns:
        PNG image bytes.
    """
    if style not in BADGE_STYLES:
        style = 'celebration'
    if time_format not in TIME_FORMATS:
        time_format = 'auto'

    # Cache key includes all personalization params
    safe_name = name.strip()[:30] if name else ''
    import hashlib
    name_hash = hashlib.md5(safe_name.encode()).hexdigest()[:8] if safe_name else 'anon'
    cache_key = f'milestone_v4_{days}_{style}_{time_format}_{name_hash}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    config = BADGE_STYLES[style]
    badge_path = os.path.join(BADGE_DIR, config['file'])

    # Load and resize the badge template
    badge = Image.open(badge_path).convert('RGBA')
    target = 1080
    badge = badge.resize((target, target), Image.LANCZOS)

    # Create overlay for text
    overlay = Image.new('RGBA', (target, target), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    cx = target // 2
    time_text = format_sobriety_time(days, time_format)

    # Scale font size based on text length
    base_font = config['max_time_font']
    if len(time_text) > 22:
        font_size = int(base_font * 0.7)
    elif len(time_text) > 16:
        font_size = int(base_font * 0.8)
    elif len(time_text) > 10:
        font_size = int(base_font * 0.9)
    else:
        font_size = base_font

    try:
        font_time = ImageFont.truetype(FONT_PATH, font_size)
        font_name = ImageFont.truetype(FONT_PATH, config['max_name_font'])
    except OSError:
        font_time = ImageFont.load_default()
        font_name = ImageFont.load_default()

    # Draw sobriety time
    bbox = draw.textbbox((0, 0), time_text, font=font_time)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = cx - tw // 2
    y = config['time_y'] - th // 2

    # If name is included, shift time up to make room
    if safe_name:
        y -= 20

    # Shadow
    draw.text((x + 2, y + 2), time_text, fill=config['shadow_color'], font=font_time)
    # Main text
    draw.text((x, y), time_text, fill=config['time_color'], font=font_time)

    # Draw optional name
    if safe_name:
        bbox = draw.textbbox((0, 0), safe_name, font=font_name)
        tw = bbox[2] - bbox[0]
        nx = cx - tw // 2
        ny = config['name_y']
        draw.text((nx + 1, ny + 1), safe_name, fill=config['shadow_color'], font=font_name)
        draw.text((nx, ny), safe_name, fill=config['name_color'], font=font_name)

    # Composite and convert
    result = Image.alpha_composite(badge, overlay)
    final = result.convert('RGB')

    buffer = BytesIO()
    final.save(buffer, 'PNG', optimize=True)
    img_bytes = buffer.getvalue()

    cache.set(cache_key, img_bytes, 86400)
    return img_bytes
