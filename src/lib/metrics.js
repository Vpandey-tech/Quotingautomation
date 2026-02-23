/**
 * Geometry metrics computation from occt-import-js result.
 *
 * All values are in the STEP file's native unit (always millimeters for STEP).
 * Volume uses the divergence theorem (signed sum of tetrahedral volumes).
 * Surface area is summed from triangle cross-products.
 */

/**
 * Compute full geometry metrics from OCCT result + original File.
 * @param {object} result  - occt-import-js ReadStepFile result
 * @param {File}   file    - original browser File (for name/size)
 * @returns {object} metrics
 */
export function computeMetrics(result, file) {
    let totalVertices = 0;
    let totalTriangles = 0;
    let totalVolume = 0;   // mm³ (signed, take abs)
    let totalSurface = 0;   // mm²

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;

    for (const mesh of result.meshes) {
        const pos = mesh.attributes.position.array; // Float32Array, XYZ triples
        const idx = mesh.index.array;               // Uint32Array, triangle indices

        totalVertices += pos.length / 3;
        totalTriangles += idx.length / 3;

        // ── Bounding box ─────────────────────────────────────────────────
        for (let i = 0; i < pos.length; i += 3) {
            const x = pos[i], y = pos[i + 1], z = pos[i + 2];
            if (x < minX) minX = x; if (x > maxX) maxX = x;
            if (y < minY) minY = y; if (y > maxY) maxY = y;
            if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
        }

        // ── Volume (divergence theorem) + Surface area per triangle ──────
        for (let i = 0; i < idx.length; i += 3) {
            const a = idx[i] * 3;
            const b = idx[i + 1] * 3;
            const c = idx[i + 2] * 3;

            const ax = pos[a], ay = pos[a + 1], az = pos[a + 2];
            const bx = pos[b], by = pos[b + 1], bz = pos[b + 2];
            const cx = pos[c], cy = pos[c + 1], cz = pos[c + 2];

            // Signed volume of tetrahedron from origin
            totalVolume += (ax * (by * cz - bz * cy) +
                bx * (cy * az - cz * ay) +
                cx * (ay * bz - az * by)) / 6;

            // Surface area: |cross(b-a, c-a)| / 2
            const ex = bx - ax, ey = by - ay, ez = bz - az;
            const fx = cx - ax, fy = cy - ay, fz = cz - az;
            const crossX = ey * fz - ez * fy;
            const crossY = ez * fx - ex * fz;
            const crossZ = ex * fy - ey * fx;
            totalSurface += Math.sqrt(crossX * crossX + crossY * crossY + crossZ * crossZ) / 2;
        }
    }

    const sizeX = maxX - minX;
    const sizeY = maxY - minY;
    const sizeZ = maxZ - minZ;

    return {
        fileName: file.name,
        fileSize: file.size,              // bytes
        meshCount: result.meshes.length,
        vertices: Math.round(totalVertices),
        triangles: Math.round(totalTriangles),
        unit: 'Millimeter',
        sizeX: sizeX.toFixed(2),       // mm
        sizeY: sizeY.toFixed(2),       // mm
        sizeZ: sizeZ.toFixed(2),       // mm
        volume: Math.abs(totalVolume).toFixed(2),  // mm³
        surfaceArea: totalSurface.toFixed(2),          // mm²
    };
}
