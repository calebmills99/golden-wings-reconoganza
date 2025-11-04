#!/usr/bin/env python3
"""
EPUB to TXT/ODT (ODF) converter

Usage examples:
  - Convert to TXT (auto output name):
      python convert_epub.py path\to\book.epub --txt

  - Convert to ODT (OpenDocument Text):
      python convert_epub.py path\to\book.epub --odt

  - Explicit output path:
      python convert_epub.py path\to\book.epub --txt -o out\book.txt

This tool prefers a pure-Python path if optional libraries are installed, and
falls back to Calibre's ebook-convert if available. If neither path is
available, it will print clear installation guidance.

Optional Python dependencies:
  - ebooklib (parse EPUB)
  - beautifulsoup4 (clean HTML to text)
  - odfpy (for ODT output)

Fallback external tool:
  - Calibre ebook-convert: https://calibre-ebook.com/download
    Common Windows paths:
      C:\\Program Files\\Calibre\\ebook-convert.exe
      C:\\Program Files (x86)\\Calibre2\\ebook-convert.exe
"""
from __future__ import annotations
import argparse
import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# Try optional libs
EBOOKLIB = None
BS4 = None
ODFPY = None
try:
    import ebooklib  # type: ignore
    from ebooklib import epub  # type: ignore
    EBOOKLIB = epub
except Exception:
    EBOOKLIB = None
try:
    from bs4 import BeautifulSoup  # type: ignore
    BS4 = BeautifulSoup
except Exception:
    BS4 = None
try:
    from odf.opendocument import OpenDocumentText  # type: ignore
    from odf.text import P, H
    ODFPY = True
except Exception:
    ODFPY = None


def find_ebook_convert() -> Optional[str]:
    """Find Calibre's ebook-convert on PATH or common Windows install paths."""
    exe = shutil.which('ebook-convert')
    if exe:
        return exe
    candidates = [
        r"C:\\Program Files\\Calibre\\ebook-convert.exe",
        r"C:\\Program Files (x86)\\Calibre2\\ebook-convert.exe",
        r"C:\\Program Files\\Calibre2\\ebook-convert.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def derive_output(input_path: Path, to_ext: str) -> Path:
    stem = input_path.stem
    return input_path.with_name(f"{stem}{to_ext}")


def html_to_text(html: str) -> str:
    if BS4 is None:
        # Fallback: extremely naive stripping
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    soup = BS4(html, 'html.parser')
    # Remove scripts/styles
    for tag in soup(['script', 'style']):
        tag.extract()
    text = soup.get_text(separator='\n')
    # Collapse excessive whitespace lines
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def convert_with_python(input_path: Path, out_txt: Optional[Path], out_odt: Optional[Path]) -> Tuple[Optional[Path], Optional[Path]]:
    """Convert using ebooklib/bs4/odfpy if available.
    Returns the produced paths (txt_path, odt_path)."""
    if EBOOKLIB is None:
        return (None, None)

    try:
        book = EBOOKLIB.read_epub(str(input_path))
    except Exception as e:
        # DRM or parse error
        print(f"⚠️  Unable to parse EPUB with ebooklib: {e}")
        return (None, None)

    # Collect spine order content
    spine_items = []
    try:
        spine = [item for k, item in book.spine]
        # However ebooklib returns ids; map to docs
        id_to_item = {item.get_id(): item for item in book.get_items()}
        for idref in [k for k, _ in book.spine]:
            it = id_to_item.get(idref)
            if it is not None:
                spine_items.append(it)
    except Exception:
        pass

    if not spine_items:
        # Fallback: take all document items
        from ebooklib import ITEM_DOCUMENT  # type: ignore
        spine_items = [it for it in book.get_items() if it.get_type() == ITEM_DOCUMENT]

    full_text_parts: list[str] = []
    for it in spine_items:
        try:
            content = it.get_content().decode('utf-8', errors='ignore')
            txt = html_to_text(content)
            if txt:
                full_text_parts.append(txt)
        except Exception:
            continue
    full_text = "\n\n".join(full_text_parts).strip()

    produced_txt: Optional[Path] = None
    produced_odt: Optional[Path] = None

    if out_txt:
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(full_text, encoding='utf-8')
        produced_txt = out_txt
        print(f"📝 Wrote TXT: {out_txt}")

    if out_odt:
        if ODFPY:
            doc = OpenDocumentText()
            # Title (if any)
            title = getattr(book, 'title', None) or input_path.stem
            if title:
                doc.text.addElement(H(outlinelevel=1, text=title))
            for para in full_text.split('\n\n'):
                if para.strip():
                    doc.text.addElement(P(text=para.strip()))
            out_odt.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(out_odt))
            produced_odt = out_odt
            print(f"📄 Wrote ODT: {out_odt}")
        else:
            print("ℹ️  odfpy not installed; cannot create ODT via Python path.")

    return (produced_txt, produced_odt)


def convert_with_calibre(input_path: Path, out_path: Path, fmt: str) -> Optional[Path]:
    exe = find_ebook_convert()
    if not exe:
        return None
    try:
        cmd = [exe, str(input_path), str(out_path)]
        print(f"⚙️  Using Calibre ebook-convert: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        if out_path.exists():
            print(f"✅ Wrote {fmt.upper()}: {out_path}")
            return out_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Calibre conversion failed: {e}")
    return None


def main():
    p = argparse.ArgumentParser(description='Convert EPUB to TXT or ODT (ODF).')
    p.add_argument('epub_path', help='Path to .epub file')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--txt', action='store_true', help='Output TXT')
    g.add_argument('--odt', action='store_true', help='Output ODT (OpenDocument Text)')
    p.add_argument('-o', '--output', help='Output file path (optional)')
    args = p.parse_args()

    in_path = Path(args.epub_path)
    if not in_path.exists():
        print(f"❌ Input not found: {in_path}")
        sys.exit(1)
    if in_path.suffix.lower() != '.epub':
        print("❌ Input must be an .epub file")
        sys.exit(1)

    target_ext = '.txt' if args.txt else '.odt'
    out_path = Path(args.output) if args.output else derive_output(in_path, target_ext)

    # Attempt pure-Python first
    want_txt = args.txt
    want_odt = args.odt
    py_txt = out_path if want_txt else None
    py_odt = out_path if want_odt else None

    produced_txt, produced_odt = convert_with_python(in_path, py_txt, py_odt)

    if (want_txt and produced_txt) or (want_odt and produced_odt):
        sys.exit(0)

    # Fallback to Calibre
    fallback = convert_with_calibre(in_path, out_path, 'txt' if want_txt else 'odt')
    if fallback:
        sys.exit(0)

    # Guidance
    print("\n---")
    print("Unable to convert with the available methods.")
    if EBOOKLIB is None or BS4 is None or (want_odt and not ODFPY):
        print("• Python path missing deps. Install optional deps:")
        print("  pip install ebooklib beautifulsoup4" + (" odfpy" if want_odt else ""))
    if find_ebook_convert() is None:
        print("• Install Calibre to enable fallback converter:")
        print("  https://calibre-ebook.com/download")
        print("  Then ensure ebook-convert is on PATH, or installed at:")
        print("   C:\\Program Files\\Calibre\\ebook-convert.exe or C:\\Program Files (x86)\\Calibre2\\ebook-convert.exe")
    sys.exit(2)


if __name__ == '__main__':
    main()
