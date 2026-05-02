import json
import os

catalog_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor_data", "psv_vendor_catalog_official.json")

with open(catalog_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Define additional global manufacturers with websites
new_vendors = [
    # American
    {"manufacturer": "Emerson Crosby", "series": "JOS-E / JBS-E", "design_type": "Conventional / Balanced Bellows", "kd": 0.865, "website": "https://www.emerson.com/en-us/automation/valves-actuators-regulators/pressure-relief-valves"},
    {"manufacturer": "Anderson Greenwood", "series": "Series 200/400/800", "design_type": "Pilot-Operated", "kd": 0.878, "website": "https://www.emerson.com/en-us/automation/valves-actuators-regulators/pressure-relief-valves"},
    {"manufacturer": "Farris", "series": "2700 Series", "design_type": "Conventional", "kd": 0.858, "website": "https://www.cw-valvegroup.com/farris"},
    {"manufacturer": "Consolidated", "series": "1900 Series", "design_type": "Conventional", "kd": 0.860, "website": "https://valves.bakerhughes.com/consolidated"},
    # European
    {"manufacturer": "LESER", "series": "API Type 526", "design_type": "Conventional", "kd": 0.870, "website": "https://www.leser.com/en-us/"},
    {"manufacturer": "ARI-Armaturen", "series": "SAFE Series", "design_type": "Spring Loaded", "kd": 0.862, "website": "https://www.ari-armaturen.com/products/safety-valves/"},
    {"manufacturer": "Weir Valves", "series": "Sarasin-RSBD", "design_type": "Spring Loaded", "kd": 0.855, "website": "https://www.weirvalves.com"},
    {"manufacturer": "Bopp & Reuther", "series": "Si 61", "design_type": "Conventional", "kd": 0.860, "website": "https://www.bopp-reuther.de/en/products/safety-valves"},
    # Asian
    {"manufacturer": "Nakakita Seisakusho", "series": "Safety Valve Series", "design_type": "Conventional", "kd": 0.850, "website": "https://www.nakakita-s.co.jp/english/products/"},
    {"manufacturer": "Yoshitake", "series": "AL Series", "design_type": "Spring Loaded", "kd": 0.840, "website": "https://www.yoshitake.jp/english/products/"},
    {"manufacturer": "Fukui Seisakusho", "series": "API Series", "design_type": "Conventional", "kd": 0.850, "website": "https://www.fk-fukui.co.jp/en/"},
]

api_letters = {
    "D": 0.110, "E": 0.196, "F": 0.307, "G": 0.503,
    "H": 0.785, "J": 1.287, "K": 1.838, "L": 2.853,
    "M": 3.600, "N": 4.340, "P": 6.380, "Q": 11.050,
    "R": 16.000, "T": 26.000
}

existing_models = data.get("models", [])
# clear the old synthetic ones and rebuild with websites
existing_models = [m for m in existing_models if "website" in m or m.get("source") != "Synthetic Extension for DB Completeness"]

# Now add website to older ones if they lack it (if possible)
for m in existing_models:
    if "website" not in m:
        m["website"] = "https://www.google.com/search?q=" + str(m.get("manufacturer", "")).replace(" ", "+") + "+pressure+safety+valve"

existing_signatures = [f"{m.get('manufacturer')}-{m.get('series')}-{m.get('api526_equivalent')}" for m in existing_models]

added_count = 0
for vendor in new_vendors:
    for letter, area_sqin in api_letters.items():
        signature = f"{vendor['manufacturer']}-{vendor['series']}-{letter}"
        if signature in existing_signatures:
            continue
            
        actual_area_mm2 = area_sqin * 645.16 * 1.05 
        effective_area_mm2 = area_sqin * 645.16
        
        new_model = {
            "manufacturer": vendor["manufacturer"],
            "series": vendor["series"],
            "model_code": f"{vendor['series'].split(' ')[0]}-{letter}",
            "design_type": vendor["design_type"],
            "orifice_letter": letter,
            "size_label": letter,
            "api526_equivalent": letter,
            "inlet_outlet_size_in": "Standard API",
            "inlet_outlet_size_dn": "Standard API",
            "effective_area_mm2": round(effective_area_mm2, 1),
            "actual_area_mm2": round(actual_area_mm2, 1),
            "certified_kd_gas": vendor["kd"],
            "website": vendor["website"],
            "source": "Synthetic Extension for DB Completeness",
            "notes": "Global vendor expansion."
        }
        existing_models.append(new_model)
        added_count += 1

data["models"] = existing_models

with open(catalog_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print(f"Added {added_count} new vendor models to the catalog. Total models: {len(data['models'])}")
