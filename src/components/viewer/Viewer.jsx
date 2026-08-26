import React, { useState, useCallback, useEffect, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { useDropzone } from 'react-dropzone';
import { Upload, RotateCcw, AlertCircle, Loader2, Box, FileText, PlusCircle } from 'lucide-react';
import Scene from './Scene';
import { parseStepFile } from '../../lib/occt';
import { computeMetrics } from '../../lib/metrics';

const API = '/api';

/**
 * AccuDesign Viewer — Phase 5
 *
 * Accepts BOTH STEP files (.step/.stp) and PDF engineering drawings (.pdf).
 * - STEP files → parsed via occt-import-js WASM → 3D render + metrics
 * - PDF files  → displayed inline as embedded PDF + sent to backend Gemini AI for analysis
 *
 * Now supports multi-part accumulation:
 * - "New File" resets everything (starts fresh quotation)
 * - "Add Part" appends a new part to the current quotation
 */
export default function Viewer({ onMetrics, onAddPart, hasExistingParts = false, activePart = null, onUpdatePartData = null }) {
    const [file, setFile] = useState(null);
    const [fileType, setFileType] = useState(null);    // 'step' | 'pdf'
    const [status, setStatus] = useState('idle');       // idle|loading|loaded|error|pdf_loaded
    const [errorMsg, setErrorMsg] = useState('');
    const [occtResult, setOcctResult] = useState(null);
    const [pdfUrl, setPdfUrl] = useState(null);         // Object URL for PDF preview
    const [showPdfToast, setShowPdfToast] = useState(false);
    const [extractedMetrics, setExtractedMetrics] = useState(null);
    const [isAddingPart, setIsAddingPart] = useState(false); // tracks if current upload is "add part"
    const [viewerMetrics, setViewerMetrics] = useState(null); // metrics shown on 3D viewer HUD

    // Cleanup PDF URL on component unmount or reset
    useEffect(() => {
        return () => {
            if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        };
    }, [pdfUrl]);

    // ── Process STEP file via OCCT ──────────────────────────────────────────
    const processStepFile = useCallback(async (f, addingPart = false) => {
        setFile(f);
        setFileType('step');
        setStatus('loading');
        setOcctResult(null);
        setErrorMsg('');
        setIsAddingPart(addingPart);
        if (pdfUrl) { URL.revokeObjectURL(pdfUrl); setPdfUrl(null); }

        try {
            const result = await parseStepFile(f);

            if (!result || !result.meshes || result.meshes.length === 0) {
                throw new Error('No geometry found in file.');
            }

            setOcctResult(result);
            setStatus('loaded');

            const metrics = computeMetrics(result, f);
            setViewerMetrics(metrics);

            if (addingPart && onAddPart) {
                // Adding as a new part to existing quotation
                onAddPart(metrics, f, result);
            } else if (onMetrics) {
                onMetrics(metrics, f, result);
            }
        } catch (err) {
            console.error('[Viewer] OCCT parse error:', err);
            setStatus('error');
            setErrorMsg(err.message || 'Failed to parse file. Ensure it is a valid STEP/STP file.');
        }
    }, [onMetrics, onAddPart, pdfUrl]);

    // ── Process PDF file — show preview + analyze via Gemini ────────────────
    const processPdfFile = useCallback(async (f, addingPart = false) => {
        setFile(f);
        setFileType('pdf');
        setStatus('loading');
        setOcctResult(null);
        setErrorMsg('');
        setIsAddingPart(addingPart);

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

            const safeNum = (val, fallback=0) => {
                if (typeof val === 'number') return val;
                if (!val) return fallback;
                const m = String(val).match(/[-+]?\d*\.?\d+/);
                return m ? parseFloat(m[0]) : fallback;
            };

            const pdfMetrics = {
                fileName: f.name,
                fileSize: f.size,
                meshCount: parts.length,
                vertices: 0,
                triangles: 0,
                unit: 'Millimeter',
                sizeX: safeNum(bb.sizeX || dims.length || dims.diameter).toFixed(2),
                sizeY: safeNum(bb.sizeY || dims.width || dims.diameter).toFixed(2),
                sizeZ: safeNum(bb.sizeZ || dims.height || dims.depth).toFixed(2),
                volume: safeNum(geom.volume || firstPart.estimated_volume_mm3).toFixed(2),
                surfaceArea: safeNum(geom.surfaceArea || firstPart.estimated_surface_area_mm2).toFixed(2),
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
                bendsCount: safeNum(firstPart.bends_count || 0),
                bendLengthMm: safeNum(firstPart.bend_length_mm || 0.0),
                reasoning: result.reasoning || null,
                // Client info extracted from PDF
                clientName: result.client_info?.client_name || null,
                clientCompany: result.client_info?.client_company || null,
            };

            setStatus('pdf_loaded');
            setShowPdfToast(true);
            setExtractedMetrics(pdfMetrics);
            setTimeout(() => {
                setShowPdfToast(false);
            }, 5000); // give the user 5 seconds to read it

            if (addingPart && onAddPart) {
                // Adding as a new part to existing quotation
                onAddPart(pdfMetrics, f, null);
            } else if (onMetrics) {
                onMetrics(pdfMetrics, f, null);
            }
        } catch (err) {
            console.error('[Viewer] PDF analysis error:', err);
            setStatus('error');
            setErrorMsg(err.message || 'Failed to analyze PDF. Is the backend running with the ACCU AI configuration?');
        }
    }, [onMetrics, onAddPart, pdfUrl]);

    // ── Universal file handler ──────────────────────────────────────────────
    const processFile = useCallback(async (f, addingPart = false) => {
        const fname = (f.name || '').toLowerCase();
        if (fname.endsWith('.pdf')) {
            await processPdfFile(f, addingPart);
        } else {
            await processStepFile(f, addingPart);
        }
    }, [processStepFile, processPdfFile]);

    // ── Dropzone — accepts STEP and PDF ─────────────────────────────────────
    const onDrop = useCallback((acceptedFiles) => {
        if (acceptedFiles.length > 0) processFile(acceptedFiles[0], false);
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
        setExtractedMetrics(null);
        setIsAddingPart(false);
        setViewerMetrics(null);
        if (onMetrics) onMetrics(null);
    }, [onMetrics, pdfUrl]);

    // ── "Add Part" handler — opens file picker for additional part ──────────
    const handleAddPart = useCallback(() => {
        // Create a hidden input to pick file
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.step,.stp,.pdf';
        input.onchange = (e) => {
            const f = e.target.files?.[0];
            if (f) processFile(f, true);
        };
        input.click();
    }, [processFile]);

    const loadCadFromSession = useCallback(async (sessionId, fileName) => {
        setStatus('loading');
        setErrorMsg('');
        try {
            const downloadUrl = `/api/design/sessions/${sessionId}/download-cad`;
            const resp = await fetch(downloadUrl);
            if (!resp.ok) {
                throw new Error(`Failed to download CAD from server (status ${resp.status})`);
            }
            const blob = await resp.blob();
            const f = new File([blob], fileName || 'model.step', { type: 'model/step' });
            
            const result = await parseStepFile(f);
            if (!result || !result.meshes || result.meshes.length === 0) {
                throw new Error('No geometry found in downloaded file.');
            }
            
            setFile(f);
            setFileType('step');
            setOcctResult(result);
            setStatus('loaded');
            
            const metrics = computeMetrics(result, f);
            setViewerMetrics(metrics);
            
            if (onUpdatePartData && activePart) {
                onUpdatePartData(activePart.id, {
                    file: f,
                    occtResult: result,
                    brepStatus: 'ready'
                });
            }
        } catch (err) {
            console.error('[Viewer] Failed to load CAD from session:', err);
            setStatus('error');
            setErrorMsg(err.message || 'Failed to download the generated CAD file from the server.');
        }
    }, [activePart, onUpdatePartData]);

    // ── Restore state when activePart changes (Switching Context) ─────────
    useEffect(() => {
        if (activePart && activePart.file) {
            const f = activePart.file;
            const fname = (f.name || '').toLowerCase();
            
            // If the Viewer is already showing this EXACT file, do nothing.
            // We use file name as a heuristic to avoid unnecessary re-renders.
            if (file && file.name === f.name) return;

            setFile(f);
            setIsAddingPart(false);
            setViewerMetrics(activePart.metrics || null);
            
            if (fname.endsWith('.pdf')) {
                setFileType('pdf');
                if (pdfUrl) URL.revokeObjectURL(pdfUrl);
                setPdfUrl(URL.createObjectURL(f));
                setStatus('pdf_loaded');
                setOcctResult(null);
                setExtractedMetrics(activePart.metrics);
                setErrorMsg('');
            } else {
                setFileType('step');
                if (pdfUrl) { URL.revokeObjectURL(pdfUrl); setPdfUrl(null); }
                if (activePart.occtResult) {
                    setOcctResult(activePart.occtResult);
                    setStatus('loaded');
                } else {
                    // Fallback to reparsing if occtResult wasn't provided
                    processStepFile(f, false);
                }
            }
        } else if (activePart && !activePart.file && activePart.metrics?.designSession) {
            // Avoid triggering if already loading or in error state
            if (status === 'loading' || status === 'error') return;
            
            loadCadFromSession(activePart.metrics.designSession, activePart.fileName);
        }
    }, [activePart, loadCadFromSession, status, file, pdfUrl]);

    return (
        <div className="w-full h-full relative bg-[#f1f5f9]" {...getRootProps()}>
            <input {...getInputProps()} />

            {/* ── 3D Canvas — only for STEP files ────────────────────────── */}
            {status === 'loaded' && occtResult && (
                <Canvas
                    className="absolute inset-0"
                    camera={{ fov: 45, near: 0.01, far: 1e7 }}
                    gl={{ antialias: true, alpha: false, preserveDrawingBuffer: true }}
                    style={{ background: '#f1f5f9' }}
                    shadows
                >
                    <Suspense fallback={null}>
                        <Scene occtResult={occtResult} />
                    </Suspense>
                </Canvas>
            )}

            {/* ── On-Screen Metrics HUD ──────────────────────────────── */}
            {status === 'loaded' && viewerMetrics && (
                <div className="absolute bottom-4 right-4 z-20 pointer-events-none">
                    <div className="bg-white/95 backdrop-blur-md rounded-xl border border-slate-200/90
                        px-3.5 py-2.5 shadow-lg" style={{ minWidth: 175 }}>
                        <p className="text-[9px] text-slate-500 uppercase tracking-widest font-bold mb-1.5
                            flex items-center gap-1">
                            <span>📐</span> Model Dimensions
                        </p>
                        <div className="space-y-0.5 text-[11px] font-mono">
                            <div className="flex justify-between gap-6">
                                <span className="text-red-500 font-bold">X</span>
                                <span className="text-slate-800 font-semibold">{viewerMetrics.sizeX} <span className="text-slate-400 text-[9px]">mm</span></span>
                            </div>
                            <div className="flex justify-between gap-6">
                                <span className="text-emerald-600 font-bold">Y</span>
                                <span className="text-slate-800 font-semibold">{viewerMetrics.sizeY} <span className="text-slate-400 text-[9px]">mm</span></span>
                            </div>
                            <div className="flex justify-between gap-6">
                                <span className="text-accu-600 font-bold">Z</span>
                                <span className="text-slate-800 font-semibold">{viewerMetrics.sizeZ} <span className="text-slate-400 text-[9px]">mm</span></span>
                            </div>
                        </div>
                        <div className="border-t border-slate-100 mt-1.5 pt-1.5 space-y-0.5 text-[10px]">
                            <div className="flex justify-between gap-4">
                                <span className="text-slate-500">Volume</span>
                                <span className="text-accu-700 font-bold font-mono">
                                    {Number(viewerMetrics.volume).toLocaleString()} <span className="text-slate-400 text-[8px]">mm³</span>
                                </span>
                            </div>
                            <div className="flex justify-between gap-4">
                                <span className="text-slate-500">Surface</span>
                                <span className="text-accu-700 font-bold font-mono">
                                    {Number(viewerMetrics.surfaceArea).toLocaleString()} <span className="text-slate-400 text-[8px]">mm²</span>
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ── PDF PREVIEW — shows the actual PDF inline ──────────────── */}
            {(status === 'pdf_loaded' || (status === 'loading' && fileType === 'pdf')) && pdfUrl && (
                <div className="absolute inset-0 z-10 flex flex-col bg-slate-100">

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
                                bg-white/95 backdrop-blur-xl border border-accu-300
                                shadow-lg">
                                <Loader2 size={16} className="text-accu-600 animate-spin flex-shrink-0" />
                                <div className="flex-1">
                                    <p className="text-[11px] text-accu-700 font-bold">
                                        {isAddingPart ? 'Adding Part with ACCU AI…' : 'Analyzing with ACCU AI…'}
                                    </p>
                                    <p className="text-[9px] text-slate-500 font-mono">
                                        Extracting dimensions, materials, tolerances & client info
                                    </p>
                                </div>
                                <div className="flex gap-1">
                                    <span className="w-1.5 h-1.5 rounded-full bg-accu-500 animate-bounce"
                                        style={{ animationDelay: '0ms' }} />
                                    <span className="w-1.5 h-1.5 rounded-full bg-accu-500 animate-bounce"
                                        style={{ animationDelay: '150ms' }} />
                                    <span className="w-1.5 h-1.5 rounded-full bg-accu-500 animate-bounce"
                                        style={{ animationDelay: '300ms' }} />
                                </div>
                            </div>
                        </div>
                    )}

                    {(status === 'pdf_loaded' && showPdfToast) && (
                        <div className="absolute bottom-0 left-0 right-0 z-20 pointer-events-none fade-out-animation transition-opacity duration-500">
                            <div className="mx-4 mb-4 px-4 py-2.5 rounded-xl flex items-center gap-3
                                bg-white/95 backdrop-blur-xl border border-emerald-300
                                shadow-lg">
                                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 flex-shrink-0 shadow-sm" />
                                <p className="text-[10px] text-emerald-700 font-mono font-bold">
                                    {isAddingPart
                                        ? '✓ Part added — Check Quote tab for combined costing'
                                        : '✓ PDF analyzed — Dimensions extracted — Check Details & Quote tabs'}
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
                        ${isDragActive ? 'bg-accu-50/70' : 'bg-transparent'}`}
                    onClick={open}
                >
                    {/* Animated ring */}
                    <div className={`relative w-40 h-40 mb-8 rounded-full border-2 flex items-center justify-center
                        transition-all duration-300 bg-white
                        ${isDragActive
                            ? 'border-accu-500 shadow-xl scale-110'
                            : 'border-slate-300 hover:border-accu-500 hover:scale-105 hover:shadow-lg'}`}
                    >
                        {isDragActive && (
                            <>
                                <div className="absolute inset-0 rounded-full border-2 border-accu-400 animate-ping opacity-30" />
                                <div className="absolute inset-[-8px] rounded-full border border-accu-400/30 animate-pulse" />
                            </>
                        )}
                        <Box
                            size={52}
                            className={`transition-colors duration-300 ${isDragActive ? 'text-accu-600' : 'text-accu-500'}`}
                            strokeWidth={1.4}
                        />
                    </div>

                    <h2 className="text-2xl font-bold text-slate-900 mb-2 tracking-tight font-heading">
                        {isDragActive ? 'Release to load' : 'Drop your CAD or Drawing file'}
                    </h2>
                    <p className="text-accu-600 font-mono text-sm mb-1 font-bold">.STEP · .STP · .PDF</p>
                    <p className="text-slate-500 text-xs mb-6">Precision CAD models or 2D engineering drawings</p>

                    <button
                        className="px-7 py-3 rounded-xl bg-white border border-slate-300
                            text-slate-800 hover:bg-accu-600 hover:text-white hover:border-accu-600
                            transition-all duration-200 text-sm font-semibold shadow-sm hover:shadow-md"
                    >
                        Browse Files
                    </button>
                </div>
            )}

            {/* ── LOADING overlay ────────────────────────────────────────── */}
            {status === 'loading' && fileType !== 'pdf' && (
                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center
                    bg-white/95 backdrop-blur-sm">
                    <div className="relative mb-6">
                        <Loader2 size={48} className="text-accu-600 animate-spin" />
                        <div className="absolute inset-0 rounded-full bg-accu-100 animate-pulse" />
                    </div>
                    <p className="text-slate-900 font-bold text-lg mb-1 font-heading">
                        {isAddingPart ? 'Adding part geometry' : 'Parsing CAD geometry'}
                    </p>
                    <p className="text-accu-600 text-sm mb-1 font-mono font-bold">{file?.name}</p>
                    <p className="text-slate-500 text-xs">Running OCCT WebAssembly CAD kernel…</p>
                </div>
            )}

            {/* ── ERROR overlay ──────────────────────────────────────────── */}
            {status === 'error' && (
                <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/95">
                    <div className="flex flex-col items-center gap-4 p-8 rounded-2xl
                        bg-red-50 border border-red-200 max-w-sm mx-4 text-center
                        shadow-xl">
                        <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center">
                            <AlertCircle size={36} className="text-red-500" />
                        </div>
                        <div>
                            <p className="text-red-800 font-bold text-xl mb-2 font-heading">
                                {fileType === 'pdf' ? 'PDF Analysis Failed' : 'Import Failed'}
                            </p>
                            <p className="text-red-600 text-sm leading-relaxed">{errorMsg}</p>
                        </div>
                        {activePart?.metrics?.designSession ? (
                            <button
                                onClick={() => loadCadFromSession(activePart.metrics.designSession, activePart.fileName)}
                                className="mt-1 px-6 py-2.5 rounded-xl bg-accu-50 border border-accu-300
                                    text-accu-700 hover:bg-accu-600 hover:text-white transition-all text-sm font-semibold"
                            >
                                Reload from Server
                            </button>
                        ) : (
                            <button
                                onClick={open}
                                className="mt-1 px-6 py-2.5 rounded-xl bg-white border border-slate-300
                                    text-slate-700 hover:bg-slate-50 transition-all text-sm font-medium shadow-sm"
                            >
                                Try another file
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* ── Top bar: file info + New File + Add Part ─────────────────── */}
            {(status === 'loaded' || status === 'loading' || status === 'pdf_loaded') && file && (
                <div className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between
                    px-4 py-3 pointer-events-none">
                    <div className="bg-white/95 backdrop-blur-md px-3.5 py-2 rounded-xl border border-slate-200
                        text-slate-800 text-sm font-mono truncate max-w-[50%] flex items-center gap-2 pointer-events-auto
                        shadow-sm">
                        <span className="text-accu-600 flex-shrink-0">
                            {fileType === 'pdf' ? '📄' : '📐'}
                        </span>
                        <span className="truncate font-semibold">{file.name}</span>
                        <span className="text-slate-400 text-xs flex-shrink-0">
                            ({(file.size / 1024).toFixed(0)} KB)
                        </span>
                    </div>
                    <div className="flex items-center gap-2 pointer-events-auto">
                        {/* Add Part button — AccuDesign orange accent */}
                        <button
                            onClick={(e) => { e.stopPropagation(); handleAddPart(); }}
                            className="flex items-center gap-1.5 bg-accuorange-500 px-3.5 py-2 rounded-xl
                                text-white hover:bg-accuorange-600
                                transition-all text-sm shadow-md"
                            title="Add another part to this quotation (same quote PDF)"
                        >
                            <PlusCircle size={14} />
                            <span className="font-semibold">Add Part</span>
                        </button>

                        {/* New File button */}
                        <button
                            onClick={handleReset}
                            className="flex items-center gap-1.5 bg-white backdrop-blur-md px-3.5 py-2 rounded-xl
                                border border-slate-300 text-slate-700 hover:text-slate-900 hover:bg-slate-50
                                transition-all text-sm pointer-events-auto shadow-sm"
                            title="Start a fresh quotation (clears all parts)"
                        >
                            <RotateCcw size={13} />
                            New File
                        </button>
                    </div>
                </div>
            )}

            {/* ── Drag-over replace overlay ──────────────────────────────── */}
            {(status === 'loaded' || status === 'pdf_loaded') && isDragActive && (
                <div className="absolute inset-0 z-40 flex items-center justify-center
                    bg-accu-50/80 border-2 border-accu-500 border-dashed rounded-xl m-2 pointer-events-none
                    backdrop-blur-sm shadow-xl">
                    <p className="text-accu-800 text-lg font-bold font-heading">Release to replace geometry</p>
                </div>
            )}
        </div>
    );
}
