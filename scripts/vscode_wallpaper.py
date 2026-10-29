#!/usr/bin/env python3
"""Prepare or apply one scoped, static editor wallpaper to the installed VS Code."""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

BEGIN = '/* ORBITE WALLPAPER BEGIN */'
END = '/* ORBITE WALLPAPER END */'

def render(original, wallpaper):
    original = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END), '', original, flags=re.S).rstrip() + '\n'
    if wallpaper is None:
        return original
    encoded = base64.b64encode(wallpaper.read_bytes()).decode('ascii')
    return original + f'''\n{BEGIN}
/* The image must be painted on the editor itself: .editor-container is opaque in VS Code. */
.monaco-workbench .part.editor .editor-group-container,
.monaco-workbench .part.editor .editor-container {{
  /* A single veil: 7% of the source image under text, 22% at the right edge.
     Paint locally in each split editor, avoiding opaque intermediate panels. */
  background: linear-gradient(90deg,
    rgba(16,11,27,.93) 0%,
    rgba(16,11,27,.93) 60%,
    rgba(16,11,27,.87) 80%,
    rgba(16,11,27,.78) 100%), url("data:image/png;base64,{encoded}") right center / cover no-repeat !important;
}}
.monaco-workbench .part.editor .editor-instance > .monaco-editor,
.monaco-workbench .part.editor .editor-instance > .monaco-editor > .overflow-guard,
.monaco-workbench .part.editor .editor-instance > .monaco-editor .monaco-editor-background,
.monaco-workbench .part.editor .editor-instance > .monaco-editor > .overflow-guard > .margin {{
  background: transparent !important;
}}
{END}\n'''

def atomic_write(path, data):
    stat = path.stat()
    fd, temp = tempfile.mkstemp(prefix='.orbite-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.chmod(temp, stat.st_mode & 0o777)
        os.chown(temp, stat.st_uid, stat.st_gid)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-dir', required=True, type=Path)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--backup-dir', required=True, type=Path)
    parser.add_argument('--remove', action='store_true')
    args = parser.parse_args()
    css = args.app_dir / 'out/vs/workbench/workbench.desktop.main.css'
    product_path = args.app_dir / 'product.json'
    image = None if args.remove else args.image
    if image and (not image.is_file() or image.suffix.lower() != '.png'):
        raise SystemExit('Une image PNG locale est nécessaire.')
    original_css, original_product = css.read_bytes(), product_path.read_bytes()
    product = json.loads(original_product)
    key = 'vs/workbench/workbench.desktop.main.css'
    if key not in product.get('checksums', {}):
        raise SystemExit('Format Code incompatible : aucun fichier modifié.')
    css_bytes = render(original_css.decode(), image).encode()
    product['checksums'][key] = base64.b64encode(hashlib.sha256(css_bytes).digest()).decode().rstrip('=')
    product_bytes = (json.dumps(product, indent='\t') + '\n').encode()
    if css_bytes == original_css and product_bytes == original_product:
        print('Fond VS Code déjà à jour.'); return
    # Back up each distinct application version/content before changing it.
    target = args.backup_dir / hashlib.sha256(original_css + original_product).hexdigest()[:20]
    target.mkdir(parents=True, exist_ok=True)
    for source in [css, product_path]:
        destination = target / source.name
        if not destination.exists(): shutil.copy2(source, destination)
    atomic_write(css, css_bytes)
    try:
        atomic_write(product_path, product_bytes)
    except Exception:
        atomic_write(css, original_css)
        raise
    print('Fond VS Code ' + ('retiré.' if args.remove else 'installé.'))

if __name__ == '__main__':
    main()
