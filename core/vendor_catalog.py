import os
import json
import sys

def get_vendor_valves(api_letter):
    """
    Reads the vendor catalog JSON and returns all commercial models 
    matching the specified API orifice letter.
    """
    if not api_letter or api_letter == "-":
        return []
        
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    catalog_path = os.path.join(base_path, "vendor_data", "psv_vendor_catalog_official.json")
    
    if not os.path.exists(catalog_path):
        return []
        
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        matching_valves = []
        for model in data.get("models", []):
            if model.get("api526_equivalent") == api_letter or model.get("orifice_letter") == api_letter:
                matching_valves.append(model)
                
        return matching_valves
    except Exception as e:
        print(f"Vendor catalog read error: {e}")
        return []
