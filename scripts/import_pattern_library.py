#!/usr/bin/env python3
"""
import_pattern_library.py — bulk-import the Pattern Library .docx into the
patterns DB table at status='draft'.

The Pattern Library is a Google Docs export with a consistent shape:
  Heading 1 = section          ("Holes", "Holes+", "High Complexity", ...)
  Heading 2 = pattern          ("1 D-Pattern / 221-Hole", "3 P-Pattern / 422-Hole", ...)
  Heading 3 = variant          ("1.1 D-Pattern Classic", "1.2 D Pattern / Start-Extension / 23-221", ...)
  Heading 4+ = sub-summary     (folded into parent body as Markdown)

Each pattern body typically contains "Depth: N" and "Difficulty: A".
Embedded images (157 of them) are extracted to --image-dir, named after the
slug, and the first one is set as the row's board_image_url. Additional images
are appended to the body as Markdown image refs so editors can see them all
before deciding how to render the pattern with a JSON grid later.

Everything is imported as status='draft' so the wiki stays empty in public
until you publish each entry from /admin/patterns.

Usage:
    # See what would happen, no DB or disk writes:
    python3 scripts/import_pattern_library.py --docx ./Pattern-Library.docx --dry-run

    # Real import on the server (run as the ubuntu user):
    python3 scripts/import_pattern_library.py \\
        --docx /home/ubuntu/git/minesweeper.org/Pattern-Library.docx \\
        --image-dir /home/ubuntu/git/minesweeper.org/static/img/patterns \\
        --editor-email richard.cross@enlyt.io

    # Re-import after the docx changes (overwrites + saves a revision):
    python3 scripts/import_pattern_library.py --docx ./Pattern-Library.docx --update-existing

Dependencies:
    pip install python-docx
"""
import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imported lazily inside import_to_db() so --dry-run works without DB creds.

try:
    from docx import Document
    from docx.oxml.ns import qn
except ImportError:
    sys.exit("python-docx is required. Install with: pip install python-docx")


# ── Section mapping ───────────────────────────────────────────────────────────
# The doc's H1 names are verbose; the DB uses tighter labels (must match
# _PATTERN_SECTIONS in main.py).
_SECTION_MAP = {
    "Holes":                                                 "Holes",
    "Holes+":                                                "Holes+",
    "High Complexity":                                       "High Complexity",
    "Higher Complexity (Simple Outward Chains/Box Logic)":   "Box Logic",
    "Higherer Complexity (Simple Inward Chains)":            "Inward Chains",
    "Chains":                                                "Chains",
    "Combinations":                                          "Combinations",
    "Other  / Uncategorized":                                "Other",
    "Other / Uncategorized":                                 "Other",
    "Some of these may be low res / not clear":              "Other",
}
_SKIP_SECTIONS = {"Epilogue/Links"}

# Lines like "Depth: 3" and "Difficulty: A" appear once per pattern; pulled
# into Pattern.depth / Pattern.difficulty columns instead of the body text.
_DEPTH_RE = re.compile(r"^\s*Depth\s*[:\-]?\s*(\d+)",       re.IGNORECASE)
_DIFF_RE  = re.compile(r"^\s*Difficulty\s*[:\-]?\s*([A-E])", re.IGNORECASE)

# Strip the leading numbering ("1 ", "1.1 ", "26A ", "14b ") so the name is
# just the descriptive part.
_LEADING_NUM_RE = re.compile(r"^\s*\d+(\.\d+)*[A-Za-z]?\s+")


# ── Document parsing ─────────────────────────────────────────────────────────
@dataclass
class HeadingNode:
    level:      int                                   # 1..5
    raw_title:  str                                   # original heading text
    body:       list[str]                  = field(default_factory=list)
    images:     list[tuple[bytes, str]]    = field(default_factory=list)
    children:   list["HeadingNode"]        = field(default_factory=list)


def _heading_level(style_name: str) -> Optional[int]:
    if not style_name.startswith("Heading "):
        return None
    try:
        n = int(style_name.split()[-1])
        return n if 1 <= n <= 5 else None
    except ValueError:
        return None


def _strip_leading_number(text: str) -> str:
    return _LEADING_NUM_RE.sub("", text).strip()


def _parse_name_and_aliases(raw_title: str) -> tuple[str, list[str]]:
    """'D Pattern / Start-Extension / 23-221' → ('D Pattern', ['Start-Extension','23-221'])"""
    stripped = _strip_leading_number(raw_title)
    parts = [p.strip() for p in stripped.split("/") if p.strip()]
    if not parts:
        return stripped or "Untitled", []
    return parts[0], parts[1:]


def _slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:120] or "pattern"


def _unique_slug(base: str, used: set[str]) -> str:
    slug = base
    i = 2
    while slug in used:
        slug = f"{base}-{i}"
        i += 1
    used.add(slug)
    return slug


def parse_doc(docx_path: str) -> list[HeadingNode]:
    """Walk the document body in order, building a tree of headings.

    Non-heading paragraphs and inline images are attached to the deepest
    currently-open heading. Returns the list of H1 nodes.
    """
    doc = Document(docx_path)
    rels = doc.part.rels

    h1s: list[HeadingNode] = []
    stack: list[Optional[HeadingNode]] = [None] * 6   # index by heading level

    for para in doc.paragraphs:
        style = para.style.name if para.style else ""
        level = _heading_level(style)
        text  = (para.text or "").strip()

        # Extract any images embedded in this paragraph
        para_images: list[tuple[bytes, str]] = []
        for blip in para._element.findall(".//" + qn("a:blip")):
            rid = blip.get(qn("r:embed"))
            if not rid:
                continue
            rel = rels.get(rid)
            if rel is None or not getattr(rel, "target_part", None):
                continue
            image_part = rel.target_part
            ext = (image_part.content_type or "image/png").split("/")[-1].lower()
            if ext == "jpeg":
                ext = "jpg"
            para_images.append((image_part.blob, ext))

        if level is not None:
            if not text:
                # Empty heading paragraphs are common in this doc — skip them
                # but keep images attached to the open node.
                target = next((stack[L] for L in range(5, 0, -1) if stack[L]), None)
                if target is not None:
                    target.images.extend(para_images)
                continue

            node = HeadingNode(level=level, raw_title=text)

            # Close anything at this level or deeper
            for L in range(level, 6):
                stack[L] = None

            # Attach to nearest open ancestor (or as a new H1)
            if level == 1:
                h1s.append(node)
            else:
                parent = next((stack[L] for L in range(level - 1, 0, -1) if stack[L]), None)
                if parent is None:
                    # Stray heading before any H1 — create an implicit H1
                    parent = HeadingNode(level=1, raw_title="Unsectioned")
                    h1s.append(parent)
                    stack[1] = parent
                parent.children.append(node)

            stack[level] = node
            node.images.extend(para_images)

        else:
            # Body paragraph — attach to deepest open heading
            target = next((stack[L] for L in range(5, 0, -1) if stack[L]), None)
            if target is None:
                continue
            if text:
                target.body.append(text)
            target.images.extend(para_images)

    return h1s


# ── Pattern record building ───────────────────────────────────────────────────
def _depth_and_difficulty(node: HeadingNode) -> tuple[Optional[int], Optional[str]]:
    depth: Optional[int]    = None
    difficulty: Optional[str] = None
    for p in node.body:
        if depth is None:
            m = _DEPTH_RE.match(p)
            if m:
                try:
                    depth = int(m.group(1))
                except ValueError:
                    pass
        if difficulty is None:
            m = _DIFF_RE.match(p)
            if m:
                difficulty = m.group(1).upper()
    return depth, difficulty


def _save_image(image_bytes: bytes, ext: str, image_dir: Path, slug: str, idx: int) -> str:
    fname = f"{slug}-{idx}.{ext}"
    (image_dir / fname).write_bytes(image_bytes)
    return f"/static/img/patterns/{fname}"


def _render_body(node: HeadingNode, image_urls: list[str]) -> str:
    """Build the body markdown. Skip Depth/Difficulty lines (stored in columns).
    Fold descendant H4+ content in as nested Markdown headings. Append extra
    images so editors can see them all in the preview."""
    lines: list[str] = []
    for p in node.body:
        if _DEPTH_RE.match(p) or _DIFF_RE.match(p):
            continue
        lines.append(p)

    def walk_deeper(parent: HeadingNode):
        for child in parent.children:
            if child.level <= 3:
                continue   # H3 is imported as its own row, don't fold here
            hashes = "#" * min(child.level, 6)
            lines.append("")
            lines.append(f"{hashes} {_strip_leading_number(child.raw_title)}")
            for p in child.body:
                if _DEPTH_RE.match(p) or _DIFF_RE.match(p):
                    continue
                lines.append(p)
            walk_deeper(child)

    walk_deeper(node)

    if len(image_urls) > 1:
        lines.append("")
        lines.append("### Additional images")
        for url in image_urls[1:]:
            lines.append(f"![]({url})")

    return "\n\n".join(lines).strip()


def build_records(h1s: list[HeadingNode], image_dir: Path,
                  dry_run: bool, limit_section: Optional[str] = None) -> list[dict]:
    """Walk the heading tree and produce dicts ready to insert as Pattern rows."""
    records: list[dict] = []
    used_slugs: set[str] = set()
    unknown_sections: set[str] = set()

    if not dry_run:
        image_dir.mkdir(parents=True, exist_ok=True)

    for h1 in h1s:
        title = h1.raw_title.strip()
        if title in _SKIP_SECTIONS:
            continue
        section_name = _SECTION_MAP.get(title)
        if section_name is None:
            unknown_sections.add(title)
            section_name = "Other"

        if limit_section and section_name != limit_section:
            continue

        sort_h2 = 0
        for h2 in [c for c in h1.children if c.level == 2]:
            sort_h2 += 10
            h2_name, h2_aliases = _parse_name_and_aliases(h2.raw_title)
            h2_slug = _unique_slug(_slugify(h2_name), used_slugs)
            depth, diff = _depth_and_difficulty(h2)
            h2_image_urls = _materialize_images(h2.images, image_dir, h2_slug, dry_run)

            records.append({
                "slug":            h2_slug,
                "name":            h2_name[:128],
                "aliases":         h2_aliases or None,
                "section":         section_name,
                "depth":           depth,
                "difficulty":      diff,
                "parent_slug":     None,
                "sort_order":      sort_h2,
                "body_md":         _render_body(h2, h2_image_urls),
                "board_json":      None,
                "board_image_url": h2_image_urls[0] if h2_image_urls else None,
                "legend":          None,
                "status":          "draft",
            })

            sort_h3 = 0
            for h3 in [c for c in h2.children if c.level == 3]:
                sort_h3 += 10
                h3_name, h3_aliases = _parse_name_and_aliases(h3.raw_title)
                h3_slug = _unique_slug(_slugify(h3_name), used_slugs)
                d3, diff3 = _depth_and_difficulty(h3)
                h3_image_urls = _materialize_images(h3.images, image_dir, h3_slug, dry_run)

                records.append({
                    "slug":            h3_slug,
                    "name":            h3_name[:128],
                    "aliases":         h3_aliases or None,
                    "section":         section_name,
                    "depth":           d3,
                    "difficulty":      diff3,
                    "parent_slug":     h2_slug,
                    "sort_order":      sort_h3,
                    "body_md":         _render_body(h3, h3_image_urls),
                    "board_json":      None,
                    "board_image_url": h3_image_urls[0] if h3_image_urls else None,
                    "legend":          None,
                    "status":          "draft",
                })

    if unknown_sections:
        print(f"  ⚠ {len(unknown_sections)} unmapped H1 section(s) bucketed as 'Other':")
        for s in sorted(unknown_sections):
            print(f"      - {s!r}")

    return records


def _materialize_images(images: list[tuple[bytes, str]], image_dir: Path,
                        slug: str, dry_run: bool) -> list[str]:
    urls: list[str] = []
    for idx, (img_bytes, ext) in enumerate(images, start=1):
        if dry_run:
            urls.append(f"/static/img/patterns/{slug}-{idx}.{ext}")
        else:
            urls.append(_save_image(img_bytes, ext, image_dir, slug, idx))
    return urls


# ── DB write ──────────────────────────────────────────────────────────────────
def import_to_db(records: list[dict], editor_email: Optional[str],
                 update_existing: bool, dry_run: bool) -> tuple[int, int, int]:
    """Insert (or update) Pattern rows. Returns (inserted, updated, skipped)."""
    if dry_run:
        return (len(records), 0, 0)

    # Lazy import so dry-runs work without DB credentials
    from database import SessionLocal, Pattern, PatternRevision

    inserted = updated = skipped = 0
    db = SessionLocal()
    try:
        for r in records:
            existing = db.query(Pattern).filter_by(slug=r["slug"]).first()
            if existing:
                if not update_existing:
                    skipped += 1
                    continue
                # Snapshot the current row before overwriting
                db.add(PatternRevision(
                    pattern_id      = existing.id,
                    slug            = existing.slug,
                    name            = existing.name,
                    aliases         = existing.aliases,
                    section         = existing.section,
                    depth           = existing.depth,
                    difficulty      = existing.difficulty,
                    parent_slug     = existing.parent_slug,
                    sort_order      = existing.sort_order,
                    body_md         = existing.body_md,
                    board_json      = existing.board_json,
                    board_image_url = existing.board_image_url,
                    legend          = existing.legend,
                    status          = existing.status,
                    editor_email    = existing.editor_email,
                    edit_summary    = "Pre-import snapshot",
                ))
                for k, v in r.items():
                    setattr(existing, k, v)
                existing.editor_email = editor_email
                updated += 1
            else:
                db.add(Pattern(editor_email=editor_email, **r))
                inserted += 1
        db.commit()
    finally:
        db.close()
    return (inserted, updated, skipped)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Import the Pattern Library docx into the patterns DB table.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--docx", required=True, help="Path to Pattern-Library.docx")
    ap.add_argument("--image-dir", default="static/img/patterns",
                    help="Directory for extracted images (default: static/img/patterns)")
    ap.add_argument("--editor-email", default="importer@minesweeper.org",
                    help="Email recorded as the editor on each row")
    ap.add_argument("--update-existing", action="store_true",
                    help="Overwrite existing patterns with the same slug (snapshot kept in pattern_revisions)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse only — don't write to DB or disk")
    ap.add_argument("--limit-section", default=None,
                    help="Only import patterns whose mapped section equals this name (e.g. 'Holes')")
    ap.add_argument("--show-records", type=int, default=0,
                    help="Print this many parsed records to stdout (useful with --dry-run)")
    args = ap.parse_args()

    docx_path = Path(args.docx).resolve()
    if not docx_path.is_file():
        sys.exit(f"docx not found: {docx_path}")

    image_dir = Path(args.image_dir).resolve()

    print(f"Reading {docx_path}")
    h1s = parse_doc(str(docx_path))
    print(f"Found {len(h1s)} top-level H1 section(s):")
    for h in h1s:
        n_h2 = sum(1 for c in h.children if c.level == 2)
        n_h3 = sum(1 for c in h.children for cc in c.children if cc.level == 3)
        n_img = sum(len(c.images) for c in h.children) + sum(
            len(cc.images) for c in h.children for cc in c.children)
        print(f"  - {h.raw_title!r:60s}  H2={n_h2:2d}  H3={n_h3:2d}  images={n_img:3d}")

    records = build_records(h1s, image_dir, args.dry_run, args.limit_section)
    print(f"\nBuilt {len(records)} pattern record(s) "
          f"({'dry run' if args.dry_run else 'will commit'})")

    by_section: dict[str, int] = {}
    for r in records:
        by_section[r["section"]] = by_section.get(r["section"], 0) + 1
    for sec, n in by_section.items():
        print(f"   {sec:20s}  {n} pattern(s)")

    if args.show_records:
        print(f"\nFirst {args.show_records} records:")
        for r in records[:args.show_records]:
            print(f"   slug={r['slug']!r}  name={r['name']!r}  "
                  f"section={r['section']!r}  parent={r['parent_slug']!r}  "
                  f"depth={r['depth']}  diff={r['difficulty']}  "
                  f"img={r['board_image_url']!r}")

    inserted, updated, skipped = import_to_db(
        records,
        editor_email=args.editor_email,
        update_existing=args.update_existing,
        dry_run=args.dry_run,
    )
    print(f"\nResult: inserted={inserted}, updated={updated}, skipped={skipped}")
    if args.dry_run:
        print("(dry run — no DB or disk writes)")
    else:
        print(f"Images written under {image_dir}")
        print("All rows staged as status='draft'. Review and publish at /admin/patterns")


if __name__ == "__main__":
    main()
