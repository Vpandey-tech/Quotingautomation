# SPEC.md — Project Specification

> **Status**: `FINALIZED`

## Vision
To provide AccuDesign clients with instantaneous, mathematically accurate manufacturing quotes (CNC and 3D printing) by analyzing 3D CAD files and live market data, delivering a full report and 3D visualization within a 30-minute window.

## Goals
1.  **Instantaneous Quote Generation**: Deliver accurate quotes for CNC and 3D printing within 30 minutes of file upload.
2.  **High-Accuracy Geometric Analysis**: Extract precise volume, surface area, and bounding box dimensions from neutral CAD formats (.step, .stp) using industry-standard B-Rep kernels.
3.  **Automated Manufacturing Feature Recognition**: Detect and classify manufacturing features (holes, complexity) to inform cost estimation.
4.  **Dynamic Market-Driven Pricing**: Integrate real-time material pricing (LME) and configurable labor/overhead rates into cost calculations.
5.  **Interactive 3D Visualization**: Provide immediate client-side 3D rendering of uploaded parts for verification.

## Non-Goals (Out of Scope)
-   Support for native CAD formats (SolidWorks, CATIA, etc.) in MVP (focus on STEP).
-   Full implementation of CAM toolpath generation (G-code); focus is on *estimation* based on geometry.
-   Marketplace functionality (connecting multiple vendors); this is an internal tool for AccuDesign.
-   Mobile app development (web-based only).

## Users
-   **AccuDesign Clients**: Engineers and procurement agents needing quick, accurate quotes for manufacturing parts.
-   **AccuDesign Estimators/Developers**: Internal staff reviewing automated quotes and maintaining the pricing logic.

## Constraints
-   **Time**: 30-minute window for quote delivery calculation (though system aims for near-instant).
-   **Accuracy**: Must distinguish between through-holes and blind holes; critical for drilling cost.
-   **Stack**: "The Free Stack" — Python (FastAPI/Flask), CadQuery/OCCT, Celery, Redis, Three.js.
-   **Input**: Primary support for ISO 10303 STEP files.

## Success Criteria
-   [ ] successful ingestion and geometric analysis of standard STEP files.
-   [ ] Accurate extraction of V (Volume), A (Surface Area), and B (Bounding Box) within < 5% error margin of native CAD tools.
-   [ ] Correct identification of > 90% of standard drilled holes (blind vs. through).
-   [ ] End-to-end quote generation (Upload -> Price) in under 2 minutes for standard parts.
-   [ ] Live material price updating functioning via scraper.
