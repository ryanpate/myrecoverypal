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
    'classic': {'file': 'badge-classic.png', 'label': 'Classic'},
    'parchment': {'file': 'badge-parchment.png', 'label': 'Parchment'},
    'celestial': {'file': 'badge-celestial.png', 'label': 'Celestial'},
    'antique': {'file': 'badge-antique.png', 'label': 'Antique'},
    'midnight': {'file': 'badge-midnight.png', 'label': 'Midnight'},
    'sapphire': {'file': 'badge-sapphire.png', 'label': 'Sapphire'},
    'pearl': {'file': 'badge-pearl.png', 'label': 'Pearl'},
    'silver': {'file': 'badge-silver.png', 'label': 'Silver'},
    'sunset': {'file': 'badge-sunset.png', 'label': 'Sunset'},
    'obsidian': {'file': 'badge-obsidian.png', 'label': 'Obsidian'},
    'phoenix': {'file': 'badge-phoenix.png', 'label': 'Phoenix'},
    'lighthouse': {'file': 'badge-lighthouse.png', 'label': 'Lighthouse'},
    'winter': {'file': 'badge-winter.png', 'label': 'Winter'},
    'blossom': {'file': 'badge-blossom.png', 'label': 'Blossom'},
    'anchor': {'file': 'badge-anchor.png', 'label': 'Anchor'},
    'dove': {'file': 'badge-dove.png', 'label': 'Dove'},
    'mountain': {'file': 'badge-mountain.png', 'label': 'Mountain'},
}

# Styles available to anonymous (non-signed-in) visitors. The rest are gated
# behind a free account — signup unlocks the full collection.
FREE_BADGE_STYLES = {'classic', 'silver', 'mountain'}

# Fraction of badge width where the gold center circle sits for text.
# All "My Recovery Pal" medallion templates share the same center-circle layout.
CENTER_WIDTH_RATIO = 0.34

TIME_FORMATS = {
    'days': 'Days',
    'months': 'Months',
    'years': 'Years',
    'auto': 'Auto',
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


def _int_to_roman(num):
    """Convert an integer (1-3999) to a Roman numeral string, AA-coin style."""
    if num < 1:
        return 'I'
    if num > 3999:
        return str(num)
    vals = [
        (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
        (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
        (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'),
    ]
    result = ''
    for value, numeral in vals:
        while num >= value:
            result += numeral
            num -= value
    return result


def format_sobriety_time(days, fmt='auto'):
    """Format sobriety time as (primary, subtitle) for the badge center circle.

    Years render as a bare Roman numeral (no "Years" word), matching AA medallion
    tradition. Months and days render as a large number with the unit label stacked
    below it.
    """
    if fmt == 'days':
        return (f'{days:,}', 'Day' if days == 1 else 'Days')

    if fmt == 'months':
        total_months = max(1, days // 30)
        return (f'{total_months}', 'Month' if total_months == 1 else 'Months')

    if fmt == 'years':
        total_years = max(1, days // 365)
        return (_int_to_roman(total_years), '')

    # auto: pick the largest unit that reads naturally
    if days < 30:
        return (f'{days}', 'Day' if days == 1 else 'Days')
    if days < 365:
        months = days // 30
        return (f'{months}', 'Month' if months == 1 else 'Months')
    years = days // 365
    return (_int_to_roman(years), '')


def _draw_outlined_text(draw, x, y, text, font, fill, outline_width):
    """Draw text with a dark outline for readability."""
    # Outline color: dark version of fill or black
    outline_color = (0, 0, 0, 220)
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, fill=outline_color, font=font)
    draw.text((x, y), text, fill=fill, font=font)


def _load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _fit_font_to_width(draw, text, max_font, max_width, min_font=24):
    """Return the largest font (<= max_font) whose rendered text fits within max_width."""
    size = max_font
    while size > min_font:
        font = _load_font(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            return font, size
        size -= 2
    return _load_font(min_font), min_font


def generate_milestone_image(days, style='classic', name='', time_format='auto',
                              text_y=50, font_size=110, color='white', outline=True):
    """Generate a personalized milestone badge image.

    Places the sobriety time inside the gold center circle of the badge,
    auto-shrinking the font if the text would overflow the circle.

    Args:
        days: Number of days sober.
        style: Badge style key from BADGE_STYLES.
        name: Optional display name to include on the badge.
        time_format: How to display sobriety time (days/months/years/etc).
        text_y: Vertical position as percentage (0=top, 100=bottom). 50 = center.
        font_size: Maximum font size in pixels (24-160). Shrinks to fit circle.
        color: Color name from TEXT_COLORS or hex '#RRGGBB'.
        outline: Whether to draw a dark outline around text.
    """
    if style not in BADGE_STYLES:
        style = 'classic'
    if time_format not in TIME_FORMATS:
        time_format = 'auto'
    text_y = max(0, min(100, int(text_y)))
    font_size = max(24, min(160, int(font_size)))

    safe_name = name.strip()[:30] if name else ''

    if color.startswith('#'):
        rgb = _hex_to_rgb(color)
    else:
        rgb = TEXT_COLORS.get(color, TEXT_COLORS['white'])
    fill = (*rgb, 255)

    params = f'{days}_{style}_{time_format}_{text_y}_{font_size}_{color}_{int(outline)}_{safe_name}'
    cache_key = f'milestone_v8_{hashlib.md5(params.encode()).hexdigest()}'
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
    primary_text, unit_text = format_sobriety_time(days, time_format)

    # Fit primary text (number or Roman numeral) to the gold center circle width.
    max_text_width = int(target * CENTER_WIDTH_RATIO) - 20
    font_time, fitted_size = _fit_font_to_width(draw, primary_text, font_size, max_text_width)

    # Unit label ("Months"/"Days") sits under the number at ~42% of the primary size.
    unit_font = None
    unit_w = 0
    unit_h = 0
    unit_gap = 0
    if unit_text:
        unit_target_size = max(20, int(fitted_size * 0.42))
        unit_font, _ = _fit_font_to_width(draw, unit_text, unit_target_size, max_text_width, min_font=16)
        ubbox = draw.textbbox((0, 0), unit_text, font=unit_font)
        unit_w = ubbox[2] - ubbox[0]
        unit_h = ubbox[3] - ubbox[1]
        unit_gap = max(4, int(fitted_size * 0.08))

    name_max_size = max(20, fitted_size - 24)
    font_name = _load_font(name_max_size)
    if safe_name:
        font_name, _ = _fit_font_to_width(draw, safe_name, name_max_size, max_text_width)

    # text_y percentage → pixel position. At 50% the text sits centered on the badge.
    margin = 40
    usable = target - 2 * margin
    pixel_y_anchor = margin + int(usable * text_y / 100)

    bbox = draw.textbbox((0, 0), primary_text, font=font_time)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    # Center the (primary + optional unit) stack vertically on the anchor Y.
    stack_h = th + (unit_gap + unit_h if unit_text else 0)
    time_y = pixel_y_anchor - stack_h // 2 - bbox[1]
    x = cx - tw // 2

    outline_w = 3 if outline else 0
    if outline:
        _draw_outlined_text(draw, x, time_y, primary_text, font_time, fill, outline_w)
    else:
        draw.text((x, time_y), primary_text, fill=fill, font=font_time)

    if unit_text:
        unit_x = cx - unit_w // 2
        unit_y = time_y + th + unit_gap
        if outline:
            _draw_outlined_text(draw, unit_x, unit_y, unit_text, unit_font, fill, max(1, outline_w - 1))
        else:
            draw.text((unit_x, unit_y), unit_text, fill=fill, font=unit_font)

    if safe_name:
        nbbox = draw.textbbox((0, 0), safe_name, font=font_name)
        ntw = nbbox[2] - nbbox[0]
        nx = cx - ntw // 2
        ny = time_y + stack_h + 12

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
