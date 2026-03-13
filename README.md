# ACCU DESIGN Quoting Automation System

## 🚀 Overview

The **ACCU DESIGN Quoting Automation System** is an AI-powered, intelligent manufacturing quotation engine. It accelerates the otherwise manual and time-consuming estimation process for engineering parts and assemblies by automatically extracting precise metrics (volumes, bounding boxes, processes, holes) straight from industrial 2D PDFs or 3D STEP files, and dynamically pricing them based on live global metal market rates and exchange APIs.

With its sleek, glassmorphic Dark Mode UI, built-in interactive 3D WebGL Viewer, and an intelligent **ACCU AI Copilot**, quoting shifts from hours of tedious spreadsheet work to a seamless, precise, and highly professional automated workflow.

---

## 🔥 Key Technical Capabilities

### 1. Intelligent File Analysis
- **3D Geometry (STEP Files):**
  - Powered by **[CadQuery](https://github.com/CadQuery/cadquery)** and **OpenCASCADE** running on the Python backend.
  - Automatically calculates bounding box dimensions (Max X, Y, Z), precise calculated volume, surface area, and complex topologies (detecting vertices, faces, edges, threaded/blind/through holes).
  - Determines complexity scores (Simple, Moderate, Complex) based on geometric features.

- **2D Drawing Parsing (PDF Files):**
  - Driven by **Google Gemini AI 2.5 Flash / Pro Multimodal Vision Models**.
  - Systematically parses industrial PDF drawings (Orthographic projections, Isometric views).
  - Extracts Multi-part Bill of Materials (BOM), determining bounding boxes, quantities, dimensions, weights, tolerances (H7, etc.), client names, and machining processes automatically.
  - Differentiates automatically between "Machined Parts" (calculated rates) and "Buyout Items" (off-the-shelf).

### 2. Live Pricing & Economics Engine
- **Global Market Integration:**
  - Pulls live metal spot prices in USD/kg (via `metals.dev` integration).
  - Converts dynamically via active live USD → INR exchange rate lookups.
- **Complex Costing Algorithm:**
  - Calculates Machine Setup Time + Operation Time based on Part Complexity, Machine Rate (per hour), Material Cost, and Manufacturing Tolerances (Multiplier parameters).
  - Calculates specific processing times varying for Turning, 3-Axis / 5-Axis Milling, Wire EDM.
  - Includes adjustable logic for Scrap factors, Margin padding (% profit), internal logistics, and Taxation (18% GST).

### 3. High-Fidelity PDF Quotation Generation
- **Authentic Industry Formatting:**
  - Employs **`fpdf2`** utilizing strict coordinates and precise Unicode fonts (`ArialUni`).
  - Capable of generating two distinct PDF formats:
    - **Single Component Quote:** Standard landscape/portrait quotation styling.
    - **BOM Assembly Quote:** Strict industrial invoice matching (including exact custom columns like `HSN`, `QTY`, `RATE`, `TAX`, dynamically numbered Total sections, and dynamically sized multiline tracking).
- **Automation Logic:** 
  - Predicts Y-axis page overlap to ensure clean page breaks rather than overlapping static footers.
  - Translates massive numerical sums into professional "Amount in Words" (e.g., *Forty Six Thousand Rupees Only*).

### 4. Interactive Frontend Application
- **Modern React + Vite Frontend:**
  - Responsive, high-performance UI styled entirely with native customized **Tailwind CSS**.
  - **Draggable Context Sidebar:** Users can simultaneously view 3D geometries or 2D PDFs alongside the active quoting configuration sidebar, seamlessly dragging to resize the UI workspace securely bypassing 3D hover-locks.
- **3D Viewer Module:**
  - Built with `@react-three/fiber` and `three.js`. Runs `.wasm` based OpenCASCADE mesh loading directly in-browser.
- **ACCU AI Conversational Copilot:**
  - Allows the user to naturally speak to the loaded assembly. E.g., *"Make this part EN-8 Steel with Ultra Precision tolerances."* The AI parses conversational text, updating the internal application states securely.

---

## 🏗️ Technology Stack

### Backend Environment 🐍
- **Framework:** `FastAPI` (Asynchronous ultra-fast Python APi)
- **Geometry Kernel:** `CadQuery` / `OpenCASCADE` (OCP/OCC via Python)
- **AI Core:** `google-generativeai` (Gemini Models 2.5 Flash & 2.5 Pro)
- **PDF Engine:** `fpdf2`
- **Concurrency:** Uses `asyncio` and optimized thread pools for CAD heavy-lifting.

### Frontend Environment ⚛️
- **Framework:** React 18 / Vite
- **Web 3D Visualization:** `@react-three/fiber`, `@react-three/drei`, `three.js`, `occt-import-js`
- **Icons & Styling:** `lucide-react`, `@heroicons/react`, `Tailwind CSS 3`, Custom Glassmorphism.
- **File Handling:** `react-dropzone`

---

## ⚙️ Architecture & Data Workflow

1. **User Uploads File:** 
   - Application detects if the file is `.step` or `.pdf`.
2. **Analysis Route:**
   - **STEP:** Dispatched to `/api/analyze`. CadQuery ingests the 3D file, computes B-Rep data, and responds with geometric statistics.
   - **PDF:** Dispatched to `/api/analyze/pdf`. Gemini Vision visually reviews the drawing grid, identifies parts/dimensions, and replies with a highly structured deterministic JSON matrix.
3. **Quoting Context:**
   - Data enters the `QuotePanel.jsx` React context. 
   - `fetch("/api/prices")` runs simultaneously to capture daily live USD/INR material costs.
4. **Interactive Adjustment:**
   - User edits material properties, processes, markup percentages, and surfaces.
5. **Report Generation:**
   - User selects `Download BOM Quote (PDF)`.
   - The React app submits verified, formatted JSON definitions to `main.py` -> `/api/quote/bom-pdf`.
   - Python processes the numerical sums and dynamically spins up an `AccuDesignAuthenticPDF()` payload and responds with a downloadable stream of the final PDF.

---

## 🔧 Setup & Installation (Local Development)

### 1. Requirements
* Node.js v18+
* Python 3.10+
* Google Gemini API Key
* Metals API Key (Optional but recommended)

### 2. Backend Setup
1. Navigate to the `/backend` folder.
2. Create your virtual environment: `python -m venv venv`
3. Activate the environment: `.\venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt` *(Note: Ensure CadQuery is installed cleanly according to OS limitations).*
5. Create `.env` file holding secrets:
   ```env
   GEMINI_API_KEY="your-gemini-key"
   METALS_DEV_API_KEY="your-metals-dev-key"
   ```
6. Start Server: `uvicorn main:app --reload`

### 3. Frontend Setup
1. Navigate to the root directory `/`.
2. Install npm packages: `npm install`
3. Execute the WASM library command (Important for 3D): `npm run copy-wasm`
4. Run Dev Server: `npm run dev`
5. Visit `http://localhost:5173` to experience the Quoting Interface.

---

*System designed exclusively for ACCU DESIGN.*
