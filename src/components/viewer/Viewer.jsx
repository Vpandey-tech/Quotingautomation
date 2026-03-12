import React, { useState, useCallback, useEffect, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { useDropzone } from 'react-dropzone';
import { Upload, RotateCcw, AlertCircle, Loader2, Box, FileText } from 'lucide-react';
import Scene from './Scene';
import { parseStepFile } from '../../lib/occt';
import { computeMetrics } from '../../lib/metrics';

const API = '/api';

/**
 * AccuDesign Viewer — Phase 4
 *
 * Accepts BOTH STEP files (.step/.stp) and PDF engineering drawings (.pdf).
 * - STEP files → parsed via occt-import-js WASM → 3D render + metrics
 * - PDF files  → displayed inline as embedded PDF + sent to backend Gemini AI for analysis
 */
export default function Viewer({ onMetrics }) {
    const [file, setFile] = useState(null);
    const [fileType, setFileType] = useState(null);    // 'step' | 'pdf'
    const [status, setStatus] = useState('idle');       // idle|loading|loaded|error|pdf_loaded
    const [errorMsg, setErrorMsg] = useState('');
    const [occtResult, setOcctResult] = useState(null);
    const [pdfUrl, setPdfUrl] = useState(null);         // Object URL for PDF preview

    // Cleanup PDF URL on component unmount or reset
    useEffect(() => {
        return () => {
            if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        };
    }, [pdfUrl]);

    // ── Process STEP file via OCCT ──────────────────────────────────────────
    const processStepFile = useCallback(async (f) => {
        setFile(f);
        setFileType('step');
        setStatus('loading');
        setOcctResult(null);
        setErrorMsg('');
        if (pdfUrl) { URL.revokeObjectURL(pdfUrl); setPdfUrl(null); }

        try {
            const result = await parseStepFile(f);

            if (!result || !result.meshes || result.meshes.length === 0) {
                throw new Error('No geometry found in file.');
            }

            setOcctResult(result);
            setStatus('loaded');

            if (onMetrics) {
                onMetrics(computeMetrics(result, f), f);
            }
        } catch (err) {
            console.error('[Viewer] OCCT parse error:', err);
            setStatus('error');
            setErrorMsg(err.message || 'Failed to parse file. Ensure it is a valid STEP/STP file.');
        }
    }, [onMetrics, pdfUrl]);

    // ── Process PDF file — show preview + analyze via Gemini ────────────────
    const processPdfFile = useCallback(async (f) => {
        setFile(f);
        setFileType('pdf');
        setStatus('loading');
        setOcctResult(null);
        setErrorMsg('');

        // Create object URL for PDF preview immediately
        if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        const url = URL.createObjectURL(f);
        setPdfUrl(url);

        try {
            const fd = new FormData();
            fd.append('file', f);
            const resp = await fetch(`${API}/analyze/pdf`, { method: 'POST', body: fd });

            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: 'PDF analysis failed' }));
                throw new Error(err.detail || `Server error ${resp.status}`);
            }

            const result = await resp.json();
            const parts = result.parts || [];

            if (parts.length === 0) {
                throw new Error('No parts could be extracted from this PDF.');
            }

            const firstPart = parts[0];
            const dims = firstPart.dimensions || {};
            const bb = firstPart.bounding_box || {};
            const geom = firstPart.geometry || {};

            const pdfMetrics = {
                fileName: f.name,
                fileSize: f.size,
                meshCount: parts.length,
                vertices: 0,
                triangles: 0,
                unit: 'Millimeter',
                sizeX: (bb.sizeX || dims.length || dims.diameter || 0).toFixed(2),
                sizeY: (bb.sizeY || dims.width || dims.diameter || 0).toFixed(2),
                sizeZ: (bb.sizeZ || dims.height || dims.depth || 0).toFixed(2),
                volume: (geom.volume || firstPart.estimated_volume_mm3 || 0).toFixed(2),
                surfaceArea: (geom.surfaceArea || firstPart.estimated_surface_area_mm2 || 0).toFixed(2),
                // PDF-specific fields
                source: 'pdf',
                partsCount: parts.length,
                material: firstPart.material || null,
                materialId: firstPart.material_id || null,
                processId: firstPart.process_id || null,
                toleranceId: firstPart.tolerance_id || null,
                partName: firstPart.name || 'Part',
                notes: firstPart.notes || '',
                holes: geom.holes || [],
                allParts: parts,
                // Client info extracted from PDF
                clientName: result.client_info?.client_name || null,
                clientCompany: result.client_info?.client_company || null,
            };

            setStatus('pdf_loaded');

            if (onMetrics) {
                onMetrics(pdfMetrics, null);
            }
        } catch (err) {
            console.error('[Viewer] PDF analysis error:', err);
            setStatus('error');
            setErrorMsg(err.message || 'Failed to analyze PDF. Is the backend running with GEMINI_API_KEY?');
        }
    }, [onMetrics, pdfUrl]);

    // ── Universal file handler ──────────────────────────────────────────────
    const processFile = useCallback(async (f) => {
        const fname = (f.name || '').toLowerCase();
        if (fname.endsWith('.pdf')) {
            await processPdfFile(f);
        } else {
            await processStepFile(f);
        }
    }, [processStepFile, processPdfFile]);

    // ── Dropzone — accepts STEP and PDF ─────────────────────────────────────
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
            'application/pdf': ['.pdf'],
        },
        multiple: false,
        noClick: true,
    });

    const handleReset = useCallback(() => {
        if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        setPdfUrl(null);
        setFile(null);
        setFileType(null);
        setStatus('idle');
        setOcctResult(null);
        setErrorMsg('');
        if (onMetrics) onMetrics(null);
    }, [onMetrics, pdfUrl]);

    return (
        <div className="w-full h-full relative bg-[#080c14]" {...getRootProps()}>
            <input {...getInputProps()} />

            {/* ── 3D Canvas — only for STEP files ────────────────────────── */}
            {status === 'loaded' && occtResult && (
                <Canvas
                    className="absolute inset-0"
                    camera={{ fov: 45, near: 0.01, far: 1e7 }}
                    gl={{ antialias: true, alpha: false, preserveDrawingBuffer: true }}
                    style={{ background: 'linear-gradient(135deg, #080c14 0%, #0d1a2e 100%)' }}
                    shadows
                >
                    <Suspense fallback={null}>
                        <Scene occtResult={occtResult} />
                    </Suspense>
                </Canvas>
            )}

            {/* ── PDF PREVIEW — shows the actual PDF inline ──────────────── */}
            {(status === 'pdf_loaded' || (status === 'loading' && fileType === 'pdf')) && pdfUrl && (
                <div className="absolute inset-0 z-10 flex flex-col"
                    style={{ background: '#1a1a2e' }}>

                    {/* PDF embedded viewer */}
                    <div className="flex-1 relative">
                        <iframe
                            src={pdfUrl}
                            className="absolute inset-0 w-full h-full border-0"
                            title="PDF Drawing Preview"
                            style={{ background: 'white' }}
                        />
                    </div>

                    {/* Status bar at bottom */}
                    {status === 'loading' && (
                        <div className="absolute bottom-0 left-0 right-0 z-20 pointer-events-none">
                            <div className="mx-4 mb-4 px-4 py-3 rounded-xl flex items-center gap-3
                                bg-gray-900/90 backdrop-blur-xl border border-cyan-500/30
                                shadow-[0_0_25px_rgba(34,211,238,0.15)]">
                                <Loader2 size={16} className="text-cyan-400 animate-spin flex-shrink-0" />
                                <div className="flex-1">
                                    <p className="text-[11px] text-cyan-300 font-bold">
                                        Analyzing with Gemini AI…
                                    </p>
                                    <p className="text-[9px] text-gray-500 font-mono">
                                        Extracting dimensions, materials, tolerances & client info
                                    </p>
                                </div>
                                <div className="flex gap-1">
                                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce"
                                        style={{ animationDelay: '0ms' }} />
                                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce"
                                        style={{ animationDelay: '150ms' }} />
                                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce"
                                        style={{ animationDelay: '300ms' }} />
                                </div>
                            </div>
                        </div>
                    )}

                    {status === 'pdf_loaded' && (
                        <div className="absolute bottom-0 left-0 right-0 z-20 pointer-events-none">
                            <div className="mx-4 mb-4 px-4 py-2.5 rounded-xl flex items-center gap-3
                                bg-gray-900/90 backdrop-blur-xl border border-green-500/30
                                shadow-[0_0_20px_rgba(74,222,128,0.1)]">
                                <span className="w-2.5 h-2.5 rounded-full bg-green-400 flex-shrink-0"
                                    style={{ boxShadow: '0 0 8px rgba(74,222,128,0.8)' }} />
                                <p className="text-[10px] text-green-300 font-mono font-bold">
                                    ✓ PDF analyzed — Dimensions extracted — Check Details & Quote tabs
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── IDLE: Full-screen drop zone ────────────────────────────── */}
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
                        {isDragActive ? 'Release to load' : 'Drop your file here'}
                    </h2>
                    <p className="text-gray-500 text-sm mb-1">.STEP · .STP · .PDF</p>
                    <p className="text-gray-600 text-xs mb-6">CAD models or PDF engineering drawings</p>

                    <button
                        className="px-6 py-2.5 rounded-xl bg-gray-800/70 border border-gray-700/80
                            text-gray-300 hover:bg-gray-700/80 hover:text-white hover:border-gray-600
                            transition-all duration-200 text-sm font-medium backdrop-blur-sm"
                    >
                        Browse files
                    </button>
                </div>
            )}

            {/* ── LOADING overlay (STEP only — PDF shows the PDF while loading) */}
            {status === 'loading' && fileType !== 'pdf' && (
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

            {/* ── ERROR overlay ──────────────────────────────────────────── */}
            {status === 'error' && (
                <div className="absolute inset-0 z-20 flex items-center justify-center bg-[#080c14]/95">
                    <div className="flex flex-col items-center gap-4 p-8 rounded-2xl
                        bg-red-950/25 border border-red-900/40 max-w-sm mx-4 text-center
                        backdrop-blur-md shadow-2xl">
                        <div className="w-16 h-16 rounded-full bg-red-900/20 flex items-center justify-center">
                            <AlertCircle size={36} className="text-red-400" />
                        </div>
                        <div>
                            <p className="text-red-300 font-bold text-xl mb-2">
                                {fileType === 'pdf' ? 'PDF Analysis Failed' : 'Import Failed'}
                            </p>
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

            {/* ── Top bar: file info + reset ─────────────────────────────── */}
            {(status === 'loaded' || status === 'loading' || status === 'pdf_loaded') && file && (
                <div className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between
                    px-4 py-3 pointer-events-none">
                    <div className="bg-gray-900/80 backdrop-blur-md px-3 py-2 rounded-xl border border-gray-700/60
                        text-gray-300 text-sm font-mono truncate max-w-[65%] flex items-center gap-2 pointer-events-auto
                        shadow-lg">
                        <span className="text-cyan-400 flex-shrink-0">
                            {fileType === 'pdf' ? '📄' : '📐'}
                        </span>
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

            {/* ── Drag-over replace overlay ──────────────────────────────── */}
            {(status === 'loaded' || status === 'pdf_loaded') && isDragActive && (
                <div className="absolute inset-0 z-40 flex items-center justify-center
                    bg-cyan-900/15 border-2 border-cyan-400/60 border-dashed rounded-xl m-2 pointer-events-none
                    backdrop-blur-sm">
                    <p className="text-cyan-300 text-lg font-semibold">Release to replace</p>
                </div>
            )}
        </div>
    );
}
