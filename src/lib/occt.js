/**
 * OCCT Import JS — browser service
 *
 * occt-import-js is loaded via a classic <script> tag in index.html which
 * sets window.occtimportjs. This avoids Vite's CJS-to-ESM bundling which
 * breaks the Emscripten WASM runtime setup.
 *
 * Required files in /public/ (served at /):
 *   - occt-import-js.js   (Emscripten JS glue — loaded globally via <script>)
 *   - occt-import-js.wasm (WebAssembly binary — fetched by the JS glue)
 *
 * To copy both:
 *   copy node_modules\occt-import-js\dist\occt-import-js.js public\
 *   (occt-import-js.wasm is already in /public/)
 */

let occtInstance = null;
let initPromise = null;

/**
 * Lazily initialise and cache the OCCT WASM module.
 * window.occtimportjs is the factory function set by the global script tag.
 */
export async function getOCCT() {
    if (occtInstance) return occtInstance;
    if (initPromise) return initPromise;

    if (typeof window.occtimportjs !== 'function') {
        throw new Error(
            'window.occtimportjs is not available. ' +
            'Ensure /public/occt-import-js.js is loaded via <script> in index.html.'
        );
    }

    initPromise = window.occtimportjs({
        // The WASM binary is in /public/ — served at the root path.
        // Emscripten's locateFile is called with "occt-import-js.wasm"
        // and must return a URL the browser can fetch.
        locateFile: (fileName) => `/${fileName}`,
    }).then((instance) => {
        occtInstance = instance;
        return instance;
    });

    return initPromise;
}

/**
 * Parse a STEP/STP browser File object via occt-import-js WASM.
 * Returns: { meshes: [...], root: {...} }
 *
 * Each mesh contains:
 *   attributes.position.array  — Float32Array (XYZ triples)
 *   attributes.normal.array    — Float32Array (optional)
 *   index.array                — Uint32Array (triangle vertex indices)
 *   brep_faces                 — face colour groups (for per-face colouring)
 *   color                      — [r, g, b] 0–1 (optional)
 */
export async function parseStepFile(file) {
    const occt = await getOCCT();
    const buf = await file.arrayBuffer();
    const bytes = new Uint8Array(buf);
    return occt.ReadStepFile(bytes, null);
}
