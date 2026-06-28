import React, { useEffect, useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useThree } from '@react-three/fiber';
import { OrbitControls, GizmoHelper, GizmoViewport, Html } from '@react-three/drei';

/**
 * Builds a THREE.Mesh from a single occt-import-js result mesh.
 * Faithfully follows the official three_viewer.html example provided
 * in the occt-import-js repository.
 */
function buildMesh(geometryMesh) {
    const geometry = new THREE.BufferGeometry();

    geometry.setAttribute(
        'position',
        new THREE.Float32BufferAttribute(geometryMesh.attributes.position.array, 3)
    );

    if (geometryMesh.attributes.normal) {
        geometry.setAttribute(
            'normal',
            new THREE.Float32BufferAttribute(geometryMesh.attributes.normal.array, 3)
        );
    }

    const index = Uint32Array.from(geometryMesh.index.array);
    geometry.setIndex(new THREE.BufferAttribute(index, 1));
    geometry.name = geometryMesh.name || 'occt-mesh';

    const defaultColor = geometryMesh.color
        ? new THREE.Color(geometryMesh.color[0], geometryMesh.color[1], geometryMesh.color[2])
        : new THREE.Color(0x6e95c0);

    const defaultMaterial = new THREE.MeshStandardMaterial({
        color: defaultColor,
        metalness: 0.45,
        roughness: 0.35,
        side: THREE.DoubleSide,
    });

    let materials = [defaultMaterial];

    if (geometryMesh.brep_faces && geometryMesh.brep_faces.length > 0) {
        for (const faceColor of geometryMesh.brep_faces) {
            const color = faceColor.color
                ? new THREE.Color(faceColor.color[0], faceColor.color[1], faceColor.color[2])
                : defaultColor.clone();
            materials.push(new THREE.MeshStandardMaterial({
                color,
                metalness: 0.45,
                roughness: 0.35,
                side: THREE.DoubleSide,
            }));
        }

        const triangleCount = geometryMesh.index.array.length / 3;
        let triangleIndex = 0;
        let faceColorGroupIndex = 0;

        while (triangleIndex < triangleCount) {
            const firstIndex = triangleIndex;
            let lastIndex, materialIndex;

            if (faceColorGroupIndex >= geometryMesh.brep_faces.length) {
                lastIndex = triangleCount;
                materialIndex = 0;
            } else if (triangleIndex < geometryMesh.brep_faces[faceColorGroupIndex].first) {
                lastIndex = geometryMesh.brep_faces[faceColorGroupIndex].first;
                materialIndex = 0;
            } else {
                lastIndex = geometryMesh.brep_faces[faceColorGroupIndex].last + 1;
                materialIndex = faceColorGroupIndex + 1;
                faceColorGroupIndex++;
            }

            geometry.addGroup(firstIndex * 3, (lastIndex - firstIndex) * 3, materialIndex);
            triangleIndex = lastIndex;
        }
    } else {
        if (!geometryMesh.attributes.normal) {
            geometry.computeVertexNormals();
        }
    }

    const mesh = new THREE.Mesh(geometry, materials.length > 1 ? materials : materials[0]);
    mesh.name = geometry.name;
    mesh.castShadow = true;
    mesh.receiveShadow = true;

    return mesh;
}

/**
 * AutoCamera: fits the camera to the loaded model's bounding sphere.
 * Extra padding (1.9×) ensures dimension lines outside the model stay visible.
 */
function AutoCamera({ groupRef, trigger }) {
    const { camera, size, gl, scene } = useThree();

    const alignFrontView = useRef(null);

    alignFrontView.current = () => {
        const targetObj = trigger || groupRef.current;
        if (!targetObj) return;

        const box = new THREE.Box3().setFromObject(targetObj);
        if (box.isEmpty()) return;

        const sphere = new THREE.Sphere();
        box.getBoundingSphere(sphere);

        const fov = (camera.fov * Math.PI) / 180;
        const aspect = camera.aspect || 1;
        const halfFov = fov / 2;
        let fitRadius = sphere.radius;
        if (aspect < 1) {
            fitRadius = fitRadius / aspect;
        }

        // 1.0x padding multiplier ensures dimension overlays and parts are comfortably framed
        const distance = (fitRadius / Math.sin(halfFov)) * 1.0;

        // Clean Front View: Camera looking directly down the Z-axis
        const dir = new THREE.Vector3(0, 0, 1).normalize();

        camera.position.copy(sphere.center).addScaledVector(dir, distance);
        camera.near = distance * 0.01;
        camera.far = distance * 100;
        camera.updateProjectionMatrix();
        camera.lookAt(sphere.center);

        // Center OrbitControls rotation target
        const controls = camera.controls || gl.domElement.__controls;
        if (controls) {
            controls.target.copy(sphere.center);
            controls.update();
        }

        // Force synchronous render to update the canvas buffer immediately for screenshot
        gl.render(scene, camera);
    };

    useEffect(() => {
        if (!trigger || !groupRef.current) return;
        alignFrontView.current();
    }, [trigger, groupRef, camera, size]);

    useEffect(() => {
        const handleCaptureReset = () => {
            if (alignFrontView.current) {
                alignFrontView.current();
            }
        };
        window.addEventListener('reset-camera-front', handleCaptureReset);
        return () => window.removeEventListener('reset-camera-front', handleCaptureReset);
    }, []);

    return null;
}


/* ────────────────────────────────────────────────────────────
 *  CAD-Style Dimension System
 *
 *  FIX: Uses the THREE.Group `model` directly (via useMemo)
 *  instead of refs + useEffect. This avoids the timing issue
 *  where the overlay's effect ran before the parent populated
 *  the group ref.
 *
 *  GPU overhead: ~7 draw calls, ~60 vertices — negligible.
 * ──────────────────────────────────────────────────────────── */

/** Format a dimension value for display */
function fmtDim(v) {
    if (v >= 100)  return v.toFixed(1);
    if (v >= 1)    return v.toFixed(2);
    if (v >= 0.01) return v.toFixed(3);
    return v.toFixed(4);
}

/**
 * DimensionLine — a single axis dimension with:
 *   • Main measurement line
 *   • Extension lines from model edges to the dimension line
 *   • Perpendicular tick marks at both ends
 *   • Centered label with axis name + value in mm
 */
function DimensionLine({ from, to, label, color, extA, extB, tickDir }) {
    const positions = useMemo(() => {
        const pts = [];
        const push = (a, b) => {
            pts.push(a[0], a[1], a[2], b[0], b[1], b[2]);
        };

        // Main dimension line
        push(from, to);

        // Extension / leader lines (model edge → dimension line)
        if (extA) push(extA, from);
        if (extB) push(extB, to);

        // Perpendicular tick marks at both ends
        if (tickDir) {
            const dimLen = Math.sqrt(
                (to[0] - from[0]) ** 2 +
                (to[1] - from[1]) ** 2 +
                (to[2] - from[2]) ** 2
            );
            const t = Math.max(dimLen * 0.025, 0.4);

            push(
                [from[0] - tickDir[0] * t, from[1] - tickDir[1] * t, from[2] - tickDir[2] * t],
                [from[0] + tickDir[0] * t, from[1] + tickDir[1] * t, from[2] + tickDir[2] * t]
            );
            push(
                [to[0] - tickDir[0] * t, to[1] - tickDir[1] * t, to[2] - tickDir[2] * t],
                [to[0] + tickDir[0] * t, to[1] + tickDir[1] * t, to[2] + tickDir[2] * t]
            );
        }

        return new Float32Array(pts);
    }, [from, to, extA, extB, tickDir]);

    const mid = useMemo(() => [
        (from[0] + to[0]) / 2,
        (from[1] + to[1]) / 2,
        (from[2] + to[2]) / 2,
    ], [from, to]);

    return (
        <group>
            <lineSegments renderOrder={999}>
                <bufferGeometry>
                    <bufferAttribute
                        attach="attributes-position"
                        array={positions}
                        count={positions.length / 3}
                        itemSize={3}
                    />
                </bufferGeometry>
                <lineBasicMaterial
                    color={color}
                    depthTest={false}
                    transparent
                    opacity={0.85}
                    toneMapped={false}
                />
            </lineSegments>
            <Html position={mid} center zIndexRange={[50, 0]} style={{ pointerEvents: 'none' }}>
                <div style={{
                    background: 'rgba(8, 12, 20, 0.9)',
                    border: `1px solid ${color}`,
                    borderRadius: 5,
                    padding: '2px 8px',
                    color,
                    fontSize: 11,
                    fontFamily: "'Inter', 'Consolas', monospace",
                    fontWeight: 700,
                    whiteSpace: 'nowrap',
                    userSelect: 'none',
                    letterSpacing: '0.03em',
                    lineHeight: '18px',
                    backdropFilter: 'blur(6px)',
                    boxShadow: `0 0 12px ${color}25, 0 2px 8px rgba(0,0,0,0.5)`,
                }}>
                    {label}
                </div>
            </Html>
        </group>
    );
}

/**
 * DimensionOverlay — computes bounding box from the model group
 * using useMemo (NOT useEffect+setState — avoids timing bugs).
 * Renders wireframe box + three axis dimension lines.
 */
function DimensionOverlay({ model }) {
    // Compute bounds directly from the model group (already fully constructed)
    const bounds = useMemo(() => {
        if (!model) return null;

        // Ensure the model's world matrix is up-to-date
        model.updateMatrixWorld(true);

        const box = new THREE.Box3().setFromObject(model);
        if (box.isEmpty()) return null;

        return {
            min: box.min.clone(),
            max: box.max.clone(),
            size: box.getSize(new THREE.Vector3()),
            center: box.getCenter(new THREE.Vector3()),
        };
    }, [model]);

    // Build wireframe box geometry once
    const boxEdges = useMemo(() => {
        if (!bounds) return null;
        const { size } = bounds;
        const boxGeo = new THREE.BoxGeometry(size.x, size.y, size.z);
        const edges = new THREE.EdgesGeometry(boxGeo);
        boxGeo.dispose();
        return edges;
    }, [bounds]);

    if (!bounds) return null;

    const { min, max, size, center } = bounds;
    const maxDim = Math.max(size.x, size.y, size.z);
    const gap = maxDim * 0.1; // 10% offset from model

    const showX = size.x > 0.001;
    const showY = size.y > 0.001;
    const showZ = size.z > 0.001;

    return (
        <group>
            {/* ─── Wireframe Bounding Box ────────────────────────────── */}
            {boxEdges && (
                <lineSegments
                    geometry={boxEdges}
                    position={[center.x, center.y, center.z]}
                    renderOrder={998}
                >
                    <lineBasicMaterial
                        color="#22d3ee"
                        opacity={0.3}
                        transparent
                        depthTest={false}
                        toneMapped={false}
                    />
                </lineSegments>
            )}

            {/* ─── X Dimension (Red) — bottom-front edge, offset down ─ */}
            {showX && (
                <DimensionLine
                    from={[min.x, min.y - gap, max.z]}
                    to={[max.x, min.y - gap, max.z]}
                    label={`X: ${fmtDim(size.x)} mm`}
                    color="#f87171"
                    extA={[min.x, min.y, max.z]}
                    extB={[max.x, min.y, max.z]}
                    tickDir={[0, 1, 0]}
                />
            )}

            {/* ─── Y Dimension (Green) — right-front edge, offset right */}
            {showY && (
                <DimensionLine
                    from={[max.x + gap, min.y, max.z]}
                    to={[max.x + gap, max.y, max.z]}
                    label={`Y: ${fmtDim(size.y)} mm`}
                    color="#4ade80"
                    extA={[max.x, min.y, max.z]}
                    extB={[max.x, max.y, max.z]}
                    tickDir={[1, 0, 0]}
                />
            )}

            {/* ─── Z Dimension (Blue) — bottom-right edge, offset down  */}
            {showZ && (
                <DimensionLine
                    from={[max.x, min.y - gap, min.z]}
                    to={[max.x, min.y - gap, max.z]}
                    label={`Z: ${fmtDim(size.z)} mm`}
                    color="#60a5fa"
                    extA={[max.x, min.y, min.z]}
                    extB={[max.x, min.y, max.z]}
                    tickDir={[0, 1, 0]}
                />
            )}

            {/* ─── Origin axes cross-hair ────────────────────────────── */}
            <axesHelper args={[maxDim * 0.08]} position={[center.x, center.y, center.z]} renderOrder={997} />
        </group>
    );
}


/**
 * Scene — main R3F content. Renders the OCCT model with CAD-style
 * dimension overlay and axis orientation gizmo.
 */
export default function Scene({ occtResult }) {
    const groupRef = useRef();

    // Build THREE group from OCCT result
    const group = useMemo(() => {
        if (!occtResult || !occtResult.meshes) return null;

        const g = new THREE.Group();
        for (const resultMesh of occtResult.meshes) {
            try {
                g.add(buildMesh(resultMesh));
            } catch (e) {
                console.warn('Failed to build mesh:', e);
            }
        }

        // Centre the model at origin
        const box = new THREE.Box3().setFromObject(g);
        const center = box.getCenter(new THREE.Vector3());
        g.position.sub(center);

        return g;
    }, [occtResult]);

    // Sync the THREE group into our ref whenever it changes
    useEffect(() => {
        if (!groupRef.current) return;
        while (groupRef.current.children.length) {
            groupRef.current.remove(groupRef.current.children[0]);
        }
        if (group) {
            groupRef.current.add(group);
        }
    }, [group]);

    return (
        <>
            {/* Lighting */}
            <ambientLight intensity={0.6} />
            <directionalLight
                position={[5, 10, 7]}
                intensity={1.4}
                castShadow
                shadow-mapSize={[2048, 2048]}
            />
            <directionalLight position={[-5, -5, -5]} intensity={0.3} />
            <pointLight position={[0, 20, 0]} intensity={0.5} />

            {/* Auto-fit camera whenever model changes */}
            <AutoCamera groupRef={groupRef} trigger={group} />

            {/* Model container */}
            <group ref={groupRef} />

            {/* ── CAD Dimension Overlay (pass group directly, not ref) ─ */}
            {group && <DimensionOverlay model={group} />}

            {/* ── Axis Orientation Gizmo (bottom-left corner) ──────── */}
            <GizmoHelper alignment="bottom-left" margin={[62, 62]}>
                <GizmoViewport
                    axisColors={['#f87171', '#4ade80', '#60a5fa']}
                    labelColor="#ffffff"
                />
            </GizmoHelper>

            {/* Orbit controls — Left: rotate, Right: pan (move view), Scroll: zoom */}
            <OrbitControls
                makeDefault
                enableDamping
                dampingFactor={0.07}
                enablePan={true}
                screenSpacePanning={true}
                panSpeed={1.2}
                minDistance={0.01}
                maxDistance={1e6}
            />

            {/* Grid helper */}
            <gridHelper args={[1000, 100, '#1a2a3a', '#0d1a27']} position={[0, -0.01, 0]} />
        </>
    );
}
