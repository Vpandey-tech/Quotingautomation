# ACCU DESIGN — Manufacturing Quoting & Text-to-CAD Automation System

An enterprise-grade, AI-powered mechanical design engineering and instant manufacturing quotation platform. Accelerates manual estimation and CAD drafting into an automated pipeline: from **natural-language specification** to **deterministic parametric 3D CAD (.STEP solid)**, **engineering analysis**, and **live INR manufacturing quotation**.

---

## 🚀 Key Modules & Capabilities

### 1. 🤖 AI-Guided Text-to-CAD & Design Automation (`/design`)
* **1-Pass Gemini Multimodal Spec-Intake**: Single LLM intake call with strict call budget enforcement ($\le 3$ calls per design session) that extracts structured engineering parameters and identifies the component family.
* **11 Parametric Component Families**:
  * ⚙️ **Shaft**: Drive shafts, stepped axles, spindles (power, speed, torque, keyways, FOS).
  * 🔩 **Flange**: Pipe flanges, mounting rings, PCD bolt circles, center bores.
  * 🪟 **Base Plate**: Flat plates with rectangular or circular hole grid patterns.
  * 📐 **Bracket**: L-brackets, U-brackets, flat mounting plates with gusset reinforcement.
  * 🧱 **Spacer / Bushing**: Standoffs, bushings, collars with bore and outer diameter.
  * ↕️ **Lever Arm**: Pivot arms and linkages with dual bore configurations.
  * 🏠 **Housing / Enclosure**: Hollow casings, shells, electronics enclosures.
  * ⭕ **Bearing Selection**: Deep groove ball / roller bearing sizing by load, speed, $L_{10}$ life.
  * ⚙️⚙️ **Gearbox Transmission**: Spur and helical gear train ratio and stage solver.
  * 🌀 **Cam Profile**: Disc cam motion profiles (Simple Harmonic, Cycloidal, Parabolic).
  * ✦ **Custom Part**: Freeform mechanical part intake with smart archetype mapping.
* **Interactive Specification Card with Inline Editing**:
  * Live click-to-edit for any parameter key with immediate delta `PATCH /api/design/sessions/{id}/params`.
  * Visual feedback: pending/dirty edit detection (amber ring) and saved confirmation (green flash).
  * Guided batch input forms with contextual hints, unit badges, and min/max range guards.
* **Progressive Workflow Rail**:
  * **Step 1**: Gather Specifications (Form + NLP extraction + Progress tracking).
  * **Step 2**: Engineering Analysis (Shigley's machine design formulas, safety factor verification, PDF generation).
  * **Step 3**: 3D CAD & Quoting Handoff (Deterministic OpenCASCADE solid build, exact volume/surface area measurement, seamless handoff).

---

### 2. 🧮 Deterministic Engineering Calculation Engine
* **Pure Python Shigley & ISO Compliance**: Eliminates LLM arithmetic hallucination by running verified formulas in Python.
* **Mechanical Safety Analysis**:
  * Torsional and bending shear stresses ($\tau = \frac{16T}{\pi d^3}$, $\sigma_b = \frac{32M}{\pi d^3}$).
  * Combined von Mises equivalent stress ($\sigma_e = \sqrt{\sigma_b^2 + 3\tau^2}$).
  * Factor of Safety (FOS) evaluation against ASME and ISO allowable yield limits.
* **Automated Engineering Reports**: Auto-generates branded PDF and Markdown calculation reports.

---

### 3. 🛠️ Parametric 3D CAD Solid Engine (`build123d` + OpenCASCADE)
* **Deterministic Geometry Synthesis**: Generates valid, watertight, manifold **AP242 STEP solids** (`.step`) with zero LLM in the CAD loop.
* **Code-Only DFM (Design for Manufacturability) Preflight Gates**:
  * Minimum CNC tool wall thickness enforcement ($\ge 0.8\text{ mm}$).
  * Minimum bore and PCD geometric envelope constraints.
  * Watertight topology and positive OpenCASCADE volume validation.
* **Fallback Error Explanation**: If geometric parameters violate manufacturing constraints, a targeted reasoning prompt explains the exact conflict in plain language.

---

### 4. 💰 Live Manufacturing Quoting Engine (`/quote`)
* **Dual Input Modes**:
  * **Direct 3D STEP Upload**: Native B-Rep topology analysis via `build123d` / `OCP` (calculates exact volume, surface area, bounding box, hole depths/types, edge perimeters, and complexity tier).
  * **2D Engineering Drawing (PDF)**: Multimodal Gemini AI drawing analysis to parse orthographic projections, isometric views, multi-part BOMs, and H7 tolerance callouts.
* **Live Material Pricing (INR)**: Real-time metal spot prices via global market APIs with live USD $\to$ INR currency conversion.
* **Cycle Time & Costing Breakdown**:
  * Machine setup and operational machining cycle times for 3-Axis / 5-Axis CNC Milling, CNC Turning, and Wire EDM.
  * Raw material stock size optimization (Round bar, Plate, Hex bar).
  * Tolerance multipliers (Standard, Precision, Ultra-Precision) and surface treatment pricing.
  * Profit margin controls (15%–30%), regional labor adjustments (Pune, Ahmedabad, Mumbai, Chennai, Bengaluru, Delhi), and 18% GST calculation.
* **Commercial PDF Generation**: Downloadable formal quotation and itemized BOM PDF generation using `fpdf2` and Unicode typography.

---

### 5. 👁️ Interactive 3D WebGL Viewer
* Embedded Three.js / React Three Fiber viewport with in-browser OpenCASCADE mesh rendering.
* Interactive 3D bounding box dimension callouts (X, Y, Z in mm), coordinate axes gizmo, and orbit controls.

---

## 🏗️ Architecture & Technology Stack

```
Quotingautomation/
├── backend/
│   ├── main.py                     # FastAPI backend entrypoint & quoting routes
│   ├── engineering_routes.py       # AIAE Design Phase API (/api/design/*)
│   ├── services/
│   │   ├── costing.py              # Machining cycle time & cost calculation
│   │   ├── pricing.py              # Metal material database & live spot rates
│   │   ├── currency.py             # USD to INR exchange rates
│   │   ├── pdf.py                  # Formal commercial PDF quote generator
│   │   ├── pdf_analyzer.py         # Gemini 2D drawing multimodal parser
│   │   └── engineering/
│   │       ├── cad_engine.py       # build123d / OpenCASCADE parametric CAD builder
│   │       ├── math_engine.py      # Shigley's machine design formula solver
│   │       ├── params.py           # Component specs, aliases, and clarification rules
│   │       ├── report_generator.py # Engineering analysis PDF reports
│   │       ├── knowledge_lookup.py # 250+ engineering formula KB & validation
│   │       └── hardware.py         # Standard off-the-shelf fasteners & parts
│   └── tests/
│       ├── test_design_refactor.py # CAD generation & DFM preflight tests
│       ├── test_api_contract.py    # End-to-end API intake & quoting handoff tests
│       └── test_calculations.py    # Engineering formula unit tests
├── src/
│   ├── pages/
│   │   ├── DesignDashboard.jsx     # 11 component families catalogue & session manager
│   │   ├── DesignSession.jsx       # 3-step linear design workspace & inline editor
│   │   └── Landing.jsx             # Main platform landing page
│   ├── components/
│   │   ├── quote/                  # Quoting panel, costing sliders & pricing breakdown
│   │   ├── viewer/                 # Three.js 3D WebGL B-Rep viewer & bounding box
│   │   └── admin/                  # Live metal rates & exchange rates dashboard
│   ├── App.jsx                     # Route definitions & global context
│   └── main.jsx                    # React root
```

---

## 🔧 Setup & Installation

### Prerequisites
* **Node.js**: v18.0 or higher
* **Python**: 3.10 or 3.11
* **API Keys**: Google Gemini API key (set in `.env`)

### 1. Backend Setup
```powershell
# Navigate to backend
cd backend

# Create & activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Create a .env file in backend/:
# GEMINI_API_KEY="your_google_gemini_api_key"
# METALS_DEV_API_KEY="your_metals_dev_api_key" # (Optional)

# Start backend server
py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```powershell
# In project root:
npm install

# Start Vite development server
npm run dev
```

Visit **`http://localhost:5173`** to access the application.

---

## 🧪 Running Automated Tests

```powershell
# 1. Test CAD Generator across all 11 component families & DFM preflight
py backend/tests/test_design_refactor.py

# 2. Test End-to-End Design Session Intake, Report & Quoting Handoff Contract
py backend/tests/test_api_contract.py

# 3. Test Engineering Formulas & Calculations
py backend/tests/test_calculations.py
```

---

## 📄 License & Attribution
*Designed and engineered exclusively for ACCU DESIGN.*
