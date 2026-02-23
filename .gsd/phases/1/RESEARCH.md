# Research: Phase 1 (Visualization)

## Tech Stack Decisions

### Frontend Framework: **React**
**Rationale**:
- The "Free Stack" PRD mentions React/Vue.
- **Why React?** The 3D ecosystem for React is significantly stronger due to **react-three-fiber (R3F)**. R3F allows declarative Three.js scenes, which simplifies managing the lifecycle of complex 3D objects compared to vanilla Three.js in Vue.
- **Tooling**: Vite (fast builds), TailwindCSS (styling).

### STEP Parsing: **occt-import-js**
**Rationale**:
- **Capability**: It is a Wasm port of OpenCascade specifically for importing STEP/IGES/BREP and outputting Three.js-compatible JSON geometry.
- **Performance**: Runs client-side (Wasm), satisfying the "Instant 3D rendering" requirement without backend round-trips for visualization.
- **Integration**: Can be wrapped in a `useEffect` hook to process files from a drag-and-drop input.
- **Alternatives**: Server-side conversion (too slow for "instant"), `cascade-studio` (too heavy/full IDE).

## Architecture for Phase 1

1.  **Input**: React Dropzone.
2.  **Processing**: Web Worker (optional for v1, but good for main thread health) or direct Async call to `occt-import-js`.
3.  **Rendering**:
    - `<Canvas>` from R3F.
    - Custom `<StepModel>` component that takes the JSON output and creates `THREE.BufferGeometry`.
    - Standard lights/gizmos.

## Risks & Mitigations
- **Wasm Size**: `occt-import-js.wasm` is large (~10MB+).
    - *Mitigation*: Lazy load it only when the user uploads a file or enters the viewer route.
- **Performance**: Large STEP files might freeze the UI.
    - *Plan*: Use a Web Worker for the conversion process if UI freezing is observed during implementation (Task 1.2).
