"""
Vendor catalog cleanup script.

- Removes records with no valid API 526 orifice letter (D..T) in either
  `api526_equivalent` or `orifice_letter`.
- Replaces google.com/search "website" placeholders with the manufacturer's
  official catalog URL from `manufacturer_directory` (or clears the field).

Usage:
    python scripts/clean_vendor_db.py            # dry-run report
    python scripts/clean_vendor_db.py --apply    # write cleaned catalog
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "vendor_data", "psv_vendor_catalog_official.json",
)

VALID_API_LETTERS = set("DEFGHJKLMNPQRT")


def main():
    parser = argparse.ArgumentParser(description="Clean the PSV vendor catalog.")
    parser.add_argument("--apply", action="store_true", help="Write the cleaned catalog back to disk.")
    args = parser.parse_args()

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    models = catalog.get("models", [])
    directory = catalog.get("manufacturer_directory", [])

    official_urls = {}
    for item in directory:
        mfr = str(item.get("manufacturer", "")).lower()
        url = item.get("official_url", "")
        if mfr and url:
            official_urls[mfr] = url

    removed = []
    fixed_websites = 0
    cleaned = []

    for model in models:
        api_letter = str(model.get("api526_equivalent", "") or "").strip().upper()
        orifice_letter = str(model.get("orifice_letter", "") or "").strip().upper()
        valid = api_letter in VALID_API_LETTERS or orifice_letter in VALID_API_LETTERS

        if not valid:
            removed.append(model.get("model_code") or model.get("orifice_letter") or "?")
            continue

        website = str(model.get("website", "") or "")
        if "google.com/search" in website:
            mfr_key = str(model.get("manufacturer", "")).lower()
            candidate = official_urls.get(mfr_key, "")
            if candidate:
                model["website"] = candidate
            else:
                model["website"] = ""
            fixed_websites += 1

        cleaned.append(model)

    print(f"Total models: {len(models)}")
    print(f"Removed (no valid API 526 orifice): {len(removed)}")
    for code in removed:
        print(f"  - {code}")
    print(f"Website placeholders replaced/cleared: {fixed_websites}")
    print(f"Cleaned model count: {len(cleaned)}")

    if args.apply:
        catalog["models"] = cleaned
        note = ("Cleaned: removed non-API-526 records; google search placeholders "
                "replaced with manufacturer official URLs.")
        if isinstance(catalog.get("notes"), list):
            catalog["notes"].append(note)
        else:
            catalog["notes"] = (catalog.get("notes", "") + " " + note).strip()
        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        print("Wrote cleaned catalog to", CATALOG_PATH)
    else:
        print("Dry run - use --apply to write changes.")


if __name__ == "__main__":
    main()