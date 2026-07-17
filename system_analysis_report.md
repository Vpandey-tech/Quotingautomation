# ACCU DESIGN Quoting Automation System - Detailed Analysis Report

## 1. System Overview
The **ACCU DESIGN Quoting Automation System** is an AI-powered manufacturing estimation engine. It allows engineers to quickly upload 3D models (.STEP files) or 2D Drawings (.PDF files) and receive immediate, precise, and professional quotations. The system leverages live global market prices for metals and automates complex costing logic based on geometric features and manufacturing rules.

---

## 2. Core Features

### 2.1 Intelligent File Analysis
- **3D Geometry Processing (STEP files):**
  - Uses **CadQuery** and **OpenCASCADE** (via Python) to extract precise geometric properties.
  - Automatically calculates bounding box dimensions (X, Y, Z), precise calculated volume, surface area, and topology metrics (faces, edges, vertices).
  - Detects complex features such as holes (diameter, depth, blind vs. through).
  - Assigns an automatic complexity score (Simple, Moderate, Complex, Very Complex) based on the number of faces, edges, and holes.
- **2D Drawing Parsing (PDF files):**
  - Employs **Google Gemini AI 2.5 (Flash/Pro)** Vision Models to visually parse industrial drawings.
  - Extracts Multi-part Bill of Materials (BOM), identifying quantities, materials, bounding boxes, tolerances (e.g. H7), and required manufacturing processes.
  - Detects "Buyout Items" (off-the-shelf) vs "Machined Parts".

### 2.2 Live Pricing & Economics Engine
- **Live Metal Pricing:** Integrates with `metals.dev` API to fetch real-time spot prices for raw materials (USD/kg).
- **Dynamic Exchange Rate:** Retrieves live USD → INR exchange rates to compute final costs in Indian Rupees.
- **Material Estimation Engine:** Calculates raw material requirements based on part bounding box (envelope method), material density, stock type (round bar, plate, hex bar), and calculates material utilization percentages.
- **Costing Algorithm:**
  - Evaluates Machining Setup Time & Operation Time based on part complexity and selected processes (e.g., CNC Turning, 3-Axis / 5-Axis Milling, Wire EDM).
  - Integrates adjustable parameters like scrap factors, margin padding (% profit), internal logistics, and 18% GST taxation.

### 2.3 Parametric Engineering Rules Engine
- Evaluates mechanical engineering rules and formulas based on strict industry standards (ASME, ISO, AGMA) using Python's deterministic math (via `sympy` and `forallpeople`).
- Uses Gemini AI strictly as a secondary validation tool.
- Capable of generating parametric CAD geometries (.STEP) using **build123d** based on dynamically calculated dimensions.
- Auto-generates detailed calculation PDFs mimicking Mathcad layouts via the **handcalcs** library.

### 2.4 High-Fidelity PDF Quotation Generation
- Built with **fpdf2** ensuring strict industrial layouts.
- Formats include Single Component Quote and Assembly BOM Quote.
- Incorporates dynamic multiline tracking, strict pagination, automated amount-in-words translation, and inclusion of HSN codes and taxes.

### 2.5 Interactive Frontend Application
- **Modern UI:** Built on React 18 and Vite. Styled with Tailwind CSS implementing Glassmorphism and Dark Mode.
- **WebGL 3D Viewer:** Renders uploaded STEP models interactively in the browser using `@react-three/fiber` and `occt-import-js`.
- **ACCU AI Copilot:** A chat assistant integrated into the UI. Users can give natural language commands like "Change material to EN-8" and the AI securely modifies the underlying quote configuration state.

---

## 3. Technology Stack & Architecture

### Frontend (User Interface)
- **Framework:** React 18 with Vite
- **3D Engine:** `three.js`, `@react-three/fiber`, `@react-three/drei`, `occt-import-js`
- **Styling:** Tailwind CSS 3, PostCSS, Lucide React (Icons)
- **State Management:** React hooks and React Router

### Backend (API Server)
- **Framework:** FastAPI (Asynchronous execution using `uvicorn`)
- **Geometry Kernels:** `CadQuery`, `build123d`, `OpenCASCADE`
- **Math & Units:** `sympy`, `forallpeople`
- **PDF Generation:** `fpdf2`, `handcalcs`
- **AI Integration:** `google-generativeai` (Gemini)
- **HTTP Client:** `httpx` (for live APIs)

### Data Workflow
1. User uploads a file (STEP or PDF) via the frontend.
2. Request hits the `/api/analyze` or `/api/analyze/pdf` endpoints.
3. Backend processes the geometry or uses AI to parse the drawing, returning a structured JSON containing metrics.
4. The React application displays the metrics and 3D preview.
5. The frontend concurrently calls `/api/prices` to get live material costs and exchange rates.
6. User adjustments (manual or via `/api/chat` copilot) recalculate the quote.
7. Final configuration is sent to `/api/quote/pdf` or `/api/quote/bom-pdf` for formal quotation generation.

---

## 4. Key Parameters & Endpoints

### 4.1 Quote Configuration Parameters
When generating a quote (`QuoteRequest`), the following detailed parameters are sent:
- `geometry`: B-Rep geometry metrics (X, Y, Z sizes, volume, surface area, holes, centroid, complexity score).
- `material_id`: ID of the material (e.g., `aluminum_6061`).
- `process_ids`: List of required processes (e.g., `["cnc_milling_3ax", "cnc_turning"]`).
- `tolerance_id`: Tolerance tier (e.g., `standard`, `precision`, `ultra`).
- `quantity`: Number of parts to produce.
- `surface_treatment_ids`: Optional surface finishing list.
- `profit_margin_pct`: Desired profit margin (15% to 30%).
- `include_setup_cost`: Boolean flag to include machine setup & amortization.
- `include_drilling_surcharge`: Boolean flag to apply surcharge for drilling holes.
- `hole_count_override`: Allows manual override of detected holes.
- `stock_type`: Type of raw material stock (`round_bar`, `plate`, `hex_bar`).

### 4.2 Main API Endpoints
- **GET `/api/health`:** System status, version, current INR exchange rate.
- **GET `/api/materials` / `/api/processes` / `/api/tolerances` / `/api/stock-sizes`:** Retrieves base parameters and rates for configuration dropdowns.
- **GET `/api/exchange-rate` / `/api/prices`:** Retrieves live spot market prices and conversion rates.
- **POST `/api/analyze`:** Extracts CAD features and dimensions from an uploaded STEP file.
- **POST `/api/analyze/pdf`:** Extracts dimensions and BOM structures from an uploaded PDF drawing.
- **POST `/api/material-estimate`:** Calculates the raw material required and estimates cost based on stock utilization.
- **POST `/api/validate-material`:** Cross-validates the internal material calculation with the Gemini LLM.
- **POST `/api/chat`:** Interprets user chat prompts to mutate the quotation settings state.
- **POST `/api/quote`:** Computes the total cost (raw material + machining + surface treatment + margin) and returns it in JSON.
- **POST `/api/quote/pdf` / `/api/quote/bom-pdf`:** Generates and returns a downloadable industrial PDF quotation.
