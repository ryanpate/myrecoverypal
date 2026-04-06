"""Generate gradient background images for milestone sharing."""
import os
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw


GRADIENTS = {
    'early': {'top': (30, 77, 139), 'bottom': (77, 184, 232)},
    'mid': {'top': (64, 145, 108), 'bottom': (82, 183, 136)},
    'long': {'top': (102, 51, 153), 'bottom': (118, 75, 162)},
}

FORMATS = {
    'story': (1080, 1920),
    'square': (1080, 1080),
}


class Command(BaseCommand):
    help = 'Generate gradient background PNGs for milestone images'

    def handle(self, *args, **options):
        output_dir = os.path.join('static', 'images', 'milestones')
        os.makedirs(output_dir, exist_ok=True)

        for name, colors in GRADIENTS.items():
            for fmt, (w, h) in FORMATS.items():
                img = Image.new('RGB', (w, h))
                draw = ImageDraw.Draw(img)

                top = colors['top']
                bottom = colors['bottom']

                for y in range(h):
                    ratio = y / h
                    r = int(top[0] + (bottom[0] - top[0]) * ratio)
                    g = int(top[1] + (bottom[1] - top[1]) * ratio)
                    b = int(top[2] + (bottom[2] - top[2]) * ratio)
                    draw.line([(0, y), (w, y)], fill=(r, g, b))

                filename = f'bg-{name}-{fmt}.png'
                filepath = os.path.join(output_dir, filename)
                img.save(filepath, 'PNG', optimize=True)
                self.stdout.write(f'  Created {filepath} ({w}x{h})')

        self.stdout.write(self.style.SUCCESS(
            f'Generated {len(GRADIENTS) * len(FORMATS)} backgrounds'
        ))
