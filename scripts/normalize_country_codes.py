#!/usr/bin/env python3
"""
normalize_country_codes.py

One-time migration to fix user_profiles rows where the `country` column
was stored as a full country name (e.g. "brazil", "netherlands") instead
of the 2-letter ISO code ("br", "nl").

This happened for early users before the /api/profile/country endpoint
enforced code validation.  The bad values only show up in Apache logs as
404s on /static/img/country-flags/<fullname>.png.

Usage (run from the repo root on the server):
    python scripts/normalize_country_codes.py [--dry-run]

    --dry-run   Print what would change without writing to the DB.

Exit codes:
    0  Success (or nothing to do)
    1  Unexpected error
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, UserProfile
from countries import COUNTRIES, VALID_COUNTRY_CODES

# Build a case-insensitive name→code lookup from the master list.
# e.g. "brazil" -> "br", "netherlands" -> "nl"
NAME_TO_CODE: dict[str, str] = {
    name.lower(): code for code, name in COUNTRIES
}


def normalize(dry_run: bool = False) -> int:
    db = SessionLocal()
    try:
        # Fetch all profiles that have a non-null country value which is NOT
        # already a valid 2-letter (or region) code.
        all_profiles = (
            db.query(UserProfile)
            .filter(UserProfile.country.isnot(None))
            .all()
        )

        to_fix:   list[tuple[UserProfile, str, str | None]] = []
        to_clear: list[tuple[UserProfile, str]]             = []

        for p in all_profiles:
            code = (p.country or "").strip().lower()
            if not code:
                continue
            if code in VALID_COUNTRY_CODES:
                continue  # already correct

            # Try to map full name → code
            mapped = NAME_TO_CODE.get(code)
            if mapped:
                to_fix.append((p, p.country, mapped))
            else:
                # Unrecognised value — null it out to avoid broken flag URLs
                to_clear.append((p, p.country))

        print(f"Profiles scanned : {len(all_profiles)}")
        print(f"To remap         : {len(to_fix)}")
        print(f"To clear (unknown): {len(to_clear)}")

        if not to_fix and not to_clear:
            print("Nothing to do.")
            return 0

        print()
        for p, old, new in to_fix:
            print(f"  REMAP  email={p.email!r:50s}  {old!r} -> {new!r}")
        for p, old in to_clear:
            print(f"  CLEAR  email={p.email!r:50s}  {old!r} -> NULL")

        if dry_run:
            print("\n[dry-run] No changes written.")
            return 0

        print()
        for p, _old, new in to_fix:
            p.country = new
        for p, _old in to_clear:
            p.country = None

        db.commit()
        print(f"Done. {len(to_fix)} remapped, {len(to_clear)} cleared.")
        return 0

    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print changes without writing to the DB")
    args = parser.parse_args()
    sys.exit(normalize(dry_run=args.dry_run))
