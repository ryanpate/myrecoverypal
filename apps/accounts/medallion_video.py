"""Animated medallion: a 5-second 1080x1920 MP4 for Reels / TikTok / Stories.

Timeline: the day count ticks up (with a gentle zoom-in), crossfades to the
design exactly as the buyer made it, then a light sweep glints across the
metal and it holds. Rendered with Pillow; encoded with the ffmpeg binary that
ships inside the imageio-ffmpeg wheel (no system package needed).
"""
import hashlib
import os
import tempfile

from django.core.cache import cache
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from .milestone_image import milestone_badge_image

WIDTH, HEIGHT = 1080, 1920
MEDALLION = 960
FPS = 30
DURATION = 5.0
COUNT_END = 2.2      # count-up finishes
FADE_END = 2.6       # crossfade to the buyer's own text format is done
SHINE_START, SHINE_END = 3.0, 4.2

CACHE_SECONDS = 7 * 24 * 3600


def _ease_out(t):
    return 1 - (1 - t) ** 3


def generate_story_video(days, **badge_kwargs):
    """Return MP4 bytes for this medallion (cached; a render takes a few seconds)."""
    key_src = f'{days}_' + '_'.join(f'{k}={badge_kwargs[k]}' for k in sorted(badge_kwargs))
    cache_key = f'medallion_video_v1_{hashlib.md5(key_src.encode()).hexdigest()}'
    cached = cache.get(cache_key)
    if cached:
        return cached
    video = _render_video(days, badge_kwargs)
    cache.set(cache_key, video, CACHE_SECONDS)
    return video


def _badge(days, badge_kwargs, **overrides):
    opts = {**badge_kwargs, 'size': MEDALLION, 'watermark': False, **overrides}
    return milestone_badge_image(days, **opts)


def _shine_strip():
    """A soft diagonal light band on a strip 3x the medallion's width."""
    strip = Image.new('L', (MEDALLION * 3, MEDALLION), 0)
    band = MEDALLION // 5
    x0 = MEDALLION + MEDALLION // 2
    ImageDraw.Draw(strip).polygon(
        [(x0, 0), (x0 + band, 0), (x0 + band - MEDALLION // 2, MEDALLION),
         (x0 - MEDALLION // 2, MEDALLION)], fill=120)
    return strip.filter(ImageFilter.GaussianBlur(MEDALLION // 30))


def _coin_mask():
    """Circle covering the coin, so the glint doesn't cross the velvet corners."""
    mask = Image.new('L', (MEDALLION, MEDALLION), 0)
    inset = int(MEDALLION * 0.03)
    ImageDraw.Draw(mask).ellipse((inset, inset, MEDALLION - inset, MEDALLION - inset), fill=255)
    return mask


def _render_video(days, badge_kwargs):
    import imageio_ffmpeg

    final = _badge(days, badge_kwargs)

    background = final.resize((HEIGHT, HEIGHT), Image.BILINEAR)
    left = (HEIGHT - WIDTH) // 2
    background = background.crop((left, 0, left + WIDTH, HEIGHT))
    background = ImageEnhance.Brightness(background.filter(ImageFilter.GaussianBlur(40))).enhance(0.45)

    strip, coin = _shine_strip(), _coin_mask()
    white = Image.new('RGB', (MEDALLION, MEDALLION), (255, 255, 255))
    count_frames = {}
    last_count = None

    fd, path = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    try:
        writer = imageio_ffmpeg.write_frames(
            path, (WIDTH, HEIGHT), fps=FPS, codec='libx264', macro_block_size=8,
            pix_fmt_in='rgb24', pix_fmt_out='yuv420p', quality=None,
            output_params=['-crf', '23', '-preset', 'veryfast', '-movflags', '+faststart'],
        )
        writer.send(None)
        for i in range(int(DURATION * FPS)):
            t = i / FPS

            if t < COUNT_END:
                n = max(1, round(days * _ease_out(t / COUNT_END)))
                if n not in count_frames:
                    count_frames[n] = _badge(n, badge_kwargs, time_format='days')
                medallion = last_count = count_frames[n]
            elif t < FADE_END:
                medallion = Image.blend(last_count or final, final,
                                        (t - COUNT_END) / (FADE_END - COUNT_END))
            else:
                medallion = final

            if SHINE_START <= t <= SHINE_END:
                progress = (t - SHINE_START) / (SHINE_END - SHINE_START)
                offset = int(MEDALLION * 2 * (1 - progress))
                glint = ImageChops.multiply(strip.crop((offset, 0, offset + MEDALLION, MEDALLION)), coin)
                medallion = Image.composite(white, medallion, glint)

            zoom = 0.88 + 0.12 * _ease_out(min(1.0, t / FADE_END))
            side = int(MEDALLION * zoom)
            frame = background.copy()
            frame.paste(medallion.resize((side, side), Image.BILINEAR),
                        ((WIDTH - side) // 2, (HEIGHT - side) // 2))
            writer.send(frame.tobytes())
        writer.close()
        with open(path, 'rb') as f:
            return f.read()
    finally:
        os.remove(path)
