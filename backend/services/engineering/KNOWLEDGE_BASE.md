# 📘 Engineering Knowledge Base (AIAE System)
### Source-Aligned with EngineersEdge, ASME, AGMA, ISO, and Standard Texts (Shigley)

---

# 1. SHAFT DESIGN

## 1.1 Required Input Parameters
- Power transmitted (P) [kW]
- Rotational speed (N) [RPM]
- Torque (T) [N·m]
- Bending moment (M) [N·m]
- Material properties:
  - Yield strength (Sy)
  - Ultimate strength (Sut)
- Factor of safety (n)
- Shock and fatigue factors:
  - Kb (bending shock factor)
  - Kt (torsion shock factor)

---

## 1.2 Torque Calculation

```
T = (9550 * P) / N
```

Where:
- T = Torque [N·m]
- P = Power [kW]
- N = Speed [RPM]

---

## 1.3 Equivalent Torque (ASME)

```
Te = √((Kb * M)^2 + (Kt * T)^2)
```

Where:
- Te = Equivalent torque
- M = Bending moment
- T = Torque
- Kb = Bending shock factor
- Kt = Torsion shock factor

---

## 1.4 Maximum Shear Stress Theory (Tresca)

```
τmax = (16 * Te) / (π * d^3)
```

Design condition:

```
τmax ≤ Sy / (2 * n)
```

---

## 1.5 Von Mises Stress

```
σe = √(σ^2 + 3τ^2)
```

Where:
- σ = Bending stress = (32M) / (πd³)
- τ = Torsional stress = (16T) / (πd³)

Design condition:

```
σe ≤ Sy / n
```

---

## 1.6 Shaft Diameter (ASME Design Equation)

```
d = [ (16 / (π * τallow)) * √((Kb*M)^2 + (Kt*T)^2) ]^(1/3)
```

---

## 1.7 Deflection of Shaft

For simply supported shaft with central load:

```
δ = (W * L^3) / (48 * E * I)
```

Where:
- W = Load
- L = Length
- E = Young’s Modulus
- I = πd⁴ / 64

---

## 1.8 Critical Speed (Whirling)

```
Nc = (30 / π) * √(g / δ)
```

Where:
- Nc = Critical speed (RPM)
- g = 9.81 m/s²
- δ = deflection

---

## 1.9 Shock Factors (Typical ASME Values)

| Condition              | Kb  | Kt  |
|-----------------------|-----|-----|
| Steady load           | 1.0 | 1.0 |
| Light shock           | 1.5 | 1.2 |
| Heavy shock           | 2.0 | 1.5 |

---

# 2. GEAR DESIGN (SPUR & HELICAL)

---

## 2.1 Required Input Parameters
- Power (P)
- Speed (N)
- Module (m)
- Number of teeth (Z)
- Face width (b)
- Material properties
- Pressure angle (ϕ)

---

## 2.2 Lewis Bending Equation

```
Ft = (σ * b * m * Y)
```

Where:
- Ft = Tangential force
- σ = Allowable stress
- Y = Lewis form factor

---

## 2.3 Tangential Load

```
Ft = (1000 * P) / v
```

Where:
- v = Pitch line velocity

```
v = (π * d * N) / 60
```

---

## 2.4 Velocity Factor (Kv)

```
Kv = 3 / (3 + v)   (for cut gears)
```

Corrected load:

```
Ft' = Ft * Kv
```

---

## 2.5 AGMA Bending Stress

```
σ = (Wt * Ko * Kv * Ks * Km) / (b * m * J)
```

Where:
- Ko = Overload factor
- Ks = Size factor
- Km = Load distribution factor
- J = Geometry factor

---

## 2.6 Hertzian Contact Stress (Wear)

```
σc = Cp * √( (Ft * Ko * Kv * Ks * Km) / (b * d * I) )
```

Where:
- Cp = Elastic coefficient
- I = Geometry factor

---

## 2.7 Module Selection Guidelines

- Standard modules: 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, etc.
- Choose module based on:
  - Load capacity
  - Manufacturing constraints
  - Space availability

---

## 2.8 Helical Gear Adjustments

- Normal module:

```
mn = mt * cos(ψ)
```

- Axial thrust:

```
Fa = Ft * tan(ψ)
```

Where:
- ψ = Helix angle

---

# 3. BEARING SELECTION

---

## 3.1 Required Input Parameters
- Radial load (Fr)
- Axial load (Fa)
- Speed (N)
- Desired life (L10h)

---

## 3.2 Equivalent Dynamic Load

```
P = X * Fr + Y * Fa
```

Where:
- X, Y = Factors (from bearing tables)

---

## 3.3 Bearing Life (L10)

```
L10 = (C / P)^p
```

Where:
- C = Dynamic load rating
- p = 3 (ball bearing), 10/3 (roller)

---

## 3.4 Life in Hours

```
L10h = (L10 * 10^6) / (60 * N)
```

---

## 3.5 Static Load Check

```
Po = Xo * Fr + Yo * Fa
```

Condition:

```
Po ≤ Co
```

Where:
- Co = Static load rating

---

## 3.6 Application Factor

- Light load → 1.0
- Moderate → 1.5
- Heavy → 2.0+

---

# 4. FASTENERS & BOLTED JOINTS

---

## 4.1 Torque-Tension Relationship

```
T = K * F * d
```

Where:
- T = Torque
- K = Nut factor (~0.2 typical)
- F = Preload force
- d = Nominal diameter

---

## 4.2 Preload Calculation

```
F = 0.75 * Proof Load
```

---

## 4.3 Thread Shear Area

```
As = π * d * Le
```

Where:
- Le = Engagement length

---

## 4.4 Tensile Stress Area

```
At = (π / 4) * (d - 0.9382p)^2
```

Where:
- p = Pitch

---

## 4.5 Factor of Safety

```
n = Sy / σ
```

---

# 5. CAMS & LINKAGES

---

## 5.1 Simple Harmonic Motion (SHM)

Displacement:

```
y = (h/2) * (1 - cos(πθ/β))
```

Velocity:

```
v = (hπ / (2β)) * sin(πθ/β)
```

Acceleration:

```
a = (hπ² / (2β²)) * cos(πθ/β)
```

---

## 5.2 Cycloidal Motion

Displacement:

```
y = h * [ (θ/β) - (1/(2π)) * sin(2πθ/β) ]
```

Velocity:

```
v = (h/β) * [1 - cos(2πθ/β)]
```

Acceleration:

```
a = (2πh / β²) * sin(2πθ/β)
```

---

## 5.3 Pressure Angle

```
tan(ϕ) = (velocity) / (base circle radius)
```

Limits:
- Recommended: ≤ 30°

---

# 6. MATERIAL PROPERTIES

---

## 6.1 Standard Material Table

| Material            | Yield Strength (MPa) | UTS (MPa) | E (GPa) | Density (kg/m³) |
|---------------------|----------------------|----------|---------|----------------|
| 1018 Steel          | 370                  | 440      | 200     | 7850           |
| 1045 Steel          | 530                  | 630      | 200     | 7850           |
| 4140 Alloy Steel    | 655                  | 850      | 205     | 7850           |
| 6061-T6 Aluminum    | 276                  | 310      | 69      | 2700           |
| 7075-T6 Aluminum    | 503                  | 572      | 71      | 2810           |
| 304 Stainless Steel | 215                  | 505      | 193     | 8000           |
| Cast Iron (Gray)    | 130                  | 240      | 110     | 7200           |

---

# 7. SPRING DESIGN (HELICAL & LEAF)

---

## 7.1 HELICAL COMPRESSION SPRINGS

### Required Input Parameters
- Load (F) [N]
- Deflection (δ) [mm]
- Spring index (C = D/d)
- Wire diameter (d)
- Mean coil diameter (D)
- Number of active coils (n)
- Modulus of rigidity (G)

---

## 7.1.1 Spring Stiffness

```
k = F / δ
```

Also:

```
k = (G * d^4) / (8 * D^3 * n)
```

Where:
- k = stiffness [N/mm]
- G = shear modulus

---

## 7.1.2 Maximum Shear Stress

```
τmax = (8 * F * D * Kw) / (π * d^3)
```

Where:
- Kw = Wahl factor

---

## 7.1.3 Wahl Factor

```
Kw = ((4C - 1) / (4C - 4)) + (0.615 / C)
```

---

## 7.1.4 Deflection Equation

```
δ = (8 * F * D^3 * n) / (G * d^4)
```

---

## 7.1.5 Factor of Safety

```
n = Ssy / τmax
```

Where:
- Ssy = Shear yield strength

---

## 7.2 LEAF SPRINGS

### Maximum Stress

```
σ = (6 * F * L) / (b * t^2 * n)
```

Where:
- L = length
- b = width
- t = thickness

---

### Deflection

```
δ = (4 * F * L^3) / (E * b * t^3 * n)
```

---

# 8. PRESSURE VESSEL DESIGN

---

## 8.1 THIN CYLINDER (t < D/20)

### Hoop Stress

```
σh = (P * D) / (2 * t)
```

---

### Longitudinal Stress

```
σl = (P * D) / (4 * t)
```

---

### Required Thickness

```
t = (P * D) / (2 * σallow)
```

---

## 8.2 THICK CYLINDER (LAMÉ EQUATIONS)

### Radial Stress

```
σr = A - (B / r^2)
```

---

### Hoop Stress

```
σθ = A + (B / r^2)
```

---

### Constants

```
A = (pi * ri^2 - po * ro^2) / (ro^2 - ri^2)
B = (ri^2 * ro^2 * (po - pi)) / (ro^2 - ri^2)
```

Where:
- pi = internal pressure
- po = external pressure

---

# 9. WELDED JOINT DESIGN

---

## 9.1 Fillet Weld Strength

```
τ = F / (0.707 * h * L)
```

Where:
- h = weld size
- L = weld length

---

## 9.2 Maximum Shear Stress

```
τmax ≤ τallow
```

---

## 9.3 Eccentric Loading

```
τtotal = √(τdirect^2 + τtorsion^2)
```

---

## 9.4 Throat Thickness

```
t = 0.707 * h
```

---

# 10. FITS & TOLERANCES (ISO SYSTEM)

---

## 10.1 Basic Definitions

- **Nominal Size**: Base size
- **Tolerance**: Variation allowed
- **Deviation**: Difference from nominal

---

## 10.2 Types of Fits

| Fit Type     | Description                  |
|--------------|-----------------------------|
| Clearance    | Always clearance            |
| Transition   | May be clearance/interference |
| Interference | Always tight fit            |

---

## 10.3 Standard IT Grades

| Grade | Accuracy Level |
|-------|--------------|
| IT5   | High precision |
| IT7   | Standard machining |
| IT10  | Rough machining |

---

## 10.4 Tolerance Unit (i)

```
i = 0.45 * (D)^(1/3) + 0.001 * D
```

Where:
- D = geometric mean diameter

---

# 11. POWER SCREWS

---

## 11.1 Torque to Raise Load

```
T = (W * d/2) * [ (tanλ + μ) / (1 - μ * tanλ) ]
```

---

## 11.2 Torque to Lower Load

```
T = (W * d/2) * [ (tanλ - μ) / (1 + μ * tanλ) ]
```

---

## 11.3 Efficiency

```
η = tanλ / (tanλ + μ)
```

---

Where:
- λ = helix angle
- μ = coefficient of friction

---

# 12. BELT & CHAIN DRIVES

---

## 12.1 Belt Tension Ratio

```
T1 / T2 = e^(μθ)
```

---

## 12.2 Power Transmission

```
P = (T1 - T2) * v
```

---

## 12.3 Centrifugal Tension

```
Tc = m * v^2
```

---

## 12.4 Velocity

```
v = (π * D * N) / 60
```

---

# 13. ADVANCED AGMA FACTORS (DETAILED)

---

## 13.1 AGMA Factors

| Factor | Meaning |
|--------|--------|
| Ko     | Overload factor |
| Kv     | Dynamic factor |
| Ks     | Size factor |
| Km     | Load distribution |
| Kb     | Rim thickness |

---

## 13.2 AGMA Dynamic Factor

```
Kv = ((A + √v) / A)^B
```

Where:
- A, B = empirical constants

---

# 14. CAD PARAMETRIC MAPPING (FOR AIAE SYSTEM)

---

## 14.1 Shaft Design Mapping

| Parameter | CAD Variable |
|----------|-------------|
| Diameter | d |
| Length   | L |
| Keyway   | width, depth |

---

## 14.2 Gear Mapping

| Parameter | CAD |
|----------|-----|
| Module   | m |
| Teeth    | Z |
| Pitch dia| d = mZ |

---

## 14.3 Bearing Mapping

| Parameter | CAD |
|----------|-----|
| Bore      | d |
| Outer dia | D |
| Width     | B |

---

# 15. SAFETY FACTOR GUIDELINES

---

## 15.1 Typical Values

| Application        | Factor of Safety |
|--------------------|-----------------|
| Static load        | 1.5 – 2 |
| Dynamic load       | 2 – 3 |
| Shock load         | 3 – 5 |
| Uncertain loading  | 5+ |

---

## 15.2 Design Condition

```
Working Stress ≤ Allowable Stress
```

---

# 16. FATIGUE DESIGN (CRITICAL FOR REAL ENGINEERING)

---

## 16.1 Required Input Parameters
- Ultimate strength (Sut)
- Yield strength (Sy)
- Surface finish
- Size of component
- Loading type (axial, bending, torsion)
- Temperature
- Reliability (%)
- Stress values:
  - Maximum stress (σmax)
  - Minimum stress (σmin)

---

## 16.2 Endurance Limit (Se)

### Step 1: Rotating Beam Endurance Limit

```
Se' = 0.5 * Sut   (for steel, Sut < 1400 MPa)
```

---

### Step 2: Apply Modifying Factors

```
Se = ka * kb * kc * kd * ke * kf * Se'
```

Where:

| Factor | Meaning |
|--------|--------|
| ka | Surface finish factor |
| kb | Size factor |
| kc | Load factor |
| kd | Temperature factor |
| ke | Reliability factor |
| kf | Miscellaneous effects |

---

## 16.3 Stress Components

```
σm = (σmax + σmin) / 2   → Mean stress
σa = (σmax - σmin) / 2   → Alternating stress
```

---

## 16.4 Soderberg Criterion (Conservative)

```
(σa / Se) + (σm / Sy) ≤ 1 / n
```

---

## 16.5 Goodman Criterion

```
(σa / Se) + (σm / Sut) ≤ 1 / n
```

---

## 16.6 Gerber Criterion (Parabolic)

```
(σa / Se) + (σm / Sut)^2 ≤ 1 / n
```

---

## 16.7 Fatigue Stress Concentration

```
Kf = 1 + q (Kt - 1)
```

Where:
- q = notch sensitivity
- Kt = theoretical stress concentration

---

## 16.8 Design Logic (Fatigue)

### Steps:
1. Calculate σmax and σmin
2. Compute σa and σm
3. Determine Se
4. Apply failure theory (Goodman preferred)
5. Check factor of safety

---

# 17. FAILURE THEORIES (STATIC LOADING)

---

## 17.1 Maximum Shear Stress Theory (Tresca)

```
τmax = (σ1 - σ3) / 2
```

Condition:

```
τmax ≤ Sy / (2n)
```

---

## 17.2 Distortion Energy Theory (Von Mises)

```
σe = √[ ((σ1 - σ2)^2 + (σ2 - σ3)^2 + (σ3 - σ1)^2) / 2 ]
```

Condition:

```
σe ≤ Sy / n
```

---

## 17.3 Maximum Normal Stress (Rankine)

```
σmax ≤ Sy / n
```

---

## 17.4 When to Use What

| Material | Theory |
|---------|-------|
| Ductile | Von Mises |
| Brittle | Rankine |
| Conservative | Tresca |

---

# 18. ADVANCED BEARING SELECTION (INDUSTRIAL LEVEL)

---

## 18.1 Required Inputs
- Radial load (Fr)
- Axial load (Fa)
- Speed (N)
- Desired life (hours)
- Reliability

---

## 18.2 Equivalent Load (Detailed)

```
P = X * Fr + Y * Fa
```

Where X, Y depend on:

```
Fa / Fr ratio
```

---

## 18.3 Life Equation (ISO Standard)

```
L10 = (C / P)^p
```

---

## 18.4 Reliability Adjustment

```
Lna = a1 * L10
```

Where:

| Reliability | a1 |
|------------|----|
| 90%        | 1.0 |
| 95%        | 0.62 |
| 99%        | 0.21 |

---

## 18.5 Selection Logic

### Steps:
1. Compute equivalent load
2. Choose bearing type
3. Calculate required C
4. Select from catalog

---

# 19. ADVANCED AGMA GEAR DESIGN

---

## 19.1 Bending Stress (AGMA)

```
σ = (Wt * Ko * Kv * Ks * Km * Kb) / (b * m * J)
```

---

## 19.2 Contact Stress

```
σc = Cp * √( (Wt * Ko * Kv * Ks * Km) / (b * d * I) )
```

---

## 19.3 Safety Factors

```
SF = Allowable Stress / Actual Stress
```

---

## 19.4 Design Steps

1. Select material
2. Choose module
3. Compute forces
4. Check bending
5. Check wear
6. Iterate

---

# 20. OPTIMIZATION LOGIC (FOR AIAE SYSTEM)

---

## 20.1 Shaft Optimization

### Objective:
- Minimize weight

### Constraints:
- Stress ≤ allowable
- Deflection ≤ limit
- Critical speed > operating speed

---

## 20.2 Gear Optimization

- Minimize size
- Maximize life
- Reduce noise

---

## 20.3 Bearing Optimization

- Max life
- Minimum cost
- Compact size

---

## 20.4 General Optimization Equation

```
Minimize: f(x)
Subject to: g(x) ≤ 0
```

---

# 21. DECISION TREE LOGIC (FOR AUTOMATION)

---

## 21.1 Shaft Design Flow

1. Input power & speed
2. Calculate torque
3. Estimate bending moment
4. Apply ASME equation
5. Select diameter
6. Check:
   - Stress
   - Deflection
   - Critical speed

---

## 21.2 Gear Design Flow

1. Input power
2. Select gear type
3. Choose module
4. Calculate forces
5. Check:
   - Bending failure
   - Wear failure

---

## 21.3 Bearing Selection Flow

1. Input loads
2. Compute equivalent load
3. Calculate life
4. Select bearing

---

# 22. FULL SYSTEM INTEGRATION (AIAE AGENT)

---

## 22.1 Input Layer
- Power
- Speed
- Material
- Constraints

---

## 22.2 Processing Layer
- Apply formulas
- Iterate design
- Optimize

---

## 22.3 Output Layer
- Dimensions
- Safety factors
- CAD parameters

---

## 22.4 CAD Output Mapping

```
Shaft → Cylinder(d, L)
Gear → Involute profile(m, Z)
Bearing → Standard library
```

---

# 23. CRITICAL DESIGN WARNINGS

---

- Always include fatigue for rotating parts
- Shock factors are critical in real systems
- Never ignore stress concentration
- Always verify with multiple failure theories
- Avoid resonance (critical speed)

---

# 24. STANDARD DATA TABLES

---

## 24.1 SHAFT DESIGN — ALLOWABLE SHEAR STRESS (ASME STYLE)

| Material              | Condition     | Allowable Shear Stress (MPa) |
|----------------------|--------------|------------------------------|
| Mild Steel           | Cold Drawn   | 0.30 × Sy                    |
| Mild Steel           | Hot Rolled   | 0.18 × Sut                   |
| Alloy Steel          | Heat Treated | 0.30 × Sy                    |
| Cast Iron            | -            | 0.12 × Sut                   |

---

## 24.2 SHOCK & FATIGUE FACTORS (ASME)

| Loading Condition | Kb (Bending) | Kt (Torsion) |
|------------------|-------------|-------------|
| Steady           | 1.0         | 1.0         |
| Minor Shock      | 1.5         | 1.2         |
| Moderate Shock   | 2.0         | 1.5         |
| Heavy Shock      | 3.0         | 2.0         |

---

## 24.3 LEWIS FORM FACTOR (SPUR GEARS, 20°)

| Teeth (Z) | Y |
|----------|----|
| 12       | 0.245 |
| 16       | 0.289 |
| 20       | 0.322 |
| 24       | 0.340 |
| 30       | 0.360 |
| 40       | 0.380 |
| 60       | 0.400 |
| 100      | 0.420 |

---

## 24.4 BEARING FACTORS (BALL BEARINGS)

| Fa/Fr Ratio | X  | Y  |
|------------|----|----|
| ≤ 0.3      | 1  | 0  |
| 0.3–0.6    | 0.56 | 1.6 |
| > 0.6      | 0.44 | 2.3 |

---

## 24.5 SURFACE FINISH FACTOR (ka)

| Surface Type | ka |
|-------------|----|
| Ground      | 0.9 |
| Machined    | 0.8 |
| Hot Rolled  | 0.7 |
| As Forged   | 0.6 |

---

## 24.6 SIZE FACTOR (kb)

| Diameter (mm) | kb |
|--------------|----|
| < 7.5        | 1.0 |
| 7.5–50       | 0.85 |
| 50–250       | 0.75 |

---

## 24.7 RELIABILITY FACTOR (ke)

| Reliability (%) | ke |
|----------------|----|
| 50             | 1.0 |
| 90             | 0.897 |
| 95             | 0.868 |
| 99             | 0.814 |

---

## 24.8 STANDARD MODULE SERIES (ISO)

```
m = [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20]
```

---

# 25. API-READY JSON STRUCTURES

---

## 25.1 SHAFT DESIGN API

```json
{
  "input": {
    "power_kw": 10,
    "speed_rpm": 1000,
    "bending_moment_Nm": 500,
    "material": "C45",
    "Kb": 1.5,
    "Kt": 1.2,
    "fos": 2
  },
  "process": [
    "Calculate torque T = 9550*P/N",
    "Compute equivalent torque Te",
    "Apply ASME equation",
    "Solve for diameter"
  ],
  "output": {
    "shaft_diameter_mm": 35,
    "max_shear_stress_MPa": 80,
    "safe": true
  }
}
```

---

## 25.2 GEAR DESIGN API

```json
{
  "input": {
    "power_kw": 5,
    "speed_rpm": 1200,
    "module": 3,
    "teeth": 20,
    "face_width_mm": 30,
    "material": "EN24"
  },
  "process": [
    "Compute pitch diameter",
    "Calculate tangential load",
    "Apply Lewis equation",
    "Check AGMA stress"
  ],
  "output": {
    "bending_stress_MPa": 120,
    "contact_stress_MPa": 900,
    "safe": true
  }
}
```

---

## 25.3 BEARING SELECTION API

```json
{
  "input": {
    "Fr": 2000,
    "Fa": 500,
    "speed_rpm": 1500,
    "life_hours": 10000
  },
  "process": [
    "Compute equivalent load P",
    "Calculate L10",
    "Select bearing with C > required"
  ],
  "output": {
    "bearing_type": "6205",
    "dynamic_capacity_N": 14000,
    "life_hours": 12000
  }
}
```

---

# 26. FORMULA ENGINE (PROGRAMMABLE)

---

## 26.1 Generic Equation Format

```json
{
  "formula": "T = 9550 * P / N",
  "inputs": ["P", "N"],
  "output": "T",
  "units": {
    "P": "kW",
    "N": "RPM",
    "T": "Nm"
  }
}
```

---

## 26.2 Example — Shaft Equivalent Torque

```json
{
  "formula": "Te = sqrt((Kb*M)^2 + (Kt*T)^2)",
  "inputs": ["Kb", "M", "Kt", "T"],
  "output": "Te"
}
```

---

# 27. RULE-BASED ENGINE (AI DECISION LOGIC)

---

## 27.1 Shaft Rules

```json
{
  "if": "loading == 'shock'",
  "then": {
    "Kb": 2.0,
    "Kt": 1.5
  }
}
```

---

## 27.2 Gear Rules

```json
{
  "if": "speed > 10 m/s",
  "then": {
    "apply_velocity_factor": true
  }
}
```

---

## 27.3 Bearing Rules

```json
{
  "if": "Fa/Fr > 0.3",
  "then": {
    "use_XY_factors": true
  }
}
```

---

# 28. OPTIMIZATION DATA STRUCTURE

---

## 28.1 Optimization Model

```json
{
  "objective": "minimize_weight",
  "constraints": [
    "stress <= allowable",
    "deflection <= limit",
    "life >= required"
  ],
  "variables": ["d", "L", "material"]
}
```

---

# 29. CAD INTEGRATION FORMAT

---

## 29.1 Shaft (STEP Generator Input)

```json
{
  "type": "shaft",
  "parameters": {
    "diameter": 40,
    "length": 500,
    "keyway": true
  }
}
```

---

## 29.2 Gear

```json
{
  "type": "gear",
  "parameters": {
    "module": 3,
    "teeth": 20,
    "face_width": 30
  }
}
```
