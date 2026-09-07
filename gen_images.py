#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HERO IMAGE GENERATOR  —  Google Imagen via the Gemini API.

    export GEMINI_API_KEY=...            # or GOOGLE_API_KEY
    python3 gen_images.py --dry-run      # print the prompts, call nothing
    python3 gen_images.py                # generate all six heroes into img/
    python3 gen_images.py --only hero-home
    python3 gen_images.py --model imagen-4.0-ultra-generate-001

For each hero the theme expects three files in img/ at 1376x602:
    hero-<slug>.jpg  hero-<slug>.webp  hero-<slug>.avif
Imagen returns 16:9, so each image is generated at 2K, centre-cropped to
the hero ratio and resized. Existing files are skipped unless --force.

Requires: pip install google-genai pillow pillow-avif-plugin
"""
import io, os, sys, argparse

W, H = 1376, 602            # what hero() in build_site.py declares on the <img>
OUT  = 'img'

# Shared style so all six read as one set. Matches the theme palette: navy
# shadows, warm gold light, sage greens and cream limestone.
STYLE = ("Photorealistic architectural photograph, Central Texas Hill Country near Austin, "
         "warm late-afternoon golden light, deep blue-navy shadows, cream and buff limestone, "
         "sage-green live oaks and cedar, wide 16:9 composition with the wall as the subject, "
         "shot on a full-frame camera with a 35mm lens, natural colour, no people, no faces, "
         "no text, no logos, no watermark, no signage.")

PROMPTS = {
 "hero-home":
   "A finished dry-stacked cream limestone block retaining wall terracing the sloped back yard of an "
   "Austin home, two tiers with a level lawn between them, mature live oak leaning over the upper "
   "tier, Hill Country ridge in the background.",
 "hero-retaining-wall-installation":
   "A new segmental block retaining wall under construction on a residential lot: compacted crushed "
   "limestone base, first courses set level, a layer of black geogrid mesh being laid back into the "
   "fill, gravel drainage column behind the wall, small excavator parked at the edge of the cut.",
 "hero-retaining-wall-repair":
   "An old limestone retaining wall in an established Austin neighbourhood leaning and bulging outward "
   "with a horizontal crack and water staining, a fresh trench excavated behind it exposing the soil, "
   "new perforated drain pipe and gravel ready beside it.",
 "hero-retaining-wall-construction":
   "An engineered poured-concrete retaining wall being built on a steep hillside lot: reinforcing "
   "steel cage tied and standing inside timber formwork on a concrete footing, cut limestone rock face "
   "behind it, surveyor's stakes and string line, a house frame above on the ridge.",
 "hero-retaining-walls":
   "Three retaining wall systems side by side along a Hill Country garden path: dry-stacked cream "
   "limestone, a wire gabion basket filled with limestone rubble, and a treated timber wall, "
   "planted with agave and native grasses, contrasting textures in warm light.",
 "hero-hillside-retaining-walls":
   "Tiered limestone retaining walls stepping down a steep wooded hillside above a limestone creek "
   "canyon west of Austin, cedar and live oak between the terraces, a modern house perched on the "
   "ridge above, long view down the canyon in golden light.",
}

def crop_resize(png_bytes):
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert('RGB')
    w, h = im.size
    target = W / H
    if w / h > target:            # too wide: trim sides
        nw = int(h * target); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
    else:                         # too tall: trim top/bottom, keep slightly above centre
        nh = int(w / target); y = int((h - nh) * 0.45); im = im.crop((0, y, w, y + nh))
    return im.resize((W, H), Image.LANCZOS)

def save_all(im, stem):
    import pillow_avif  # noqa: F401  (registers the AVIF encoder)
    os.makedirs(OUT, exist_ok=True)
    im.save(os.path.join(OUT, stem + '.jpg'),  'JPEG', quality=82, optimize=True, progressive=True)
    im.save(os.path.join(OUT, stem + '.webp'), 'WEBP', quality=80, method=6)
    im.save(os.path.join(OUT, stem + '.avif'), 'AVIF', quality=58, speed=4)

def generate(client, model, prompt):
    from google.genai import types
    r = client.models.generate_images(
        model=model, prompt=prompt,
        config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio='16:9',
                                          image_size='2K', output_mime_type='image/png',
                                          person_generation='dont_allow'))
    if not r.generated_images:
        raise RuntimeError('no image returned (prompt may have been filtered)')
    return r.generated_images[0].image.image_bytes

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='imagen-4.0-generate-001')
    ap.add_argument('--only', action='append', help='hero stem, repeatable')
    ap.add_argument('--force', action='store_true', help='regenerate existing files')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    todo = [k for k in PROMPTS if not a.only or k in a.only]
    if a.dry_run:
        for k in todo: print('\n%s\n  %s %s' % (k, PROMPTS[k], STYLE))
        return
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key: sys.exit('set GEMINI_API_KEY (or GOOGLE_API_KEY) first')
    from google import genai
    client = genai.Client(api_key=key)
    for k in todo:
        if not a.force and all(os.path.exists(os.path.join(OUT, k + e)) for e in ('.jpg', '.webp', '.avif')):
            print('skip  %s (exists)' % k); continue
        print('gen   %s ...' % k, end='', flush=True)
        png = generate(client, a.model, PROMPTS[k] + ' ' + STYLE)
        save_all(crop_resize(png), k)
        print(' ok  ->  %s/%s.{jpg,webp,avif}' % (OUT, k))
    print('\nDone. Rebuild is not needed: build_site.py already references these paths.')

if __name__ == '__main__':
    main()
