import json

file_path = 'backend/services/engineering/knowledge_base.json'

new_data = [
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "Pitch-Line Velocity (U.S. Customary)",
    "type": "formula",
    "formula_string": "V = (3.14159 * d_P * n_P) / 12",
    "inputs": [
      {"symbol": "d_P", "description": "Pitch diameter of the pinion", "unit": "in"},
      {"symbol": "n_P", "description": "Pinion speed", "unit": "rev/min"}
    ],
    "output": {"symbol": "V", "description": "Pitch-line velocity", "unit": "ft/min"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "Transmitted Tangential Load (U.S. Customary)",
    "type": "formula",
    "formula_string": "W_t = (33000 * H) / V",
    "inputs": [
      {"symbol": "H", "description": "Power transmitted", "unit": "hp"},
      {"symbol": "V", "description": "Pitch-line velocity", "unit": "ft/min"}
    ],
    "output": {"symbol": "W_t", "description": "Transmitted tangential load", "unit": "lbf"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "Pitch-Line Velocity (SI Units)",
    "type": "formula",
    "formula_string": "V = (3.14159 * d_P * n_P) / 60000",
    "inputs": [
      {"symbol": "d_P", "description": "Pitch diameter of the pinion", "unit": "mm"},
      {"symbol": "n_P", "description": "Pinion speed", "unit": "rev/min"}
    ],
    "output": {"symbol": "V", "description": "Pitch-line velocity", "unit": "m/s"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "Transmitted Tangential Load (SI Units)",
    "type": "formula",
    "formula_string": "W_t = (60000000 * H) / (3.14159 * d_P * n_P)",
    "inputs": [
      {"symbol": "H", "description": "Power transmitted", "unit": "kW"},
      {"symbol": "d_P", "description": "Pitch diameter of the pinion", "unit": "mm"},
      {"symbol": "n_P", "description": "Pinion speed", "unit": "rev/min"}
    ],
    "output": {"symbol": "W_t", "description": "Transmitted tangential load", "unit": "N"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "AGMA Bending Stress (U.S. Customary)",
    "type": "formula",
    "formula_string": "sigma = W_t * K_o * K_v * K_s * (P_d / F) * (K_m * K_B / J)",
    "inputs": [
      {"symbol": "W_t", "description": "Transmitted tangential load", "unit": "lbf"},
      {"symbol": "K_o", "description": "Overload factor", "unit": "dimensionless"},
      {"symbol": "K_v", "description": "Dynamic factor", "unit": "dimensionless"},
      {"symbol": "K_s", "description": "Size factor", "unit": "dimensionless"},
      {"symbol": "P_d", "description": "Transverse diametral pitch", "unit": "teeth/in"},
      {"symbol": "F", "description": "Net face width of the narrowest member", "unit": "in"},
      {"symbol": "K_m", "description": "Load-distribution factor", "unit": "dimensionless"},
      {"symbol": "K_B", "description": "Rim-thickness factor", "unit": "dimensionless"},
      {"symbol": "J", "description": "AGMA Geometry factor for bending strength", "unit": "dimensionless"}
    ],
    "output": {"symbol": "sigma", "description": "AGMA Bending Stress", "unit": "psi"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "AGMA Bending Stress (SI Units)",
    "type": "formula",
    "formula_string": "sigma = W_t * K_o * K_v * K_s * (1 / (b * m_t)) * (K_m * K_B / J)",
    "inputs": [
      {"symbol": "W_t", "description": "Transmitted tangential load", "unit": "N"},
      {"symbol": "K_o", "description": "Overload factor", "unit": "dimensionless"},
      {"symbol": "K_v", "description": "Dynamic factor", "unit": "dimensionless"},
      {"symbol": "K_s", "description": "Size factor", "unit": "dimensionless"},
      {"symbol": "b", "description": "Face width", "unit": "mm"},
      {"symbol": "m_t", "description": "Transverse module", "unit": "mm/tooth"},
      {"symbol": "K_m", "description": "Load-distribution factor", "unit": "dimensionless"},
      {"symbol": "K_B", "description": "Rim-thickness factor", "unit": "dimensionless"},
      {"symbol": "J", "description": "AGMA Geometry factor for bending strength", "unit": "dimensionless"}
    ],
    "output": {"symbol": "sigma", "description": "AGMA Bending Stress", "unit": "MPa"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "AGMA Contact Stress",
    "type": "formula",
    "formula_string": "sigma_c = C_p * ( W_t * K_o * K_v * K_s * (K_m / (d_P * F * I)) * C_f )**(1/2)",
    "inputs": [
      {"symbol": "C_p", "description": "Elastic coefficient", "unit": "sqrt(psi) or sqrt(MPa)"},
      {"symbol": "W_t", "description": "Transmitted tangential load", "unit": "lbf or N"},
      {"symbol": "K_o", "description": "Overload factor", "unit": "dimensionless"},
      {"symbol": "K_v", "description": "Dynamic factor", "unit": "dimensionless"},
      {"symbol": "K_s", "description": "Size factor", "unit": "dimensionless"},
      {"symbol": "K_m", "description": "Load-distribution factor", "unit": "dimensionless"},
      {"symbol": "d_P", "description": "Pitch diameter of the pinion", "unit": "in or mm"},
      {"symbol": "F", "description": "Net face width", "unit": "in or mm"},
      {"symbol": "I", "description": "AGMA Geometry factor for pitting resistance", "unit": "dimensionless"},
      {"symbol": "C_f", "description": "Surface condition factor", "unit": "dimensionless"}
    ],
    "output": {"symbol": "sigma_c", "description": "Maximum Hertzian contact stress", "unit": "psi or MPa"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "AGMA Allowable Bending Stress",
    "type": "formula",
    "formula_string": "sigma_all = (S_t * Y_N) / (K_T * K_R)",
    "inputs": [
      {"symbol": "S_t", "description": "AGMA Bending strength of the material", "unit": "psi or MPa"},
      {"symbol": "Y_N", "description": "Stress-cycle factor for bending strength", "unit": "dimensionless"},
      {"symbol": "K_T", "description": "Temperature factor", "unit": "dimensionless"},
      {"symbol": "K_R", "description": "Reliability factor", "unit": "dimensionless"}
    ],
    "output": {"symbol": "sigma_all", "description": "Allowable bending stress", "unit": "psi or MPa"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "AGMA Allowable Contact Stress",
    "type": "formula",
    "formula_string": "sigma_c_all = (S_c * Z_N * C_H) / (K_T * K_R)",
    "inputs": [
      {"symbol": "S_c", "description": "AGMA Surface endurance strength of the material", "unit": "psi or MPa"},
      {"symbol": "Z_N", "description": "Stress-cycle factor for pitting resistance", "unit": "dimensionless"},
      {"symbol": "C_H", "description": "Hardness-ratio factor", "unit": "dimensionless"},
      {"symbol": "K_T", "description": "Temperature factor", "unit": "dimensionless"},
      {"symbol": "K_R", "description": "Reliability factor", "unit": "dimensionless"}
    ],
    "output": {"symbol": "sigma_c_all", "description": "Allowable contact stress", "unit": "psi or MPa"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "Bending Safety Factor",
    "type": "formula",
    "formula_string": "S_F = sigma_all / sigma",
    "inputs": [
      {"symbol": "sigma_all", "description": "Allowable bending stress", "unit": "psi or MPa"},
      {"symbol": "sigma", "description": "AGMA Bending Stress", "unit": "psi or MPa"}
    ],
    "output": {"symbol": "S_F", "description": "Bending Safety Factor", "unit": "dimensionless"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "Pitting (Wear) Safety Factor",
    "type": "formula",
    "formula_string": "S_H = sigma_c_all / sigma_c",
    "inputs": [
      {"symbol": "sigma_c_all", "description": "Allowable contact stress", "unit": "psi or MPa"},
      {"symbol": "sigma_c", "description": "Maximum Hertzian contact stress", "unit": "psi or MPa"}
    ],
    "output": {"symbol": "S_H", "description": "Pitting (Wear) Safety Factor", "unit": "dimensionless"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "Dynamic Factor (Cut or Milled Profile)",
    "type": "formula",
    "formula_string": "K_v = (1200 + V) / 1200",
    "inputs": [
      {"symbol": "V", "description": "Pitch-line velocity", "unit": "ft/min"}
    ],
    "output": {"symbol": "K_v", "description": "Dynamic factor", "unit": "dimensionless"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "Dynamic Factor (Hobbed or Shaped Profile)",
    "type": "formula",
    "formula_string": "K_v = (50 + V**(1/2)) / 50",
    "inputs": [
      {"symbol": "V", "description": "Pitch-line velocity", "unit": "ft/min"}
    ],
    "output": {"symbol": "K_v", "description": "Dynamic factor", "unit": "dimensionless"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Spur and Helical Gears (AGMA Standards)",
    "topic": "Dynamic Factor (Shaved or Ground Profile)",
    "type": "formula",
    "formula_string": "K_v = (78 + V**(1/2)) / 78",
    "inputs": [
      {"symbol": "V", "description": "Pitch-line velocity", "unit": "ft/min"}
    ],
    "output": {"symbol": "K_v", "description": "Dynamic factor", "unit": "dimensionless"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Rolling-Contact Bearings",
    "topic": "Equivalent Dynamic Radial Load",
    "type": "formula",
    "formula_string": "F_e = X * V * F_r + Y * F_a",
    "inputs": [
      {"symbol": "X", "description": "Radial load factor", "unit": "dimensionless"},
      {"symbol": "V", "description": "Rotation factor", "unit": "dimensionless"},
      {"symbol": "F_r", "description": "Applied radial load", "unit": "lbf or N"},
      {"symbol": "Y", "description": "Axial load factor", "unit": "dimensionless"},
      {"symbol": "F_a", "description": "Applied axial (thrust) load", "unit": "lbf or N"}
    ],
    "output": {"symbol": "F_e", "description": "Equivalent dynamic radial load", "unit": "lbf or N"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Rolling-Contact Bearings",
    "topic": "Axial Load Negligibility Check",
    "type": "rule",
    "formula_string": None,
    "inputs": [
      {"symbol": "F_a", "description": "Applied axial load", "unit": "lbf or N"},
      {"symbol": "V", "description": "Rotation factor", "unit": "dimensionless"},
      {"symbol": "F_r", "description": "Applied radial load", "unit": "lbf or N"},
      {"symbol": "e", "description": "Catalog specific threshold", "unit": "dimensionless"}
    ],
    "output": {"symbol": "F_e", "description": "Simplified equivalent load", "unit": "lbf or N"},
    "rule_logic": "IF F_a / (V * F_r) <= e THEN axial load is negligible, set X = 1, Y = 0, AND F_e = V * F_r.",
    "table_data": None
  },
  {
    "domain": "Rolling-Contact Bearings",
    "topic": "Required Basic Rating Life",
    "type": "formula",
    "formula_string": "L_D = (60 * h_D * n_D) / 10**6",
    "inputs": [
      {"symbol": "h_D", "description": "Desired design hours", "unit": "hours"},
      {"symbol": "n_D", "description": "Design speed", "unit": "rev/min"}
    ],
    "output": {"symbol": "L_D", "description": "Required basic rating life", "unit": "millions of revolutions"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Rolling-Contact Bearings",
    "topic": "Dimensionless Design Life",
    "type": "formula",
    "formula_string": "x_D = L_D / L_R",
    "inputs": [
      {"symbol": "L_D", "description": "Desired design life", "unit": "millions of revolutions"},
      {"symbol": "L_R", "description": "Manufacturer's rating life threshold", "unit": "millions of revolutions"}
    ],
    "output": {"symbol": "x_D", "description": "Dimensionless multiple of rating life", "unit": "dimensionless"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Rolling-Contact Bearings",
    "topic": "Catalog Rating for 90% Reliability (Standard Equation)",
    "type": "formula",
    "formula_string": "C_10 = a_f * F_D * (L_D / L_R)**(1/a)",
    "inputs": [
      {"symbol": "a_f", "description": "Application factor (shock/impact modifier)", "unit": "dimensionless"},
      {"symbol": "F_D", "description": "Desired design load (Equivalent Radial Load F_e)", "unit": "lbf or N"},
      {"symbol": "L_D", "description": "Desired design life", "unit": "millions of revolutions"},
      {"symbol": "L_R", "description": "Manufacturer's rating life threshold", "unit": "millions of revolutions"},
      {"symbol": "a", "description": "Load-life exponent", "unit": "dimensionless"}
    ],
    "output": {"symbol": "C_10", "description": "Required basic dynamic load rating", "unit": "lbf or N"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Rolling-Contact Bearings",
    "topic": "Catalog Rating for Higher Reliability (Weibull Equation)",
    "type": "formula",
    "formula_string": "C_10 = a_f * F_D * ( x_D / ( x_0 + (theta - x_0) * (1 - R_D)**(1/b) ) )**(1/a)",
    "inputs": [
      {"symbol": "a_f", "description": "Application factor", "unit": "dimensionless"},
      {"symbol": "F_D", "description": "Desired design load", "unit": "lbf or N"},
      {"symbol": "x_D", "description": "Dimensionless design life", "unit": "dimensionless"},
      {"symbol": "x_0", "description": "Weibull guaranteed dimensionless life parameter", "unit": "dimensionless"},
      {"symbol": "theta", "description": "Weibull characteristic dimensionless life parameter", "unit": "dimensionless"},
      {"symbol": "R_D", "description": "Desired reliability", "unit": "dimensionless"},
      {"symbol": "b", "description": "Weibull shape parameter", "unit": "dimensionless"},
      {"symbol": "a", "description": "Load-life exponent", "unit": "dimensionless"}
    ],
    "output": {"symbol": "C_10", "description": "Required basic dynamic load rating for specified reliability", "unit": "lbf or N"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Rolling-Contact Bearings",
    "topic": "Equivalent Static Load",
    "type": "formula",
    "formula_string": "F_0e = X_0 * F_r + Y_0 * F_a",
    "inputs": [
      {"symbol": "X_0", "description": "Static radial load factor", "unit": "dimensionless"},
      {"symbol": "F_r", "description": "Applied radial load", "unit": "lbf or N"},
      {"symbol": "Y_0", "description": "Static axial load factor", "unit": "dimensionless"},
      {"symbol": "F_a", "description": "Applied axial load", "unit": "lbf or N"}
    ],
    "output": {"symbol": "F_0e", "description": "Equivalent static load", "unit": "lbf or N"},
    "rule_logic": None,
    "table_data": None
  },
  {
    "domain": "Rolling-Contact Bearings",
    "topic": "Static Loading Verification",
    "type": "rule",
    "formula_string": None,
    "inputs": [
      {"symbol": "C_0", "description": "Basic static load rating", "unit": "lbf or N"},
      {"symbol": "n_s", "description": "Static factor of safety", "unit": "dimensionless"},
      {"symbol": "F_0e", "description": "Equivalent static load", "unit": "lbf or N"}
    ],
    "output": None,
    "rule_logic": "IF C_0 >= n_s * F_0e THEN bearing prevents permanent plastic deformation (brinelling) ELSE bearing fails static check.",
    "table_data": None
  },
  {
    "domain": "Rolling-Contact Bearings",
    "topic": "Typical Weibull Parameters (Manufacturer 2)",
    "type": "table",
    "formula_string": None,
    "inputs": None,
    "output": None,
    "rule_logic": None,
    "table_data": {
      "Guaranteed dimensionless life (x_0)": 0.02,
      "Characteristic life (theta)": 4.439,
      "Shape parameter (b)": 1.483,
      "Rating life (L_R)": 1e6
    }
  }
]

try:
    with open(file_path, 'r') as f:
        data = json.load(f)
    data.extend(new_data)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
