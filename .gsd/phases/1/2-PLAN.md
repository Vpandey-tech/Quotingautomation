---
phase: 1
plan: 1.2
wave: 1
---

# Plan 1.2: Instant Preview 3D Viewer

## Objective
Implement the "Instant Preview" functionality where a user can drop a STEP file and see a 3D rendering immediately in the browser.

## Context
- .gsd/SPEC.md (Goal 5: Interactive 3D Visualization)
- .gsd/phases/1/RESEARCH.md (Architecture)

## Tasks

<task type="auto">
  <name>Implement File Dropzone</name>
  <files>c:\Users\DELL\Desktop\Quotingautomation\src\components\viewer\Dropzone.jsx</files>
  <action>
    Create a dropzone component using `react-dropzone`.
    - Accept `.step`, `.stp` extensions.
    - Visual feedback on drag.
    - Call a parent `onFileUpload` handler with the File object.
  </action>
  <verify>Manual check: Dragging a file logs it to console.</verify>
  <done>File object accessible in React state.</done>
</task>

<task type="auto">
  <name>Implement OCCT Loader Service</name>
  <files>c:\Users\DELL\Desktop\Quotingautomation\src\lib\occt.js</files>
  <action>
    Create a service to handle `occt-import-js`.
    - Initialize the WASM module.
    - Function `processStepFile(fileObject)` that reads the file as ArrayBuffer, passes to OCCT, and returns the mesh data.
    - IMPORTANT: Ensure `occt-import-js.wasm` is in the `public` folder or correctly correctly handled by Vite assets.
  </action>
  <verify>Unit test or console log ensuring mesh data is returned from a dummy STEP file.</verify>
  <done>STEP file converts to JSON geometry data.</done>
</task>

<task type="auto">
  <name>Implement 3D Scene</name>
  <files>c:\Users\DELL\Desktop\Quotingautomation\src\components\viewer\Scene.jsx</files>
  <action>
    Create a R3F Canvas component.
    - `<Canvas>` setup with `OrbitControls`, `Stage` (from drei).
    - A component that takes the processed geometry and renders a `<mesh>`.
    - Handle loading state.
  </action>
  <verify>Browser check: Rendering a simple box, then integrating the STEP mesh.</verify>
  <done>Uploaded STEP file appears in 3D scene.</done>
</task>

## Success Criteria
- [ ] Drag and drop a valid STEP file.
- [ ] 3D rendering appears within seconds.
- [ ] User can rotate/zoom the model.
