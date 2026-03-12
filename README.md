# Accu Design ⚙️
**Advanced Manufacturing Quoting & Engineering Automation System**

Accu Design is an autonomous, high-performance manufacturing quotation platform designed for precision CAD engineers, procurement teams, and CNC machine shops. It allows users to upload **3D CAD models (.step)** or **2D Engineering Drawings (.pdf)**, visualize them instantly in the browser, extract precise geometric properties, and generate instant, highly accurate production quotes based on live global metal prices, USD-to-INR currency exchange rates, and explicit machine hour configurations.

---

## 🔥 Key Features (Phase 4 Updates)

* **Dual Format Analysis (3D CAD & 2D PDF)**: Drop a `.step` file for immediate 3D in-browser B-Rep calculation constraints, or drop a `.pdf` engineering drawing to witness the document seamlessly rendered while Google Gemini AI autonomously extracts dimensions, materials, tolerances, and client details.
* **Authentic Quote Generation**: The quoting engine dynamically compiles the exact, perfectly symmetrical **ACCU DESIGN** quotation template natively inside a high-performance Python PDF generator, supporting Unicode Indian Rupee (`₹`) symbols and aesthetic HTML/PDF color codes matching your brand. Fully custom logic calculates CGST, SGST, Total A/B calculations, and translates the Grand Total into Indian numbering words dynamically.
* **Smart Anti-Hallucination OCR Engine**: A state-of-the-art backend built precisely around `gemini-2.5-flash` with aggressive fallback architectures (`gemini-2.0-flash` -> `gemini-2.5-pro` -> etc.) programmed explicitly to extract client letterheads (to auto-fill quote destination details) and dimension sets, whilst enforcing strict nil responses over hallucinations.
* **Live Pricing Engine**: Queries live commodity markets (LME via metals.dev) for base USD rates, dynamically converts them to live INR via global currency APIs, and feeds the output directly into CNC hour complexity algorithms to guarantee quoting accuracy against live metal shifts.

---

## 🏗️ Architecture & Flow

1. **Client-Side Rendering**: User drags and drops a `.step` or `.pdf` file. The frontend automatically detects the MIME type. STEP files are parsed instantly into a lightweight Three.js mesh. PDF files are seamlessly piped into an `iframe` for live previewing.
2. **Backend Engine**: Simultaneously, the original file is sent to the backend. CAD files undergo deep Boundary Representation (B-Rep) via `CadQuery` to extract mathematically precise geometry (exact volume, bounding boxes). PDF files are streamed into `google-generativeai` multi-modal analysis buffers.
3. **Quoting Algorithm (INR)**: Dynamic algorithms execute against the extracted geometry or document metrics. It divides USD benchmark machine rates, converts to live INR, applies 1.5x manufacturing overhead factors, bounds the final cost safely, and pushes the itemized results into the final payload.
4. **PDF Generation**: Users download a formalized, authentic Accu Design quotation. 

---

## 🛠️ Tech Stack 

### Frontend (User Interface & 3D Environment)
* **React + Vite**: Blazing fast development environment.
* **Tailwind CSS**: Glassmorphism premium dark-mode UI customized specially for Accu Design branding metrics.
* **Three.js / @react-three/fiber**: Core 3D rendering engine for `.step` manipulation.
* **occt-import-js (WASM)**: Running as an in-browser WebAssembly module for native performance CAD parsing.
* **React Dropzone**: Secure and aesthetic file drop mechanics supporting high-payload CAD binaries.

### Backend (Geometry Engine, AI & APIs)
* **FastAPI**: A high-performance, asynchronous Python web framework providing endpoint architecture (`/api/quote`, `/api/analyze`, `/api/analyze/pdf`).
* **Google Generative AI**: Gemini 2.5 architecture implementation specifically tuned for engineering drawing (OCR/Visual) extraction.
* **CadQuery (OpenCASCADE)**: Heavyweight B-Rep geometric kernel. Reads the true mathematical topological surfaces of the STEP file.
* **FPDF2**: Modern PDF generation library heavily customized to load native Windows Unicode TTF (Arial) fonts dynamically on the server for `₹` mapping without layout destruction.
* **Uvicorn**: Lightning-fast ASGI web server.

---

## 🚀 Setup & Execution Guide

### Prerequisites
* **Node.js**: v18+ (v20+ recommended)
* **Python**: v3.9+ (v3.11/v3.12 recommended)
* Local install of **Arial** TTF fonts (built-in on Windows systems)

---

### 1️⃣ Backend Setup (Python / FastAPI)

1. **Open a new terminal** and navigate to the backend directory:
   ```bash
   cd backend
   ```

2. **Python Virtual Environment (Recommended)**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables Config**:
   Copy the example config file:
   ```bash
   cp .env.example .env
   ```
   Open `backend/.env` and configure your API keys:
   * `METALS_DEV_API_KEY`: Required for live metal USD querying.
   * `GEMINI_API_KEY`: Strictly required for `.pdf` drawing analysis endpoints.

5. **Start the Backend Server**:
   *(Ensure you run this from the `/backend` directory)*
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

### 2️⃣ Frontend Setup (React / Vite)

1. **Open a separate new terminal** in the root directory (`/Quotingautomation`).

2. **Install Node modules**:
   ```bash
   npm install
   ```

3. **Start the Frontend Development Server**:
   ```bash
   npm run dev
   ```

4. **Access the App**: Click the local link provided by Vite (usually `http://localhost:5173`).

---

## ⚙️ Running the Demo
1. Make sure both servers are running cleanly.
2. Drag and drop a `.step` CAD file **OR** a `.pdf` Engineering Drawing into the viewport.
3. Observe the live preview mechanism while the backend (FastAPI / Gemini / CadQuery) asynchronously analyzes the payload.
4. If a `.pdf` drawing is dropped, ensure the "Client details" auto-populate securely from the title block of the drawing.
5. In the left panel, configure the specific Material, Surface Treatment, or custom overrides.
6. The app computes the exact manufacturing cost (in INR).
7. Click **Generate PDF** to download the perfectly formatted, authentic ACCU DESIGN quotation matching exact industry standards!
