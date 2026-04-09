"""Generate shareable milestone badge images using Pillow."""
import math
import os
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.cache import cache


FONT_PATH = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Inter-Bold.ttf')

MILESTONE_NAMES = {
    1: '1 Day', 7: '1 Week', 14: '2 Weeks', 30: '1 Month',
    60: '2 Months', 90: '90 Days', 180: '6 Months', 365: '1 Year',
    730: '2 Years', 1095: '3 Years', 1825: '5 Years', 3650: '10 Years',
}

# Tier color schemes: (inner_color, outer_color)
TIER_COLORS = {
    'early': {
        'gradient': [(242, 134, 81), (229, 75, 95)],  # warm sunrise orange → coral
        'ring': (255, 255, 255),
        'ring_track': (255, 255, 255, 40),
        'ring_glow': (255, 200, 150, 60),
        'tagline': 'Every day counts',
    },
    'mid': {
        'gradient': [(66, 134, 244), (55, 48, 163)],  # cool blue → indigo
        'ring': (255, 255, 255),
        'ring_track': (255, 255, 255, 40),
        'ring_glow': (150, 180, 255, 60),
        'tagline': None,
    },
    'long': {
        'gradient': [(108, 45, 199), (186, 143, 33)],  # deep purple → gold
        'ring': (255, 255, 255),
        'ring_track': (255, 255, 255, 40),
        'ring_glow': (220, 190, 100, 80),
        'tagline': None,
    },
}

# Milestones for progress ring calculation
MILESTONE_DAYS = [1, 7, 14, 30, 60, 90, 180, 365, 730, 1095, 1825, 3650]


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


def get_milestone_progress(days):
    """Return (progress 0.0-1.0, current_milestone, next_milestone)."""
    prev = 1
    for m in MILESTONE_DAYS:
        if days < m:
            progress = (days - prev) / max(1, m - prev)
            return min(progress, 1.0), prev, m
        prev = m
    return 1.0, MILESTONE_DAYS[-1], MILESTONE_DAYS[-1]


def _lerp_color(c1, c2, t):
    """Linear interpolate between two RGB tuples."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _draw_radial_gradient(img, center, radius, inner_color, outer_color):
    """Draw a radial gradient on the image."""
    draw = ImageDraw.Draw(img)
    for r in range(int(radius), 0, -1):
        t = 1.0 - (r / radius)
        color = _lerp_color(outer_color, inner_color, t)
        bbox = [center[0] - r, center[1] - r, center[0] + r, center[1] + r]
        draw.ellipse(bbox, fill=color)


def _draw_gradient_background(img, color1, color2):
    """Fill image with a diagonal linear gradient."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        color = _lerp_color(color1, color2, t)
        draw.line([(0, y), (w, y)], fill=color)


def _draw_vignette(img):
    """Apply a subtle dark vignette around the edges."""
    w, h = img.size
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    max_dim = max(w, h)
    cx, cy = w // 2, h // 2
    for i in range(40):
        r = max_dim * (0.5 + i * 0.02)
        alpha = int(i * 1.8)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(0, 0, 0, alpha),
            width=max(1, int(max_dim * 0.015)),
        )
    img_rgba = img.convert('RGBA')
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    return img_rgba.convert('RGB')


def _draw_sparkles(draw, w, h, count, tier):
    """Draw decorative sparkle/star shapes."""
    rng = random.Random(42)  # deterministic for caching
    for _ in range(count):
        x = rng.randint(int(w * 0.05), int(w * 0.95))
        y = rng.randint(int(h * 0.05), int(h * 0.95))
        size = rng.randint(2, 6) if tier != 'long' else rng.randint(3, 10)
        alpha = rng.randint(60, 150)
        color = (255, 255, 255, alpha)
        # 4-point star shape
        draw.line([(x - size, y), (x + size, y)], fill=color, width=1)
        draw.line([(x, y - size), (x, y + size)], fill=color, width=1)
        # Diagonal lines for larger sparkles
        if size > 4:
            ds = size // 2
            draw.line([(x - ds, y - ds), (x + ds, y + ds)], fill=color, width=1)
            draw.line([(x - ds, y + ds), (x + ds, y - ds)], fill=color, width=1)


def _draw_ring(draw, center, radius, thickness, progress, ring_color, track_color, glow_color, tier):
    """Draw a progress ring with optional glow."""
    cx, cy = center

    # Glow behind the ring
    if glow_color:
        for g in range(6, 0, -1):
            glow_r = radius + g * 2
            glow_thick = thickness + g * 4
            a = glow_color[3] // (g + 1)
            gc = (*glow_color[:3], a)
            bbox = [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r]
            draw.arc(bbox, -90, -90 + int(360 * progress), fill=gc, width=glow_thick)

    # Track (full circle, faded)
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    draw.arc(bbox, 0, 360, fill=track_color, width=thickness)

    # Progress arc
    if progress > 0:
        start_angle = -90
        end_angle = -90 + int(360 * progress)
        draw.arc(bbox, start_angle, end_angle, fill=ring_color, width=thickness)

    # Double ring for long tier
    if tier == 'long':
        outer_r = radius + thickness + 8
        outer_bbox = [cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r]
        draw.arc(outer_bbox, 0, 360, fill=(*ring_color[:3], 60) if len(ring_color) > 3 else (*ring_color, 60), width=2)

    # Milestone markers on ring for mid tier
    if tier == 'mid':
        for frac in [0.25, 0.5, 0.75]:
            angle = math.radians(-90 + 360 * frac)
            mx = cx + int(radius * math.cos(angle))
            my = cy + int(radius * math.sin(angle))
            draw.ellipse([mx - 3, my - 3, mx + 3, my + 3], fill=(255, 255, 255, 120))


def generate_milestone_image(days, fmt='story'):
    cache_key = f'milestone_badge_{days}_{fmt}_v2'
    cached = cache.get(cache_key)
    if cached:
        return cached

    size = (1080, 1920) if fmt == 'story' else (1080, 1080)
    w, h = size
    tier = get_bg_tier(days)
    colors = TIER_COLORS[tier]
    progress, _, _ = get_milestone_progress(days)

    # Create RGBA image for alpha support
    img = Image.new('RGBA', size, (0, 0, 0, 255))

    # Draw gradient background
    bg = Image.new('RGB', size)
    _draw_gradient_background(bg, colors['gradient'][0], colors['gradient'][1])
    bg = _draw_vignette(bg)
    img.paste(bg, (0, 0))

    # Sparkles layer
    sparkle_overlay = Image.new('RGBA', size, (0, 0, 0, 0))
    sparkle_draw = ImageDraw.Draw(sparkle_overlay)
    sparkle_count = 15 if tier == 'early' else (25 if tier == 'mid' else 40)
    _draw_sparkles(sparkle_draw, w, h, sparkle_count, tier)
    img = Image.alpha_composite(img, sparkle_overlay)

    # Main drawing layer
    overlay = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Load fonts
    try:
        font_huge = ImageFont.truetype(FONT_PATH, 140)
        font_large = ImageFont.truetype(FONT_PATH, 56)
        font_medium = ImageFont.truetype(FONT_PATH, 40)
        font_small = ImageFont.truetype(FONT_PATH, 32)
        font_tagline = ImageFont.truetype(FONT_PATH, 28)
    except OSError:
        font_huge = ImageFont.load_default()
        font_large = font_huge
        font_medium = font_huge
        font_small = font_huge
        font_tagline = font_huge

    # Vertical center of badge area
    cy = h // 2 if fmt == 'story' else h // 2
    cx = w // 2

    # Progress ring
    ring_radius = 220
    ring_thickness = 16 if tier == 'early' else (22 if tier == 'mid' else 24)
    _draw_ring(
        draw, (cx, cy - 30), ring_radius, ring_thickness, progress,
        colors['ring'], colors['ring_track'], colors['ring_glow'], tier,
    )

    # Day count number (centered in ring)
    day_text = f'{days:,}'
    bbox = draw.textbbox((0, 0), day_text, font=font_huge)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    # Shadow
    draw.text((cx - tw // 2 + 3, cy - 30 - th // 2 - 10 + 3), day_text,
              fill=(0, 0, 0, 50), font=font_huge)
    # Text
    draw.text((cx - tw // 2, cy - 30 - th // 2 - 10), day_text,
              fill=(255, 255, 255, 255), font=font_huge)

    # "days sober" label below the number
    sub_text = 'days sober'
    bbox = draw.textbbox((0, 0), sub_text, font=font_medium)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, cy - 30 + th // 2 + 5), sub_text,
              fill=(255, 255, 255, 180), font=font_medium)

    # Milestone label below the ring
    label = get_milestone_label(days)
    bbox = draw.textbbox((0, 0), label, font=font_large)
    tw = bbox[2] - bbox[0]
    label_y = cy - 30 + ring_radius + ring_thickness + 30
    draw.text((cx - tw // 2, label_y), label, fill=(255, 255, 255, 230), font=font_large)

    # Decorative line separator
    line_y = label_y + 70
    line_half = 60
    draw.line([(cx - line_half, line_y), (cx + line_half, line_y)],
              fill=(255, 255, 255, 100), width=2)

    # Tagline for early tier
    if colors.get('tagline'):
        tag_y = line_y + 20
        bbox = draw.textbbox((0, 0), colors['tagline'], font=font_tagline)
        tw = bbox[2] - bbox[0]
        draw.text((cx - tw // 2, tag_y), colors['tagline'],
                  fill=(255, 255, 255, 140), font=font_tagline)

    # Watermark at bottom
    watermark = 'MyRecoveryPal.com'
    bbox = draw.textbbox((0, 0), watermark, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw // 2, h - 100), watermark,
              fill=(255, 255, 255, 140), font=font_small)

    # Composite overlay onto image
    img = Image.alpha_composite(img, overlay)

    # Convert to RGB for PNG output
    final = img.convert('RGB')

    buffer = BytesIO()
    final.save(buffer, 'PNG', optimize=True)
    img_bytes = buffer.getvalue()

    cache.set(cache_key, img_bytes, 86400)
    return img_bytes
