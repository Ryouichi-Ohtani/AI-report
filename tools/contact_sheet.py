"""Make a compact visual-QA contact sheet from rendered PDF pages."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
args = parser.parse_args()
paths = sorted(args.directory.glob('page-*.png'))
width, height, columns = 360, 535, 3
sheet = Image.new('RGB', (columns * width, ((len(paths) + columns - 1) // columns) * height), '#d8dde0')
draw = ImageDraw.Draw(sheet)
for i, path in enumerate(paths):
    image = Image.open(path).convert('RGB')
    image.thumbnail((width - 12, height - 25))
    x, y = (i % columns) * width, (i // columns) * height
    sheet.paste(image, (x + 6, y + 20))
    draw.text((x + 8, y + 4), path.stem, fill='black')
sheet.save(args.directory / 'contact-sheet.png')
