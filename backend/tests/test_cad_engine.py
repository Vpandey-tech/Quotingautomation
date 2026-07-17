import sys
import os
import math

# Ensure backend directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from services.engineering.cad_engine import (
    generate_cad, compute_expected_properties, lookup_bearing_dimensions
)

def run_all_tests():
    print("=============================================================")
    print("      Running AccuDesign CAD Engine Regression Tests         ")
    print("=============================================================")

    # Test 1: SHAFT
    print("\n1. Testing Shaft Generation...")
    shaft_dims = {
        "diameter_mm": 40.0,
        "length_mm": 200.0,
        "inner_diameter_mm": 20.0
    }
    shaft_params = {
        "keyway": "yes",
        "num_keyways": 2,
        "chamfer_length_mm": 1.5
    }
    res_shaft = generate_cad("shaft", shaft_dims, shaft_params)
    assert res_shaft["step_file"] is not None, "Shaft STEP file generation failed!"
    assert os.path.exists(res_shaft["step_file"]), "Shaft STEP file does not exist!"
    assert "note" not in res_shaft, f"Shaft verification failed with note: {res_shaft.get('note')}"
    print(f"Shaft generated successfully. STEP: {res_shaft['step_file']}")

    # Test 2: CAM
    print("\n2. Testing Cam Generation...")
    cam_dims = {
        "base_circle_radius_mm": 40.0,
        "lift_mm": 15.0,
        "cam_width_mm": 25.0
    }
    cam_params = {
        "profile_type": "cycloidal",
        "rise_angle_deg": 100.0,
        "dwell_angle_deg": 80.0,
        "bore_diameter_mm": 12.0
    }
    res_cam = generate_cad("cam", cam_dims, cam_params)
    assert res_cam["step_file"] is not None, "Cam STEP file generation failed!"
    assert os.path.exists(res_cam["step_file"]), "Cam STEP file does not exist!"
    assert "note" not in res_cam, f"Cam verification failed with note: {res_cam.get('note')}"
    print(f"Cam generated successfully. STEP: {res_cam['step_file']}")

    # Test 3: BEARING
    print("\n3. Testing Bearing Generation...")
    bearing_dims = {
        "bore_diameter_mm": 30.0,
    }
    bearing_params = {
        "bearing_series": "62xx",
        "num_balls": 10
    }
    res_bearing = generate_cad("bearing", bearing_dims, bearing_params)
    assert res_bearing["step_file"] is not None, "Bearing STEP file generation failed!"
    assert os.path.exists(res_bearing["step_file"]), "Bearing STEP file does not exist!"
    assert "note" not in res_bearing, f"Bearing verification failed with note: {res_bearing.get('note')}"
    print(f"Bearing generated successfully. STEP: {res_bearing['step_file']}")

    # Test 4: GEARBOX
    print("\n4. Testing Gearbox Generation...")
    gearbox_dims = {
        "pinion_pitch_dia_mm": 60.0,
        "gear_pitch_dia_mm": 180.0,
        "face_width_mm": 30.0,
        "input_shaft_dia_mm": 20.0,
        "output_shaft_dia_mm": 50.0
    }
    gearbox_params = {
        "num_stages": 1,
        "wall_thickness_mm": 8.0,
        "flange_width_mm": 15.0,
        "flange_thickness_mm": 12.0,
        "bolt_hole_diameter_mm": 10.0
    }
    res_gearbox = generate_cad("gearbox", gearbox_dims, gearbox_params)
    assert res_gearbox["step_file"] is not None, "Gearbox STEP file generation failed!"
    assert os.path.exists(res_gearbox["step_file"]), "Gearbox STEP file does not exist!"
    assert "note" not in res_gearbox, f"Gearbox verification failed with note: {res_gearbox.get('note')}"
    print(f"Gearbox generated successfully. STEP: {res_gearbox['step_file']}")

    # Test 5: CUSTOM (Advanced operations)
    print("\n5. Testing Custom Part with Advanced Ops...")
    custom_dims = {}
    custom_params = {
        "operations": [
            {
                "type": "box",
                "l": 80.0,
                "w": 60.0,
                "h": 40.0,
                "action": "add"
            },
            {
                "type": "sketch_extrude",
                "points": [[-20.0, -20.0], [20.0, -20.0], [0.0, 20.0]],
                "height": 15.0,
                "x": 0.0,
                "y": 0.0,
                "z": 20.0,
                "action": "cut"
            },
            {
                "type": "hole_pattern",
                "pattern": "circular",
                "count": 6,
                "diameter": 6.0,
                "depth": 50.0,
                "pcd_radius": 20.0,
                "center": [0.0, 0.0, -10.0],
                "action": "cut"
            },
            {
                "type": "fillet",
                "target": "top",
                "radius": 2.0
            }
        ]
    }
    res_custom = generate_cad("custom", custom_dims, custom_params)
    assert res_custom["step_file"] is not None, "Custom STEP file generation failed!"
    assert os.path.exists(res_custom["step_file"]), "Custom STEP file does not exist!"
    assert "note" not in res_custom, f"Custom verification failed with note: {res_custom.get('note')}"
    print(f"Custom Part generated successfully. STEP: {res_custom['step_file']}")

    print("\n=============================================================")
    print("      All AccuDesign CAD Engine Tests Passed Successfully!   ")
    print("=============================================================")

if __name__ == "__main__":
    run_all_tests()
