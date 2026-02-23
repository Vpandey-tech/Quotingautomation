# AccuDesign ⚙️
**Advanced Manufacturing Quoting Automation System**

AccuDesign is an automated, high-performance manufacturing quotation platform designed for engineers, procurement teams, and CNC machine shops. It allows users to upload 3D CAD models (.step), visualize them instantly in the browser, extract precise geometric properties, and generate instant, highly accurate production quotes based on live metal prices and precise material removal rates (MRR).

![AccuDesign Architecture](https://via.placeholder.com/1200x600.png?text=AccuDesign+Quoting+Architecture) *(Replace with actual screenshot)*

---

## 🏗️ Architecture & Flow

1. **Client-Side Rendering**: User drags and drops a `.step` file. The frontend parses the file in-browser into a lightweight mesh for instant 3D visualization.
2. **Backend B-Rep Analysis**: Simultaneously, the original file is sent to the backend where it undergoes deep Boundary Representation (B-Rep) analysis to extract mathematically precise geometry (exact volume, bounding boxes, internal hole detection). 
3. **Live Pricing Engine**: If an exact B-Rep volume is calculated, the system queries live commodity markets (LME via metals.dev) to get the exact per-kg cost of the chosen material in USD.
4. **Machining Estimator**: Machining time is estimated using material-specific Material Removal Rates (MRR) dynamically calculated against the part's bounding box vs. final volume difference.
5. **PDF Generation**: Users can download a formalized, itemized PDF quote based on their specific Process, Tolerance, and Material configurations.

---

## 🛠️ Tech Stack & Library Purposes

### Frontend (User Interface & 3D Environment)
* **React + Vite**: Provides a blazing fast development environment and optimized production builds. 
* **Tailwind CSS**: Used for all styling. Includes responsive design, deep dark-mode support, and custom glassmorphism effects for a premium SaaS feel.
* **Three.js / @react-three/fiber / @react-three/drei**: The core 3D rendering engine. Connects the 3D canvas natively to React's component cycles for smooth camera controls (`OrbitControls`) and dynamic lighting.
* **occt-import-js (WASM)**: Running as an in-browser WebAssembly module, it instantly parses STEP files directly on the client side into meshes, ensuring the user gets a 3D preview without waiting for server responses.
* **Lucide React**: Clean, modern icons used throughout the dashboard.

### Backend (Geometry Engine & APIs)
* **FastAPI**: A high-performance, asynchronous Python web framework managing the API endpoints (`/api/quote`, `/api/analyze`, etc).
* **Uvicorn**: Lightning-fast ASGI web server used to serve the FastAPI application.
* **CadQuery (OpenCASCADE / OCC)**: The heavyweight geometric workhorse. Unlike mesh approximations, CadQuery reads the true mathematical surfaces of the STEP file. Used to calculate the *exact* volume, bounding box, and detect internal hole depths (cylinder topology).
* **HTTPX**: A fully async HTTP client. Used by the pricing engine to concurrently fetch live metal commodity prices from `metals.dev`.
* **FPDF2**: A modern PDF generation library. Used to rapidly assemble and render the dynamic, downloadable Quote Proposal document.
* **Pydantic**: Enforces strict typing and validation for all incoming and outgoing API traffic.
* **python-multipart**: Required by FastAPI to handle binary `.step` file streams.

---

## 🚀 Setup & Execution Guide

### Prerequisites
* **Node.js**: v18 or heavily recommended v20+
* **Python**: v3.9+ (v3.11 recommended)
* **Git**

---

### 1️⃣ Backend Setup (Python / FastAPI)

1. **Open a new terminal** and navigate to the backend directory:
   ```bash
   cd backend
   ```

2. **(Optional but Recommended) Create a Python Virtual Environment**:
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
   *(Note: Installing `cadquery` may take a minute or two as it includes the OpenCASCADE C++ core bindings).*

4. **Environment Variables Config**:
   Copy the example config file and insert your API key:
   ```bash
   cp .env.example .env
   ```
   Open backend/`.env` and configure your `METALS_DEV_API_KEY`. Without a valid API key, the system will gracefully fall back to hardcoded safety estimators.

5. **Start the Backend Server**:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   # Or on Windows:
   py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   *The backend should now be running at `http://localhost:8000`*

---

### 2️⃣ Frontend Setup (React / Vite)

1. **Open a separate new terminal** and ensure you are in the root directory of the project.

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
1. Make sure both servers are running.
2. Open the browser to the Vite dev server URL.
3. Drag and drop any `.step` file into the 3D viewport. 
4. The 3D model will instantly render. You will see an "Analyzing..." badge in the top right while the backend calculates exact geometry.
5. In the left panel, configure your material, manufacturing process, and target tolerance.
6. The app automatically fetches the live metal price per kg, applies complexity constraints, and estimates the final job cost.
7. Click **Generate PDF** to download the quote!
