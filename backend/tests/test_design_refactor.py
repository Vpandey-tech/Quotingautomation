import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.engineering.cad_engine import generate_cad, run_dfm_checks
from services.engineering.params import get_params_for_component, generate_clarification_questions

def run_tests():
    print("=== 1. Testing Deterministic CAD Generation across Families ===")
    test_cases = [
        ('shaft', {'diameter_mm': 25.0, 'length_mm': 200.0}, {'keyway': 'yes', 'num_keyways': 1}),
        ('flange', {'outer_diameter_mm': 140.0, 'inner_bore_diameter_mm': 30.0, 'thickness_mm': 15.0, 'bolt_circle_diameter_mm': 100.0, 'num_bolts': 4}, {'bolt_size': 'M8'}),
        ('plate_hole_pattern', {'length_mm': 150.0, 'width_mm': 100.0, 'thickness_mm': 10.0, 'hole_diameter_mm': 8.0, 'hole_count': 4}, {}),
        ('bracket', {'length_mm': 80.0, 'width_mm': 50.0, 'height_mm': 60.0, 'wall_thickness_mm': 5.0}, {'bracket_type': 'l_shape'}),
        ('spacer', {'outer_diameter_mm': 25.0, 'inner_bore_diameter_mm': 10.0, 'length_mm': 30.0}, {}),
        ('lever', {'length_mm': 120.0, 'thickness_mm': 8.0, 'width_mm': 20.0}, {'pivot_bore_diameter_mm': 10.0, 'load_end_bore_diameter_mm': 6.0}),
        ('housing', {'outer_length_mm': 120.0, 'outer_width_mm': 80.0, 'outer_height_mm': 50.0, 'wall_thickness_mm': 4.0}, {'is_hollow': 'yes'}),
    ]

    for family, dims, params in test_cases:
        res = generate_cad(family, dims, params)
        status = res.get('validation_status')
        vol = res.get('volume', 0)
        area = res.get('surface_area', 0)
        has_file = res.get('step_file') is not None
        print(f"[{family.upper()}] Status: {status} | Volume: {vol} mm3 | Area: {area} mm2 | File: {has_file}")
        assert status == 'PASS', f"{family} failed CAD generation: {res}"
        assert vol > 0, f"{family} volume non-positive"

    print("\n=== 2. Testing DFM Preflight Violations ===")
    bad_bracket = generate_cad('bracket', {'length_mm': 80.0, 'width_mm': 50.0, 'height_mm': 60.0, 'wall_thickness_mm': 0.4}, {'wall_thickness_mm': 0.4})
    print(f"[THIN WALL TEST] Status: {bad_bracket.get('validation_status')} | Error: {bad_bracket.get('error')}")
    assert bad_bracket.get('validation_status') == 'FAIL'
    assert bad_bracket.get('error', {}).get('error_code') == 'DFM_VIOLATION'

    print("\n=== 3. Testing Clarification Question Generation ===")
    qs = generate_clarification_questions('flange', {'outer_diameter_mm': 140.0})
    print(f"Generated {len(qs)} missing questions for partial flange spec:")
    for q in qs:
        print(f"  - {q.field}: {q.question}")
    assert len(qs) > 0

    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    run_tests()
