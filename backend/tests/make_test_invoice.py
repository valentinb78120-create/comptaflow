"""Génère une image de facture de test pour valider le fallback Tesseract."""
from PIL import Image, ImageDraw, ImageFont

OUT = "/tmp/facture_engie.png"

img = Image.new("RGB", (1200, 800), "white")
d = ImageDraw.Draw(img)
try:
    font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
except OSError:
    font_big = font = ImageFont.load_default()

d.text((60, 50), "ENGIE SA", font=font_big, fill="black")
d.text((60, 140), "FACTURE N 2026-0042", font=font, fill="black")
d.text((60, 200), "Date de facture : 02/06/2026", font=font, fill="black")
d.text((60, 320), "Montant HT : 80,00 EUR", font=font, fill="black")
d.text((60, 380), "TVA 20% : 16,00 EUR", font=font, fill="black")
d.text((60, 440), "Montant TTC : 96,00 EUR", font=font, fill="black")

img.save(OUT)
print(f"image creee: {OUT}")
