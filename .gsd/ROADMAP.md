# ROADMAP.md

> **Current Phase**: Phase 2
> **Milestone**: v1.0 (MVP)

## Must-Haves (from SPEC)
- [x] STEP file ingestion and validation
- [x] Web-based 3D Viewer (Three.js / R3F)
- [x] Client-side Geometric extraction (Volume, Area, Bounding Box) from mesh
- [x] B-Rep truth metrics (Volume, Area) via CadQuery backend — **Phase 2**
- [x] Feature recognition (Holes, geometric complexity) — **Phase 2**
- [x] Dynamic Costing Engine with live material tracking — **Phase 3**
- [ ] PDF Quote Generation — **Phase 4**

## Phases

### Phase 1: Visualization & Client-Side Foundation
**Status**: ✅ Complete
**Objective**: Enable immediate visual verification of uploaded parts.
**Deliverables**:
- [x] React + Vite frontend setup (Tailwind, R3F, lucide-react)
- [x] Integration of `occt-import-js` (WASM) + `@react-three/fiber` for STEP rendering
- [x] Drag-and-drop file upload with react-dropzone
- [x] Bounding box, vertex/triangle count, volume, surface area from mesh data
- [x] Dark-themed sidebar with Details panel (Vertices, Triangles, Size X/Y/Z, Volume, Surface)
- [x] OrbitControls, auto-camera fit, per-face colours, lighting, grid

### Phase 2: Geometric Core & Backend Worker
**Status**: 🔄 In Progress
**Objective**: Build the heavy-lifting analysis engine.
**Deliverables**:
- [x] FastAPI backend scaffolded (`backend/main.py`)
- [x] CadQuery B-Rep analysis endpoint (`POST /api/analyze`)
- [x] Cylindrical hole detection (blind vs. through) heuristic
- [x] Complexity scoring for machining tier classification
- [ ] Celery + Redis async job queue integration
- [ ] Non-Manifold Geometry handling (MeshLib/pymeshfix)
- [ ] Frontend polling for async B-Rep results
- [ ] Replace client-side mesh metrics with B-Rep truth values from backend
**Requirements**: 2.1, 4 (Worker Queue)

### Phase 3: Costing Intelligence & Data Feeds
**Status**: ✅ Complete
**Objective**: Connect geometry to money.
**Deliverables**:
- [x] Scraper implementation for LME pricing (metals-api & World Bank fallback)
- [x] Machining Time Estimation formulas (MRR logic done)
- [x] Additive manufacturing estimation logic
- [x] Cost Summation logic ($Material + Labor + Overhead$)
**Requirements**: 2.2, 5.3 (Deep hole penalty)

### Phase 4: Integration & Reporting
**Status**: 🔄 In Progress
**Objective**: Deliver the final product to the user.
**Deliverables**:
- [x] Unified API linking Geometry → Price
- [x] PDF Report generation (FPDF/ReportLab)
- [ ] Backend Developer HUD for inspecting Attribute Adjacency Graphs
- [ ] Unit conversion handling (quantulum3)
**Requirements**: 3, 5.2
