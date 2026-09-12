"""
Shrink blog featured images to web size, in place.

Web spec for daniks-ai-ads/src/assets/blog/*.jpg:
  - max 1200 px wide (height follows the aspect ratio)
  - progressive JPEG, 4:2:0 chroma, metadata stripped
  - quality starts at 82 and steps down (never below 70) until the file
    is under 250 KB

fal.ai returns a 2K render (2752x1536, 0.5-2.5 MB). The blog only ever shows
the image at ~360-600 px wide (listing cards) and as og:image (1200 px), so
anything bigger is wasted bandwidth and repo bloat.

Usage:
    python3 data_sources/modules/image_optimizer.py FILE_OR_DIR [more...]
    python3 data_sources/modules/image_optimizer.py --check FILE [more...]   # exit 1 if any file is over spec
    python3 data_sources/modules/image_optimizer.py --force FILE             # re-encode even if already within spec

Requires Pillow (python3 -m pip install Pillow). Falls back to macOS `sips`
when Pillow is missing.
"""

import argparse
import io
import os
import shutil
import subprocess
import sys

MAX_WIDTH = 1200
MAX_BYTES = 250_000
START_QUALITY = 82
MIN_QUALITY = 70
QUALITY_STEP = 4
JPEG_EXTS = {".jpg", ".jpeg"}


def _image_size(path):
    """Return (width, height) or (None, None) if it can't be read."""
    try:
        from PIL import Image

        with Image.open(path) as im:
            return im.size
    except ImportError:
        try:
            out = subprocess.run(
                ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                capture_output=True, text=True, check=True,
            ).stdout
            vals = {}
            for line in out.splitlines():
                line = line.strip()
                for key in ("pixelWidth", "pixelHeight"):
                    if line.startswith(key + ":"):
                        vals[key] = int(line.split(":", 1)[1])
            return vals.get("pixelWidth"), vals.get("pixelHeight")
        except Exception:
            return None, None
    except Exception:
        return None, None


def check_within_spec(path, max_width=MAX_WIDTH, max_bytes=MAX_BYTES):
    """Return (ok, reason) for a single file."""
    size = os.path.getsize(path)
    w, h = _image_size(path)
    problems = []
    if w is not None and w > max_width:
        problems.append(f"{w}x{h} px is wider than {max_width} px")
    if size > max_bytes:
        problems.append(f"{size / 1024:.0f} KB is over {max_bytes / 1024:.0f} KB")
    return (not problems), "; ".join(problems)


def _optimize_with_pillow(path, max_width, max_bytes, force):
    from PIL import Image, ImageOps

    before = os.path.getsize(path)
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        w, h = im.size
        needs_resize = w > max_width
        if not needs_resize and before <= max_bytes and not force:
            return {"before": before, "after": before, "width": w, "height": h,
                    "quality": None, "changed": False, "method": "pillow"}
        if needs_resize:
            new_h = max(1, round(h * max_width / w))
            im = im.resize((max_width, new_h), Image.LANCZOS)
        if im.mode != "RGB":
            im = im.convert("RGB")
        quality = START_QUALITY
        while True:
            buf = io.BytesIO()
            # subsampling=2 -> 4:2:0; no exif/icc passed -> metadata stripped
            im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True, subsampling=2)
            if buf.tell() <= max_bytes or quality <= MIN_QUALITY:
                break
            quality -= QUALITY_STEP
        out_w, out_h = im.size
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return {"before": before, "after": os.path.getsize(path), "width": out_w, "height": out_h,
            "quality": quality, "changed": True, "method": "pillow"}


def _optimize_with_sips(path, max_width, max_bytes, force):
    """macOS fallback when Pillow isn't installed."""
    if not shutil.which("sips"):
        raise RuntimeError("Neither Pillow nor `sips` is available; run: python3 -m pip install Pillow")
    before = os.path.getsize(path)
    w, h = _image_size(path)
    if w is not None and w <= max_width and before <= max_bytes and not force:
        return {"before": before, "after": before, "width": w, "height": h,
                "quality": None, "changed": False, "method": "sips"}
    quality = START_QUALITY
    while True:
        cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(quality)]
        if w is not None and w > max_width:
            cmd += ["--resampleWidth", str(max_width)]
        subprocess.run(cmd + [path, "--out", path], capture_output=True, check=True)
        if os.path.getsize(path) <= max_bytes or quality <= MIN_QUALITY:
            break
        quality -= QUALITY_STEP
    out_w, out_h = _image_size(path)
    return {"before": before, "after": os.path.getsize(path), "width": out_w, "height": out_h,
            "quality": quality, "changed": True, "method": "sips"}


def optimize_for_web(path, max_width=MAX_WIDTH, max_bytes=MAX_BYTES, force=False):
    """Resize/recompress a JPEG in place. Returns a dict describing what happened."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in JPEG_EXTS:
        raise ValueError(f"{path}: only .jpg/.jpeg are supported (got {ext or 'no extension'})")
    try:
        import PIL  # noqa: F401
    except ImportError:
        return _optimize_with_sips(path, max_width, max_bytes, force)
    return _optimize_with_pillow(path, max_width, max_bytes, force)


def _expand(paths):
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                if os.path.splitext(name)[1].lower() in JPEG_EXTS:
                    yield os.path.join(p, name)
        else:
            yield p


def main():
    parser = argparse.ArgumentParser(description="Shrink blog featured JPEGs to web size (in place)")
    parser.add_argument("paths", nargs="+", help="JPEG files or directories")
    parser.add_argument("--check", action="store_true", help="Only report; exit 1 if any file is over spec")
    parser.add_argument("--force", action="store_true", help="Re-encode even if already within spec")
    parser.add_argument("--max-width", type=int, default=MAX_WIDTH)
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    args = parser.parse_args()

    files = list(_expand(args.paths))
    if not files:
        print("No JPEG files found.")
        sys.exit(1)

    failures = 0
    total_before = total_after = 0
    for path in files:
        if not os.path.isfile(path):
            print(f"MISSING  {path}")
            failures += 1
            continue
        if args.check:
            ok, reason = check_within_spec(path, args.max_width, args.max_bytes)
            w, h = _image_size(path)
            size = os.path.getsize(path)
            print(f"{'OK     ' if ok else 'TOO BIG'}  {size / 1024:7.0f} KB  {w}x{h}  {path}" + (f"  ({reason})" if reason else ""))
            failures += 0 if ok else 1
            continue
        try:
            r = optimize_for_web(path, args.max_width, args.max_bytes, args.force)
        except Exception as e:  # keep going, report at the end
            print(f"ERROR    {path}: {e}")
            failures += 1
            continue
        total_before += r["before"]
        total_after += r["after"]
        if r["changed"]:
            print(f"SHRUNK   {r['before'] / 1024:7.0f} KB -> {r['after'] / 1024:5.0f} KB  {r['width']}x{r['height']}  q{r['quality']}  {path}")
        else:
            print(f"KEPT     {r['before'] / 1024:7.0f} KB            {r['width']}x{r['height']}        {path}")

    if not args.check and len(files) > 1:
        print(f"\nTotal: {total_before / 1024 / 1024:.1f} MB -> {total_after / 1024 / 1024:.1f} MB across {len(files)} files")
    if failures:
        print(f"\n{failures} file(s) failed or are over spec.")
        sys.exit(1)


if __name__ == "__main__":
    main()
