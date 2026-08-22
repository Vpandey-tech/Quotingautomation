import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from main import app

def test_api_endpoints():
    client = TestClient(app)

    print("=== Testing Endpoints & Quoting Handoff Contract ===")
    
    # 1. Create Session
    create_res = client.post("/api/design/sessions", json={"component_type": "custom", "custom_description": "I want a 150mm flange with 20mm thickness, 40mm center bore, and 4 M8 bolt holes on 110mm PCD in Steel"})
    assert create_res.status_code == 200, f"Session create failed: {create_res.text}"
    session_data = create_res.json()
    sid = session_data["id"]
    print(f"Session created: {sid} | Component Family: {session_data.get('component_type')}")
    
    # 2. Batch Parameters
    batch_res = client.post(f"/api/design/sessions/{sid}/params/batch", json={"answers": {
        "outer_diameter_mm": 150.0,
        "thickness_mm": 20.0,
        "inner_bore_diameter_mm": 40.0,
        "bolt_circle_diameter_mm": 110.0,
        "num_bolts": 4,
        "bolt_size": "M8",
        "material_id": "steel_1045"
    }})
    assert batch_res.status_code == 200, f"Batch params failed: {batch_res.text}"
    
    # 3. Generate Report
    report_res = client.post(f"/api/design/sessions/{sid}/generate-report")
    assert report_res.status_code == 200, f"Generate report failed: {report_res.text}"
    
    # 4. Approve Report
    approve_res = client.post(f"/api/design/sessions/{sid}/approve-report")
    assert approve_res.status_code == 200, f"Approve report failed: {approve_res.text}"
    
    # 5. Generate CAD
    cad_res = client.post(f"/api/design/sessions/{sid}/generate-cad")
    assert cad_res.status_code == 200, f"Generate CAD failed: {cad_res.text}"
    cad_data = cad_res.json()
    print(f"CAD generated: {cad_data.get('step_file')} | Volume: {cad_data.get('volume')} mm3 | Area: {cad_data.get('surface_area')} mm2")
    
    # 6. Send to Quoting
    quote_res = client.post(f"/api/design/sessions/{sid}/send-to-quoting")
    assert quote_res.status_code == 200, f"Send to quoting failed: {quote_res.text}"
    quote_data = quote_res.json()
    print(f"Quoting handoff metrics: {quote_data.get('metrics')}")
    print(f"Quoting handoff top keys: {list(quote_data.keys())}")
    
    # Verify contract keys
    expected_top_keys = {"session_id", "transferred", "component_type", "has_cad_file", "download_url", "metrics", "engineering_data"}
    assert set(quote_data.keys()) == expected_top_keys, f"Top level keys mismatch: {set(quote_data.keys())} vs {expected_top_keys}"
    
    expected_metric_keys = {"volume", "surfaceArea", "sizeX", "sizeY", "sizeZ", "material", "quantity"}
    assert set(quote_data["metrics"].keys()) == expected_metric_keys, f"Metrics keys mismatch: {set(quote_data['metrics'].keys())} vs {expected_metric_keys}"
    
    expected_eng_keys = {"params", "calculations", "safety", "dimensions", "standards"}
    assert set(quote_data["engineering_data"].keys()) == expected_eng_keys, f"Engineering data keys mismatch: {set(quote_data['engineering_data'].keys())} vs {expected_eng_keys}"
    
    # Verify exact OCC measured volume and area are populated
    assert quote_data["metrics"]["volume"] > 0, "Volume must be positive"
    assert quote_data["metrics"]["surfaceArea"] > 0, "Surface area must be positive"
    
    print("\nAPI CONTRACT & QUOTING HANDOFF VERIFICATION PASSED 100%!")

if __name__ == '__main__':
    test_api_endpoints()
