import os
import json
import sys
import logging

logger = logging.getLogger(__name__)

_catalog_cache = None
_catalog_path = None

def _load_catalog():
    global _catalog_cache, _catalog_path
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    _catalog_path = os.path.join(base_path, "vendor_data", "psv_vendor_catalog_official.json")

    if not os.path.exists(_catalog_path):
        logger.warning("Vendor catalog file not found at: %s", _catalog_path)
        _catalog_cache = {"models": []}
        return

    try:
        with open(_catalog_path, 'r', encoding='utf-8') as f:
            _catalog_cache = json.load(f)
    except Exception as e:
        logger.error("Vendor catalog read error: %s", e)
        _catalog_cache = {"models": []}

_DESIGN_CATEGORY_KEYWORDS = {
    "conventional": ("conventional", "spring"),
    "balanced_bellows": ("balanced", "bellows"),
    "pilot": ("pilot",),
}

def _design_categories(design_type):
    """Classify a vendor design_type string into one or more valve categories."""
    text = (design_type or "").lower()
    cats = set()
    for cat, keywords in _DESIGN_CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            cats.add(cat)
    if not cats and text:
        cats.add("conventional")
    return cats

def get_vendor_valves(api_letter, valve_type=None):
    if not api_letter or api_letter == "-":
        return []

    if _catalog_cache is None:
        _load_catalog()

    matching_valves = []
    for model in _catalog_cache.get("models", []):
        if model.get("api526_equivalent") == api_letter or model.get("orifice_letter") == api_letter:
            if valve_type:
                if valve_type.lower() not in _design_categories(model.get("design_type", "")):
                    continue
            matching_valves.append(model)

    return matching_valves

def reload_catalog():
    global _catalog_cache
    _catalog_cache = None
    _load_catalog()
