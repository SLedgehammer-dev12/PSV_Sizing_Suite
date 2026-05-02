import json
import os
from copy import deepcopy


CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "vendor_data",
    "psv_vendor_catalog_official.json",
)

API_ORIFICE_AREAS_SQIN = {
    "D": 0.110,
    "E": 0.196,
    "F": 0.307,
    "G": 0.503,
    "H": 0.785,
    "J": 1.287,
    "K": 1.838,
    "L": 2.853,
    "M": 3.600,
    "N": 4.340,
    "P": 6.380,
    "Q": 11.050,
    "R": 16.000,
    "T": 26.000,
}

GLOBAL_VENDORS = [
    # Americas
    {
        "manufacturer": "Emerson Crosby",
        "series": "JOS-E / JBS-E",
        "design_type": "Conventional / Balanced Bellows",
        "kd": 0.865,
        "headquarters_country": "United States",
        "regions": ["Americas", "Europe", "Asia"],
        "website": "https://www.emerson.com/en-us/automation/valves-actuators-regulators/pressure-relief-valves",
        "product_scope": "Crosby spring-loaded pressure relief valves for process and power services",
    },
    {
        "manufacturer": "Anderson Greenwood",
        "series": "Series 200 / 400 / 800",
        "design_type": "Pilot-Operated",
        "kd": 0.878,
        "headquarters_country": "United States",
        "regions": ["Americas", "Europe", "Asia"],
        "website": "https://www.emerson.com/en-us/automation/valves-actuators-regulators/pressure-relief-valves",
        "product_scope": "Pilot-operated pressure relief valves and tank protection products",
    },
    {
        "manufacturer": "Kunkle",
        "series": "Industrial Safety Relief",
        "design_type": "Spring Loaded",
        "kd": 0.840,
        "headquarters_country": "United States",
        "regions": ["Americas"],
        "website": "https://www.emerson.com/en-us/automation/valves-actuators-regulators/pressure-relief-valves",
        "product_scope": "Commercial and industrial safety relief valves",
    },
    {
        "manufacturer": "Mercer Valve",
        "series": "9100 / 9500 Series",
        "design_type": "Conventional",
        "kd": 0.850,
        "headquarters_country": "United States",
        "regions": ["Americas"],
        "website": "https://www.mercervalve.net/",
        "product_scope": "ASME/NB certified safety relief valves",
    },
    {
        "manufacturer": "Circle Seal Controls",
        "series": "Safety Relief Valves",
        "design_type": "Spring Loaded",
        "kd": 0.840,
        "headquarters_country": "United States",
        "regions": ["Americas"],
        "website": "https://www.circlesealcontrols.com/products/relief-valves/",
        "product_scope": "Compact relief valves for gas, liquid, and specialty services",
    },
    {
        "manufacturer": "Kingston Valves",
        "series": "Safety Relief Valves",
        "design_type": "Spring Loaded",
        "kd": 0.830,
        "headquarters_country": "United States",
        "regions": ["Americas"],
        "website": "https://www.kingstonvalves.com/",
        "product_scope": "Industrial and commercial safety valves",
    },
    # Europe
    {
        "manufacturer": "BESA",
        "series": "API / ASME Safety Valves",
        "design_type": "Conventional / Balanced Bellows",
        "kd": 0.850,
        "headquarters_country": "Italy",
        "regions": ["Europe", "Americas", "Asia"],
        "website": "https://www.besa.it/",
        "product_scope": "Safety valves designed to PED, ATEX, API 520/526/527 and ASME requirements",
    },
    {
        "manufacturer": "IMI Bopp & Reuther",
        "series": "Si 830 / Si 41",
        "design_type": "Spring Loaded",
        "kd": 0.860,
        "headquarters_country": "Germany",
        "regions": ["Europe", "Americas", "Asia"],
        "website": "https://www.imi-critical.com/products/safety-valves/",
        "product_scope": "High-flow safety relief valves and process safety valves",
    },
    {
        "manufacturer": "Birkett",
        "series": "API Safety Relief",
        "design_type": "Conventional / Balanced Bellows",
        "kd": 0.850,
        "headquarters_country": "United Kingdom",
        "regions": ["Europe", "Americas", "Asia"],
        "website": "https://www.trilliumflow.com/products/valves/pressure-relief-valves/",
        "product_scope": "API and ASME pressure relief valves under Trillium Flow Technologies",
    },
    {
        "manufacturer": "Seetru",
        "series": "LGS / Safety Relief",
        "design_type": "Spring Loaded",
        "kd": 0.820,
        "headquarters_country": "United Kingdom",
        "regions": ["Europe", "Americas", "Asia"],
        "website": "https://www.seetru.com/products/safety-valves/",
        "product_scope": "Safety relief valves for liquid, gas, air, and steam",
    },
    {
        "manufacturer": "Valvitalia",
        "series": "Safety Relief Valves",
        "design_type": "Conventional / Pilot-Operated",
        "kd": 0.850,
        "headquarters_country": "Italy",
        "regions": ["Europe", "Americas", "Asia"],
        "website": "https://www.valvitalia.com/products/",
        "product_scope": "Oil and gas pressure relief valve product portfolio",
    },
    {
        "manufacturer": "Sapag",
        "series": "Safety Relief Valves",
        "design_type": "Spring Loaded / Pilot-Operated",
        "kd": 0.850,
        "headquarters_country": "France",
        "regions": ["Europe", "Americas", "Asia"],
        "website": "https://www.valves.emerson.com/",
        "product_scope": "Process safety relief valves historically supplied under Sapag product lines",
    },
    {
        "manufacturer": "VYC Industrial",
        "series": "285 / 286 / 385",
        "design_type": "Conventional",
        "kd": 0.840,
        "headquarters_country": "Spain",
        "regions": ["Europe", "Americas", "Asia"],
        "website": "https://vycindustrial.com/en/",
        "product_scope": "ASME/API safety valves for gas, steam, and liquid services",
    },
    # Asia
    {
        "manufacturer": "Fukui Seisakusho",
        "series": "RE / API Series",
        "design_type": "Conventional / Balanced Bellows",
        "kd": 0.850,
        "headquarters_country": "Japan",
        "regions": ["Asia", "Americas", "Europe"],
        "website": "https://www.fkis.co.jp/eng/",
        "product_scope": "Safety relief valves for energy, petrochemical, and industrial services",
    },
    {
        "manufacturer": "Nakakita Seisakusho",
        "series": "Safety Valve Series",
        "design_type": "Conventional",
        "kd": 0.850,
        "headquarters_country": "Japan",
        "regions": ["Asia", "Americas", "Europe"],
        "website": "https://www.nakakita-s.co.jp/english/products/",
        "product_scope": "Safety and control valves for shipbuilding, power, and process industries",
    },
    {
        "manufacturer": "Yoshitake",
        "series": "AL / Safety Relief",
        "design_type": "Spring Loaded",
        "kd": 0.840,
        "headquarters_country": "Japan",
        "regions": ["Asia", "Americas", "Europe"],
        "website": "https://www.yoshitake.jp/english/products/",
        "product_scope": "Steam, air, gas, and liquid safety relief valves",
    },
    {
        "manufacturer": "TLV",
        "series": "Safety Valves",
        "design_type": "Spring Loaded",
        "kd": 0.830,
        "headquarters_country": "Japan",
        "regions": ["Asia", "Americas", "Europe"],
        "website": "https://www.tlv.com/global/",
        "product_scope": "Steam safety valves and pressure control equipment",
    },
    {
        "manufacturer": "KOSO Kent Introl",
        "series": "Safety Relief Valves",
        "design_type": "Spring Loaded",
        "kd": 0.840,
        "headquarters_country": "Japan / United Kingdom",
        "regions": ["Asia", "Europe", "Americas"],
        "website": "https://www.koso.co.jp/en/",
        "product_scope": "Control and safety valve products for process industries",
    },
    {
        "manufacturer": "H. P. Valve",
        "series": "API 520 / 526 Safety Relief",
        "design_type": "Conventional",
        "kd": 0.840,
        "headquarters_country": "India",
        "regions": ["Asia", "Europe", "Americas"],
        "website": "https://www.hpvalve.net/safety_relief_valve.html",
        "product_scope": "API 520/526 safety relief valves for industrial services",
    },
    {
        "manufacturer": "Erardo",
        "series": "API 520 / 526 Safety Relief",
        "design_type": "Conventional",
        "kd": 0.840,
        "headquarters_country": "India",
        "regions": ["Asia", "Europe", "Americas"],
        "website": "https://erardoindia.com/steam_pressure_safety_valve.html",
        "product_scope": "API 520/526/527 safety relief valves",
    },
    {
        "manufacturer": "Sasthan Engineers",
        "series": "API Safety Relief",
        "design_type": "Spring Loaded",
        "kd": 0.840,
        "headquarters_country": "India",
        "regions": ["Asia", "Europe", "Americas"],
        "website": "https://www.sasthanengineers.com/safety-relief-valves",
        "product_scope": "API 520/526 safety relief valves",
    },
]


def model_signature(model):
    return (
        model.get("manufacturer"),
        model.get("series"),
        model.get("api526_equivalent") or model.get("orifice_letter"),
    )


def directory_signature(entry):
    return entry.get("manufacturer")


def build_model(vendor, letter, area_sqin):
    effective_area_mm2 = area_sqin * 645.16
    actual_area_mm2 = effective_area_mm2 * 1.05
    series_slug = "".join(
        c if c.isalnum() else "-"
        for c in vendor["series"].split("/")[0].strip()
    ).strip("-")

    return {
        "manufacturer": vendor["manufacturer"],
        "series": vendor["series"],
        "model_code": f"{series_slug}-{letter}",
        "design_type": vendor["design_type"],
        "orifice_letter": letter,
        "size_label": letter,
        "api526_equivalent": letter,
        "inlet_outlet_size_in": "Standard API screening",
        "inlet_outlet_size_dn": "Standard API screening",
        "effective_area_mm2": round(effective_area_mm2, 1),
        "actual_area_mm2": round(actual_area_mm2, 1),
        "certified_kd_gas": vendor["kd"],
        "website": vendor["website"],
        "source": "Regional Vendor Coverage Extension",
        "data_quality": "screening_placeholder",
        "notes": (
            "Preliminary regional vendor coverage row. Verify exact certified capacity, trim, "
            "materials, pressure class, and code stamp with the manufacturer before purchase."
        ),
    }


with open(CATALOG_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

data.setdefault("notes", [])
coverage_note = (
    "Version 2.1 expands vendor coverage across the Americas, Europe, and Asia. "
    "Rows marked Regional Vendor Coverage Extension are screening placeholders and "
    "must be validated against current manufacturer-certified sizing data."
)
if coverage_note not in data["notes"]:
    data["notes"].append(coverage_note)

data.setdefault("manufacturer_directory", [])
existing_directory = {directory_signature(entry) for entry in data["manufacturer_directory"]}
for vendor in GLOBAL_VENDORS:
    if vendor["manufacturer"] in existing_directory:
        for entry in data["manufacturer_directory"]:
            if entry.get("manufacturer") == vendor["manufacturer"]:
                entry.setdefault("regions", vendor["regions"])
                entry.setdefault("official_url", vendor["website"])
                entry.setdefault("product_scope", vendor["product_scope"])
                entry["screening_models_included"] = True
                break
        continue

    data["manufacturer_directory"].append({
        "manufacturer": vendor["manufacturer"],
        "headquarters_country": vendor["headquarters_country"],
        "regions": deepcopy(vendor["regions"]),
        "screening_models_included": True,
        "official_reference": "Manufacturer product page",
        "official_url": vendor["website"],
        "product_scope": vendor["product_scope"],
        "notes": "Added for version 2.1 regional PSV vendor coverage.",
    })
    existing_directory.add(vendor["manufacturer"])

data.setdefault("models", [])
existing_models = {model_signature(model) for model in data["models"]}
added_count = 0
for vendor in GLOBAL_VENDORS:
    for letter, area_sqin in API_ORIFICE_AREAS_SQIN.items():
        model = build_model(vendor, letter, area_sqin)
        signature = model_signature(model)
        if signature in existing_models:
            continue

        data["models"].append(model)
        existing_models.add(signature)
        added_count += 1

with open(CATALOG_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"Added {added_count} vendor screening models.")
print(f"Total models: {len(data['models'])}")
print(f"Directory manufacturers: {len(data['manufacturer_directory'])}")
