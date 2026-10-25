"""Optional development preview: python -m hardware.render_cue_sheet.

Requires Pillow on the development computer. This is not used by the Pi client.
Raster symbols are scaled with nearest-neighbor interpolation to show the actual pixels.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(output=None):
    from PIL import Image, ImageDraw, ImageFont
    assets = json.loads((ROOT / 'hardware/oled-assets.json').read_text())['bitmaps']
    cues = json.loads((ROOT / 'audio/cue-catalog.json').read_text())['cues']
    sheet = Image.new('RGB', (1120, ((len(cues)+9)//10)*180), '#0b0b0a')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=14)
    for index, cue in enumerate(cues):
        x, y = (index % 10)*112, (index // 10)*180
        icon = Image.new('RGB', (32, 32), 'black')
        for yy, row in enumerate(assets[cue['icon_id']]):
            for xx, pixel in enumerate(row):
                if pixel == '1':
                    icon.putpixel((xx, yy), (244, 242, 234))
        sheet.paste(icon.resize((96, 96), Image.Resampling.NEAREST), (x+8, y+8))
        lines = ['']
        for word in cue['label'].split():
            candidate = (lines[-1]+' '+word).strip()
            if draw.textlength(candidate, font=font) > 108:
                lines.append(word)
            else:
                lines[-1] = candidate
        for row, text in enumerate(lines):
            draw.text((x+4, y+112+row*17), text, font=font, fill='#f4f2ea')
    output = output or ROOT / 'docs/images/cues-50.png'
    sheet.save(output)
    return output


if __name__ == '__main__':
    print(build())
