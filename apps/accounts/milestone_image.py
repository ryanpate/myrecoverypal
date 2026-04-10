"""Generate shareable milestone badge images using badge PNG templates."""
import hashlib
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.cache import cache


FONT_PATH = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Inter-Bold.ttf')
BADGE_DIR = os.path.join(settings.BASE_DIR, 'static', 'images', 'badges')

BADGE_STYLES = {
    'celebration': {'file': 'badge-celebration.png', 'label': 'Celebration'},
    'athletic': {'file': 'badge-athletic.png', 'label': 'Athletic'},
    'elegant': {'file': 'badge-elegant.png', 'label': 'Elegant'},
    'vintage': {'file': 'badge-vintage.png', 'label': 'Vintage'},
    'comic': {'file': 'badge-comic.png', 'label': 'Comic'},
    'crystal': {'file': 'badge-crystal.png', 'label': 'Crystal'},
    'anime': {'file': 'badge-anime.png', 'label': 'Anime'},
}

TIME_FORMATS = {
    'auto': 'Auto (best fit)',
    'days': 'Days only',
    'months': 'Months & days',
    'years': 'Years & months',
    'full': 'Years, months & days',
}

# Preset colors users can pick from
TEXT_COLORS = {
    'white': (255, 255, 255),
    'gold': (212, 175, 55),
    'silver': (192, 192, 192),
    'black': (20, 20, 20),
    'cream': (255, 253, 208),
    'bronze': (140, 110, 50),
}


def _hex_to_rgb(hex_str):
    """Convert '#RRGGBB' to (R, G, B) tuple."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return (255, 255, 255)


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

    # auto
    if days < 30:
        return f'{days} Day{"s" if days != 1 else ""}'
    if days < 365:
        if remaining_days > 0:
            return f'{months} Month{"s" if months != 1 else ""}, {remaining_days} Day{"s" if remaining_days != 1 else ""}'
        return f'{months} Month{"s" if months != 1 else ""}'
    if months > 0:
        return f'{years} Year{"s" if years != 1 else ""}, {months} Month{"s" if months != 1 else ""}'
    return f'{years} Year{"s" if years != 1 else ""}'


def _draw_outlined_text(draw, x, y, text, font, fill, outline_width):
    """Draw text with a dark outline for readability."""
    # Outline color: dark version of fill or black
    outline_color = (0, 0, 0, 220)
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, fill=outline_color, font=font)
    draw.text((x, y), text, fill=fill, font=font)


def generate_milestone_image(days, style='celebration', name='', time_format='auto',
                              text_y=50, font_size=48, color='white', outline=True):
    """Generate a personalized milestone badge image.

    Args:
        days: Number of days sober.
        style: Badge style key from BADGE_STYLES.
        name: Optional display name to include on the badge.
        time_format: How to display sobriety time.
        text_y: Vertical position as percentage (0=top, 100=bottom).
        font_size: Font size in pixels (24-96).
        color: Color name from TEXT_COLORS or hex '#RRGGBB'.
        outline: Whether to draw a dark outline around text.
    """
    if style not in BADGE_STYLES:
        style = 'celebration'
    if time_format not in TIME_FORMATS:
        time_format = 'auto'
    text_y = max(0, min(100, int(text_y)))
    font_size = max(24, min(96, int(font_size)))

    safe_name = name.strip()[:30] if name else ''

    # Resolve color
    if color.startswith('#'):
        rgb = _hex_to_rgb(color)
    else:
        rgb = TEXT_COLORS.get(color, TEXT_COLORS['white'])
    fill = (*rgb, 255)

    # Cache key
    params = f'{days}_{style}_{time_format}_{text_y}_{font_size}_{color}_{int(outline)}_{safe_name}'
    cache_key = f'milestone_v5_{hashlib.md5(params.encode()).hexdigest()}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    config = BADGE_STYLES[style]
    badge_path = os.path.join(BADGE_DIR, config['file'])

    badge = Image.open(badge_path).convert('RGBA')
    target = 1080
    badge = badge.resize((target, target), Image.LANCZOS)

    overlay = Image.new('RGBA', (target, target), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    cx = target // 2
    time_text = format_sobriety_time(days, time_format)

    try:
        font_time = ImageFont.truetype(FONT_PATH, font_size)
        name_font_size = max(20, font_size - 16)
        font_name = ImageFont.truetype(FONT_PATH, name_font_size)
    except OSError:
        font_time = ImageFont.load_default()
        font_name = ImageFont.load_default()

    # Convert text_y percentage to pixel position (with margins)
    margin = 40
    usable = target - 2 * margin
    pixel_y = margin + int(usable * text_y / 100)

    # Draw sobriety time — centered horizontally at the user's chosen Y
    bbox = draw.textbbox((0, 0), time_text, font=font_time)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = cx - tw // 2

    outline_w = 3 if outline else 0
    if outline:
        _draw_outlined_text(draw, x, pixel_y, time_text, font_time, fill, outline_w)
    else:
        draw.text((x, pixel_y), time_text, fill=fill, font=font_time)

    # Draw optional name below sobriety time
    if safe_name:
        bbox = draw.textbbox((0, 0), safe_name, font=font_name)
        ntw = bbox[2] - bbox[0]
        nx = cx - ntw // 2
        ny = pixel_y + th + 10

        if outline:
            _draw_outlined_text(draw, nx, ny, safe_name, font_name, fill, max(1, outline_w - 1))
        else:
            draw.text((nx, ny), safe_name, fill=fill, font=font_name)

    result = Image.alpha_composite(badge, overlay)
    final = result.convert('RGB')

    buffer = BytesIO()
    final.save(buffer, 'PNG', optimize=True)
    img_bytes = buffer.getvalue()

    cache.set(cache_key, img_bytes, 86400)
    return img_bytes
