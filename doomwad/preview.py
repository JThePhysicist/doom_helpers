"""Self-contained read-only HTML atlas preview with geometry and pixel diffs."""
import base64
import html
from io import BytesIO

from PIL import ImageChops

from .atlas import iter_manifest_sprites
from .manifest import validate_manifest
from .storage import atomic_write


def _image(image):
    stream=BytesIO(); image.save(stream,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()


def preview_html(manifest, pages, baseline=None):
    validate_manifest(manifest,pages)
    original = {}
    if baseline is not None:
        original = {name:image for name,image,_,_ in iter_manifest_sprites(*baseline)}
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>doomwad atlas preview</title>',
           '<style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:16px;background:#f5f7fb;color:#182c42}svg{width:100%;background:#ddd}img{image-rendering:pixelated;max-width:100%}article{display:inline-block;vertical-align:top;padding:16px;margin:8px;background:white;border:1px solid #bbb}button{margin:5px}.swatch{display:inline-block;width:22px;height:22px}table{border-collapse:collapse}td,th{padding:6px;border:1px solid #bbb}</style>',
           '<h1>Atlas preview</h1><p>Read-only: this document changes no WAD, PNG, or manifest files. Cyan: crop bounds. Orange: editing allocation. Red: anchor. Transparent pixels use a checkerboard.</p>',
           '<button onclick="document.querySelectorAll(\'.overlay\').forEach(e=>e.hidden=!e.hidden)">Toggle overlays</button>']
    for i,page in enumerate(pages):
        size=manifest['atlas_size']
        parts.append(f'<h2>Page {i}</h2><svg viewBox="0 0 {size} {size}" role="img" aria-label="Atlas page {i}"><image width="{size}" height="{size}" href="{_image(page)}"/>')
        for e in manifest['sprites']:
            if e['page']!=i: continue
            ax,ay,aw,ah=e.get('allocation',[e['x'],e['y'],e['width'],e['height']])
            anchor_x=e['x']+e['left_offset'];anchor_y=e['y']+e['top_offset']
            parts.append(f'<g class="overlay"><rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" fill="none" stroke="orange"/><rect x="{e["x"]}" y="{e["y"]}" width="{e["width"]}" height="{e["height"]}" fill="none" stroke="cyan"/><circle cx="{anchor_x}" cy="{anchor_y}" r="2" fill="red"/><title>{html.escape(e["name"])}</title></g>')
        parts.append('</svg>')
    parts.append('<h2>Sprites</h2><p>Eight-character names may share one patch across two mirrored frame/rotation uses; names are preserved exactly.</p>')
    for name,image,left,top in iter_manifest_sprites(manifest,pages):
        parts.append(f'<article><h3>{html.escape(name)}</h3><img alt="{html.escape(name,quote=True)}" src="{_image(image)}"><p>{image.width}×{image.height}; anchor ({left}, {top})</p>')
        if name in original:
            before=original[name]
            if before.size!=image.size: parts.append('<p>Baseline dimensions differ.</p>')
            else:
                diff=ImageChops.difference(before,image)
                changed=sum(any(pixel) for pixel in diff.getdata())
                parts.append(f'<p>{changed} changed pixels vs baseline</p><img alt="Pixel difference" src="{_image(diff.convert("RGB"))}">')
        parts.append('</article>')
    parts.append('<h2>Embedded palette</h2>')
    for i,(r,g,b) in enumerate(manifest['palette']):
        parts.append(f'<span class="swatch" title="Index {i}: {r},{g},{b}" style="background:rgb({r},{g},{b})"></span>')
    return ''.join(parts)+'</html>'


def write_preview(path, manifest, pages, baseline=None, *, overwrite=False):
    atomic_write(path,preview_html(manifest,pages,baseline).encode(),overwrite=overwrite)
