import sys
import os
import pytest

# Ensure backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.engineering.math_engine import run_calculation


def test_shaft_calculations():
    params = {
        "power_kw": 55.0,
        "speed_rpm": 1500.0,
        "bending_moment_nm": 300.0,
        "torsional_shock_factor": 1.5,
        "bending_shock_factor": 2.0,
        "fos": 2.5,
        "material_id": "steel_1045",
        "loading_type": "rotating",
    }
    res = run_calculation("shaft", params)
    
    # Assert result structure
    assert "calculations" in res
    assert "dimensions" in res
    assert "safety" in res
    assert "kb_verifications" in res
    
    dims = res["dimensions"]
    assert dims["equivalent_torque_nm"] > 0
    assert dims["min_diameter_asme_mm"] > 0
    assert dims["diameter_mm"] >= dims["min_diameter_asme_mm"]
    assert "tolerance_class" in dims
    assert "fit_shaft" in dims
    
    # Assert KB checks exist and match
    kb_checks = res["kb_verifications"]
    assert len(kb_checks) > 0
    for check in kb_checks:
        assert "kb_verified" in check
        assert check["kb_verified"] is True


def test_bearing_calculations():
    params = {
        "radial_load_n": 8000.0,
        "axial_load_n": 2000.0,
        "speed_rpm": 1200.0,
        "bearing_type": "deep_groove_ball",
        "desired_life_hours": 20000.0,
        "reliability_pct": 95.0,
        "fos": 1.5,
    }
    res = run_calculation("bearing", params)
    
    assert "calculations" in res
    assert "dimensions" in res
    assert "safety" in res
    assert "kb_verifications" in res
    
    dims = res["dimensions"]
    assert dims["bore_diameter_mm"] > 0
    assert dims["outer_diameter_mm"] > dims["bore_diameter_mm"]
    assert dims["width_mm"] > 0
    assert dims["C_required_n"] > 0
    
    # Check KB verifications
    kb_checks = res["kb_verifications"]
    assert len(kb_checks) > 0
    for check in kb_checks:
        assert "kb_verified" in check
        assert check["kb_verified"] is True


def test_gearbox_calculations():
    params = {
        "power_kw": 30.0,
        "input_speed_rpm": 1440.0,
        "output_speed_rpm": 360.0,
        "stages": 1,
        "material_id": "steel_4140",
        "fos": 2.0,
        "gear_type": "spur",
        "teeth_pinion": 18,
    }
    res = run_calculation("gearbox", params)
    
    assert "calculations" in res
    assert "dimensions" in res
    assert "safety" in res
    assert "kb_verifications" in res
    
    dims = res["dimensions"]
    assert dims["module_mm"] > 0
    assert dims["pinion_teeth"] == 18
    assert dims["gear_teeth"] == 72  # 1440 / 360 = 4.0 ratio; 18 * 4 = 72 teeth
    assert dims["center_distance_mm"] == round((dims["pinion_pitch_dia_mm"] + dims["gear_pitch_dia_mm"]) / 2, 2)
    assert dims["addendum_mm"] == dims["module_mm"]
    assert dims["dedendum_mm"] == round(1.25 * dims["module_mm"], 2)
    
    # Check KB verifications
    kb_checks = res["kb_verifications"]
    assert len(kb_checks) > 0
    for check in kb_checks:
        assert "kb_verified" in check
        assert check["kb_verified"] is True


def test_cam_calculations():
    params = {
        "cam_speed_rpm": 600.0,
        "follower_lift_mm": 20.0,
        "profile_type": "shm",
        "follower_type": "roller",
        "base_circle_radius_mm": 50.0,
        "rise_angle_deg": 90.0,
        "dwell_angle_deg": 60.0,
        "fos": 2.0,
    }
    res = run_calculation("cam", params)
    
    assert "calculations" in res
    assert "dimensions" in res
    assert "safety" in res
    
    dims = res["dimensions"]
    assert dims["base_circle_radius_mm"] == 50.0
    assert dims["max_radius_mm"] == 70.0
    assert dims["rise_angle_deg"] == 90.0
    assert dims["dwell_angle_deg"] == 60.0
    assert dims["return_angle_deg"] == 210.0
    assert "profile_table" in dims
    
    # Profile table must have exactly 73 points (0 to 360 in 5 deg increments)
    pts = dims["profile_table"]
    assert len(pts) == 73
    assert pts[0]["angle_deg"] == 0
    assert pts[0]["radius_mm"] == 50.0
    assert pts[72]["angle_deg"] == 360
    assert pts[72]["radius_mm"] == 50.0
    # At full lift (90 to 150 deg), radius should be 70.0
    assert pts[18]["angle_deg"] == 90
    assert pts[18]["radius_mm"] == 70.0
    assert pts[30]["angle_deg"] == 150
    assert pts[30]["radius_mm"] == 70.0


def test_custom_part_calculations():
    params = {
        "archetype": "flange",
        "outer_diameter_mm": 120.0,
        "thickness_mm": 15.0,
        "material_id": "steel_1045",
        "tolerance_class": "ISO 2768-f (Fine)",
        "surface_finish": "1.6 (Polished)",
        "load_direction": "dynamic",
        "quantity": 150,
    }
    res = run_calculation("custom", params)
    
    assert "calculations" in res
    assert "dimensions" in res
    assert "safety" in res
    
    dims = res["dimensions"]
    assert dims["archetype"] == "flange"
    assert dims["length_mm"] == 120.0
    assert dims["width_mm"] == 120.0
    assert dims["height_mm"] == 15.0
    assert dims["tolerance_class"] == "ISO 2768-f (Fine)"
    assert dims["surface_finish"] == "1.6 (Polished)"
    
    safety = res["safety"]
    # Check warning/recommendation routing
    assert any("Fine tolerance" in r for r in safety["recommendations"])
    assert any("Polished finish" in r for r in safety["recommendations"])
    assert any("Dynamic/combined loading" in w for w in safety["warnings"])
    assert any("Batch of 150" in r for r in safety["recommendations"])
