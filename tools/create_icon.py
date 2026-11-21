"""Regenerate the Windows ICO from the supplied blue musical-note icon."""
from pathlib import Path
from PIL import Image
base = Path(__file__).resolve().parents[1] / 'assets'
image = Image.open(base/'icon.png').convert('RGBA')
image.save(base/'icon.ico', format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(base/'icon.ico')
