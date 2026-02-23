---
phase: 1
plan: 1.1
wave: 1
---

# Plan 1.1: Frontend Scaffolding

## Objective
Initialize the React application with the necessary build tooling, styling, and basic structure to support the AccuDesign Quoting Agent.

## Context
- .gsd/SPEC.md (Requirements: React/Vue frontend)
- .gsd/phases/1/RESEARCH.md (Decision: React + Vite + Tailwind)

## Tasks

<task type="auto">
  <name>Initialize React Project</name>
  <files>
    c:\Users\DELL\Desktop\Quotingautomation\package.json
    c:\Users\DELL\Desktop\Quotingautomation\vite.config.js
  </files>
  <action>
    - Initialize a new Vite project with React and JavaScript (keep it simple for now, TS if preferred but JS is faster for "Free Stack" speed).
    - Install `tailwindcss`, `postcss`, `autoprefixer`.
    - Configure Tailwind.
    - Clean up default boilerplate (App.css, etc.).
  </action>
  <verify>
    npm run dev  -> opens default page with Tailwind working.
  </verify>
  <done>
    Project builds, dev server runs, Tailwind classes apply.
  </done>
</task>

<task type="auto">
  <name>Install Core Dependencies</name>
  <files>c:\Users\DELL\Desktop\Quotingautomation\package.json</files>
  <action>
    Install specific libraries for Phase 1:
    - `three`
    - `@react-three/fiber`
    - `@react-three/drei`
    - `occt-import-js`
    - `react-dropzone` (for file upload UI)
    - `lucide-react` (for icons)
  </action>
  <verify>npm list three @react-three/fiber occt-import-js</verify>
  <done>All dependencies installed without conflict.</done>
</task>

<task type="auto">
  <name>Create Project Structure</name>
  <files>
    c:\Users\DELL\Desktop\Quotingautomation\src\components\viewer\Viewer.jsx
    c:\Users\DELL\Desktop\Quotingautomation\src\components\ui\Layout.jsx
  </files>
  <action>
    Create a basic directory structure:
    - `/src/components/viewer`
    - `/src/components/ui`
    - `/src/lib` (for logic)
  </action>
  <verify>Test-Path src/components/viewer</verify>
  <done>Directory structure exists.</done>
</task>

## Success Criteria
- [ ] Vite dev server running on localhost.
- [ ] Tailwind utility classes working.
- [ ] Three.js and occt-import-js installed and ready for import.
