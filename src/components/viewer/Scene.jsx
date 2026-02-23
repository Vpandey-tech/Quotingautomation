import React, { useEffect, useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';

/**
 * Builds a THREE.Mesh from a single occt-import-js result mesh.
 * Faithfully follows the official three_viewer.html example provided
 * in the occt-import-js repository.
 */
function buildMesh(geometryMesh) {
    const geometry = new THREE.BufferGeometry();

    // Positions (required)
    geometry.setAttribute(
        'position',
        new THREE.Float32BufferAttribute(geometryMesh.attributes.position.array, 3)
    );

    // Normals (optional – not all STEP topologies export them)
    if (geometryMesh.attributes.normal) {
        geometry.setAttribute(
            'normal',
            new THREE.Float32BufferAttribute(geometryMesh.attributes.normal.array, 3)
        );
    }

    // Index
    const index = Uint32Array.from(geometryMesh.index.array);
    geometry.setIndex(new THREE.BufferAttribute(index, 1));
    geometry.name = geometryMesh.name || 'occt-mesh';

    // Default material (steel-blue metallic)
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

    // Per-face colours from B-Rep topology
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
        // No face groups — compute normals if missing
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
 * Called once after the group is populated.
 */
function AutoCamera({ groupRef, trigger }) {
    const { camera, size } = useThree();

    useEffect(() => {
        if (!trigger || !groupRef.current) return;

        const box = new THREE.Box3().setFromObject(groupRef.current);
        if (box.isEmpty()) return;

        const sphere = new THREE.Sphere();
        box.getBoundingSphere(sphere);

        const fov = (camera.fov * Math.PI) / 180;
        const aspect = size.width / size.height;
        const distance = (sphere.radius / Math.sin(fov / 2)) * 1.6;

        // Set camera at an isometric-ish angle
        const dir = new THREE.Vector3(1, 0.7, 1).normalize();
        camera.position.copy(sphere.center).addScaledVector(dir, distance);
        camera.near = distance * 0.001;
        camera.far = distance * 100;
        camera.updateProjectionMatrix();
        camera.lookAt(sphere.center);
    }, [trigger, groupRef, camera, size]);

    return null;
}

/**
 * The R3F scene content: parses an occt result and renders all meshes.
 * @param {{ occtResult: object|null }} props
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
        // Clear previous children
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

            {/* Orbit controls — full rotate/pan/zoom */}
            <OrbitControls
                makeDefault
                enableDamping
                dampingFactor={0.07}
                minDistance={0.01}
                maxDistance={1e6}
            />

            {/* Grid helper for ground reference */}
            <gridHelper args={[1000, 100, '#1a2a3a', '#0d1a27']} position={[0, -0.01, 0]} />
        </>
    );
}
