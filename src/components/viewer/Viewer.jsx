import React, { useState, useCallback, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { useDropzone } from 'react-dropzone';
import { Upload, RotateCcw, AlertCircle, Loader2, Box } from 'lucide-react';
import Scene from './Scene';
import { parseStepFile } from '../../lib/occt';
import { computeMetrics } from '../../lib/metrics';

/**
 * AccuDesign 3D Viewer — Phase 1 implementation.
 *
 * Architecture:
 *  - File is received via drag-drop or file-picker (react-dropzone).
 *  - parseStepFile() reads it via occt-import-js WASM → returns mesh data.
 *  - @react-three/fiber <Canvas> renders the mesh via Scene.jsx.
 *
 * Why @react-three/fiber instead of online-3d-viewer's EmbeddedViewer?
 *  EmbeddedViewer reads clientWidth/clientHeight at constructor time which
 *  is always 0 in a React flex layout → blank WebGL canvas forever.
 *  R3F's <Canvas> manages its own ResizeObserver and always fills its parent.
 */
export default function Viewer({ onMetrics }) {
    const [file, setFile] = useState(null);
    const [status, setStatus] = useState('idle');   // idle|loading|loaded|error
    const [errorMsg, setErrorMsg] = useState('');
    const [occtResult, setOcctResult] = useState(null);

    // ── Process file via OCCT ─────────────────────────────────────────────────
    const processFile = useCallback(async (f) => {
        setFile(f);
        setStatus('loading');
        setOcctResult(null);
        setErrorMsg('');

        try {
            const result = await parseStepFile(f);

            if (!result || !result.meshes || result.meshes.length === 0) {
                throw new Error('No geometry found in file.');
            }

            setOcctResult(result);
            setStatus('loaded');

            // Compute full geometry metrics and bubble up to parent
            // Pass the original File object as 2nd arg so App can POST it to /api/analyze
            if (onMetrics) {
                onMetrics(computeMetrics(result, f), f);
            }
        } catch (err) {
            console.error('[Viewer] OCCT parse error:', err);
            setStatus('error');
            setErrorMsg(err.message || 'Failed to parse file. Ensure it is a valid STEP/STP file.');
        }
    }, [onMetrics]);

    // ── Dropzone ──────────────────────────────────────────────────────────────
    const onDrop = useCallback((acceptedFiles) => {
        if (acceptedFiles.length > 0) processFile(acceptedFiles[0]);
    }, [processFile]);

    const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
        onDrop,
        accept: {
            'model/step': ['.step', '.stp'],
            'application/step': ['.step', '.stp'],
            'application/octet-stream': ['.step', '.stp'],
            'text/plain': ['.step', '.stp'],
        },
        multiple: false,
        noClick: true,
    });

    const handleReset = useCallback(() => {
        setFile(null);
        setStatus('idle');
        setOcctResult(null);
        setErrorMsg('');
        if (onMetrics) onMetrics(null);
    }, [onMetrics]);

    return (
        <div className="w-full h-full relative bg-[#080c14]" {...getRootProps()}>
            <input {...getInputProps()} />

            {/* ── 3D Canvas — always mounted, R3F handles sizing ─────────── */}
            {status === 'loaded' && occtResult && (
                <Canvas
                    className="absolute inset-0"
                    camera={{ fov: 45, near: 0.01, far: 1e7 }}
                    gl={{ antialias: true, alpha: false }}
                    style={{ background: 'linear-gradient(135deg, #080c14 0%, #0d1a2e 100%)' }}
                    shadows
                >
                    <Suspense fallback={null}>
                        <Scene occtResult={occtResult} />
                    </Suspense>
                </Canvas>
            )}

            {/* ── IDLE: Full-screen drop zone ───────────────────────────── */}
            {status === 'idle' && (
                <div
                    className={`absolute inset-0 z-10 flex flex-col items-center justify-center
                        cursor-pointer transition-all duration-300
                        ${isDragActive ? 'bg-cyan-500/5' : 'bg-transparent'}`}
                    onClick={open}
                >
                    {/* Animated ring */}
                    <div className={`relative w-40 h-40 mb-8 rounded-full border-2 flex items-center justify-center
                        transition-all duration-300
                        ${isDragActive
                            ? 'border-cyan-400 shadow-[0_0_60px_rgba(0,212,255,0.2)] scale-110'
                            : 'border-gray-700/60 hover:border-gray-500/80 hover:scale-105'}`}
                    >
                        {isDragActive && (
                            <>
                                <div className="absolute inset-0 rounded-full border-2 border-cyan-400 animate-ping opacity-30" />
                                <div className="absolute inset-[-8px] rounded-full border border-cyan-400/20 animate-pulse" />
                            </>
                        )}
                        <Box
                            size={52}
                            className={`transition-colors duration-300 ${isDragActive ? 'text-cyan-400' : 'text-gray-500'}`}
                            strokeWidth={1.2}
                        />
                    </div>

                    <h2 className="text-2xl font-semibold text-gray-100 mb-2 tracking-tight">
                        {isDragActive ? 'Release to load model' : 'Drop your STEP file here'}
                    </h2>
                    <p className="text-gray-500 text-sm mb-1">.STEP · .STP</p>
                    <p className="text-gray-600 text-xs mb-6">ISO 10303 B-Rep geometry · parsed via OCCT WebAssembly</p>

                    <button
                        className="px-6 py-2.5 rounded-xl bg-gray-800/70 border border-gray-700/80
                            text-gray-300 hover:bg-gray-700/80 hover:text-white hover:border-gray-600
                            transition-all duration-200 text-sm font-medium backdrop-blur-sm"
                    >
                        Browse files
                    </button>
                </div>
            )}

            {/* ── LOADING overlay ───────────────────────────────────────── */}
            {status === 'loading' && (
                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center
                    bg-[#080c14]/90 backdrop-blur-sm">
                    <div className="relative mb-6">
                        <Loader2 size={48} className="text-cyan-400 animate-spin" />
                        <div className="absolute inset-0 rounded-full bg-cyan-400/10 animate-pulse" />
                    </div>
                    <p className="text-gray-100 font-semibold text-lg mb-1">Parsing geometry</p>
                    <p className="text-gray-400 text-sm mb-1">{file?.name}</p>
                    <p className="text-gray-600 text-xs">Running OCCT WebAssembly engine…</p>
                </div>
            )}

            {/* ── ERROR overlay ─────────────────────────────────────────── */}
            {status === 'error' && (
                <div className="absolute inset-0 z-20 flex items-center justify-center bg-[#080c14]/95">
                    <div className="flex flex-col items-center gap-4 p-8 rounded-2xl
                        bg-red-950/25 border border-red-900/40 max-w-sm mx-4 text-center
                        backdrop-blur-md shadow-2xl">
                        <div className="w-16 h-16 rounded-full bg-red-900/20 flex items-center justify-center">
                            <AlertCircle size={36} className="text-red-400" />
                        </div>
                        <div>
                            <p className="text-red-300 font-bold text-xl mb-2">Import Failed</p>
                            <p className="text-red-400/80 text-sm leading-relaxed">{errorMsg}</p>
                        </div>
                        <button
                            onClick={open}
                            className="mt-1 px-6 py-2.5 rounded-xl bg-gray-800 border border-gray-700
                                text-gray-300 hover:bg-gray-700 hover:text-white transition-all text-sm font-medium"
                        >
                            Try another file
                        </button>
                    </div>
                </div>
            )}

            {/* ── Top bar: file info + reset ────────────────────────────── */}
            {(status === 'loaded' || status === 'loading') && file && (
                <div className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between
                    px-4 py-3 pointer-events-none">
                    <div className="bg-gray-900/80 backdrop-blur-md px-3 py-2 rounded-xl border border-gray-700/60
                        text-gray-300 text-sm font-mono truncate max-w-[65%] flex items-center gap-2 pointer-events-auto
                        shadow-lg">
                        <span className="text-cyan-400 flex-shrink-0">📐</span>
                        <span className="truncate">{file.name}</span>
                        <span className="text-gray-500 text-xs flex-shrink-0">
                            ({(file.size / 1024).toFixed(0)} KB)
                        </span>
                    </div>
                    <button
                        onClick={handleReset}
                        className="flex items-center gap-1.5 bg-gray-900/80 backdrop-blur-md px-3 py-2 rounded-xl
                            border border-gray-700/60 text-gray-400 hover:text-white hover:bg-gray-800/90
                            transition-all text-sm pointer-events-auto shadow-lg"
                    >
                        <RotateCcw size={13} />
                        New file
                    </button>
                </div>
            )}

            {/* ── Drag-over replace overlay (when model is loaded) ──────── */}
            {status === 'loaded' && isDragActive && (
                <div className="absolute inset-0 z-40 flex items-center justify-center
                    bg-cyan-900/15 border-2 border-cyan-400/60 border-dashed rounded-xl m-2 pointer-events-none
                    backdrop-blur-sm">
                    <p className="text-cyan-300 text-lg font-semibold">Release to replace model</p>
                </div>
            )}
        </div>
    );
}
