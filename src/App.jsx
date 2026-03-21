import React, { useState, useRef, useCallback } from 'react';
import Viewer from './components/viewer/Viewer';
import QuotePanel from './components/quote/QuotePanel';
import {
  Box, FileText, Activity, Ruler, FlaskConical,
  DollarSign, Layers, ChevronRight, MessageSquare, Send, X, Eye
} from 'lucide-react';

/* ─── Metric row ─────────────────────────────────────────────────────────── */
function MetricRow({ label, value, highlight }) {
  return (
    <div className="flex items-center justify-between py-[7px]
      border-b border-white/[0.035] last:border-0 px-1 rounded-md
      hover:bg-white/[0.025] transition-colors duration-150 group">
      <span className="text-[11px] text-gray-500 font-medium tracking-wide group-hover:text-gray-400 transition-colors">
        {label}
      </span>
      <span className={`font-mono text-[11px] font-semibold tracking-wider
        ${highlight ? 'text-cyan-300 drop-shadow-[0_0_6px_rgba(34,211,238,0.5)]' : 'text-gray-200'}`}>
        {value}
      </span>
    </div>
  );
}

/* ─── Section card ───────────────────────────────────────────────────────── */
function SectionCard({ icon: Icon, title, children, accent }) {
  return (
    <div className="rounded-xl overflow-hidden transition-all duration-200
      hover:shadow-[0_4px_20px_rgba(0,0,0,0.4)] group"
      style={{
        background: 'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)',
        border: '1px solid rgba(255,255,255,0.06)',
      }}>
      <div className="flex items-center gap-2 px-3.5 py-2.5
        border-b border-white/[0.05]"
        style={{ background: 'rgba(0,0,0,0.2)' }}>
        <div className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0"
          style={{ background: accent || 'rgba(34,211,238,0.1)' }}>
          <Icon size={11} className="text-cyan-400" />
        </div>
        <h2 className="text-[10px] font-bold text-gray-300 uppercase tracking-[0.12em]">
          {title}
        </h2>
      </div>
      <div className="px-3.5 py-2">{children}</div>
    </div>
  );
}

/* ─── Tab button ─────────────────────────────────────────────────────────── */
function Tab({ active, onClick, icon: Icon, label, badge }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-[10px]
        font-bold uppercase tracking-[0.12em] transition-all duration-200 relative
        ${active
          ? 'text-cyan-300'
          : 'text-gray-600 hover:text-gray-400 hover:bg-white/[0.02]'
        }`}
    >
      <Icon size={12} className={active ? 'drop-shadow-[0_0_4px_rgba(34,211,238,0.6)]' : ''} />
      {label}
      {badge > 0 && (
        <span className="ml-1 w-4 h-4 rounded-full bg-emerald-500/80 text-white text-[8px] font-bold
          flex items-center justify-center leading-none shadow-[0_0_6px_rgba(16,185,129,0.5)]">
          {badge}
        </span>
      )}
      {active && (
        <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-[2px] rounded-full"
          style={{ background: 'linear-gradient(90deg, transparent, #22d3ee, transparent)' }} />
      )}
    </button>
  );
}

/* ─── App ────────────────────────────────────────────────────────────────── */
export default function App() {
  const [metrics, setMetrics] = useState(null);
  const [geometry, setGeometry] = useState(null);
  const [brepStatus, setBrepStatus] = useState('idle'); // idle|loading|ready|offline
  const [tab, setTab] = useState('details');
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [isAiTyping, setIsAiTyping] = useState(false);

  // ── Multi-part state ──────────────────────────────────────────────────────
  // Each "part" stores its own metrics, geometry, and file reference
  const [parts, setParts] = useState([]);
  const [activePartId, setActivePartId] = useState(null);
  
  // Update a part's config/quote data
  const handleUpdatePartData = useCallback((id, data) => {
    setParts(prev => prev.map(p => p.id === id ? { ...p, ...data } : p));
  }, []);

  // Track sidebar hover to block pointer events on 3D canvas
  const [sidebarHovered, setSidebarHovered] = useState(false);

  // ── Draggable sidebar width ──
  const [sidebarWidth, setSidebarWidth] = useState(340);
  const isDraggingRef = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(340);

  const viewerRef = useRef(null);

  // Capture screenshot of 3D canvas for PDF isometric view
  const captureScreenshot = useCallback(() => {
    try {
      const canvas = document.querySelector('canvas');
      if (canvas) return canvas.toDataURL('image/png');
    } catch (e) {
      console.warn('Screenshot capture failed:', e);
    }
    return null;
  }, []);

  const handleSidebarEnter = useCallback(() => {
    setSidebarHovered(true);
    // Directly block pointer events on canvas so OrbitControls can't see wheel
    if (viewerRef.current) {
      viewerRef.current.style.pointerEvents = 'none';
    }
  }, []);

  const handleSidebarLeave = useCallback(() => {
    setSidebarHovered(false);
    if (viewerRef.current) {
      viewerRef.current.style.pointerEvents = 'auto';
    }
  }, []);

  // ── Sidebar resize drag handler ──
  const handleResizeStart = useCallback((e) => {
    e.preventDefault();
    isDraggingRef.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    if (viewerRef.current) {
      viewerRef.current.style.pointerEvents = 'none';
    }

    const onMove = (moveE) => {
      if (!isDraggingRef.current) return;
      const delta = moveE.clientX - dragStartX.current;
      const clamped = Math.min(Math.max(dragStartWidth.current + delta, 280), window.innerWidth * 0.75);
      setSidebarWidth(clamped);
    };

    const onUp = () => {
      isDraggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      
      // Restore pointer events UNLESS sidebar is currently hovered
      if (viewerRef.current && !sidebarHovered) {
        viewerRef.current.style.pointerEvents = 'auto';
      }
      
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [sidebarWidth]);

  // ── Build geometry from metrics helper ──
  const buildGeometry = (m) => {
    if (!m) return null;
    return {
      volume: parseFloat(m.volume) || 0,
      surfaceArea: parseFloat(m.surfaceArea) || 0,
      boundingBox: {
        sizeX: parseFloat(m.sizeX) || 0,
        sizeY: parseFloat(m.sizeY) || 0,
        sizeZ: parseFloat(m.sizeZ) || 0,
      },
      complexity: { tier: 'Moderate', score: 150, faces: 0, edges: 0, holes: 0 },
      holes: m.holes || [],
    };
  };

  // Called by Viewer with mesh metrics + original File object
  // This is the PRIMARY file handler — resets parts and starts fresh
  const handleMetrics = async (m, file, result) => {
    if (!m) {
      setMetrics(null);
      setGeometry(null);
      setBrepStatus('idle');
      setParts([]); // Clear all parts on reset
      setActivePartId(null);
      return;
    }
    setMetrics(m);

    // Build geometry object from metrics
    const geom = buildGeometry(m);

    // When a new file is loaded (not Add Part), reset parts and add this as part 1
    const newId = Date.now();
    const newPart = {
      id: newId,
      metrics: m,
      geometry: geom,
      file: file,
      fileName: m.fileName || 'Part 1',
      occtResult: result,
      brepStatus: m.source === 'pdf' ? 'pdf' : 'loading',
      config: null,
      quote: null,
      materialEstimate: null,
      aiValidation: null,
    };
    setParts([newPart]);
    setActivePartId(newId);

    // For PDF files — geometry is already extracted by Gemini, no B-Rep needed
    if (m.source === 'pdf') {
      setGeometry(geom);
      setBrepStatus('pdf');
      
      // Initialize chat with the AI's reasoning from the analysis
      if (m.reasoning) {
        setChatMessages([
          { role: 'assistant', text: "ACCU AI Analysis Complete.\n" + m.reasoning }
        ]);
      } else {
        setChatMessages([
          { role: 'assistant', text: "ACCU AI Analysis Complete. I've populated the quote details based on the provided PDF drawing. Let me know if you need to adjust any parameters." }
        ]);
      }
      return;
    }

    // For STEP files — set mesh geometry first, then try B-Rep
    setGeometry(geom);

    if (!file) return;
    setBrepStatus('loading');
    
    // Auto-clear loading state after 3.5 seconds
    const loadingTimeout = setTimeout(() => {
      setBrepStatus(prev => prev === 'loading' ? 'ready' : prev);
    }, 3500);

    try {
      const fd = new FormData();
      fd.append('file', file);
      const resp = await fetch('/api/analyze', { method: 'POST', body: fd });
      clearTimeout(loadingTimeout);
      if (resp.ok) {
        const brepGeom = await resp.json();
        setGeometry(brepGeom);
        setBrepStatus('ready');
        // Update the part's geometry with B-Rep data
        setParts(prev => prev.map(p => p.id === newId ? { ...p, geometry: brepGeom, brepStatus: 'ready' } : p));
      } else {
        setBrepStatus('offline');
        setParts(prev => prev.map(p => p.id === newId ? { ...p, brepStatus: 'offline' } : p));
      }
    } catch {
      clearTimeout(loadingTimeout);
      setBrepStatus('offline');
      setParts(prev => prev.map(p => p.id === newId ? { ...p, brepStatus: 'offline' } : p));
    }
  };

  // ── "Add Part" handler — appends a new part without resetting existing ones ──
  const handleAddPart = async (m, file, result) => {
    if (!m) return;

    const geom = buildGeometry(m);
    const activePart = parts.find(p => p.id === activePartId);
    
    // Deep clone the active config to avoid unintended reference sharing, but reset quantity to 1 for the new part
    const newConfig = activePart?.config ? JSON.parse(JSON.stringify(activePart.config)) : null;
    if (newConfig) {
        newConfig.quantity = 1;
    }

    const newId = Date.now();

    const newPart = {
      id: newId,
      metrics: m,
      geometry: geom,
      file: file,
      fileName: m.fileName || `Part ${parts.length + 1}`,
      occtResult: result,
      brepStatus: m.source === 'pdf' ? 'pdf' : 'loading',
      config: newConfig,
      quote: null,
      materialEstimate: null,
      aiValidation: null,
    };

    setParts(prev => [...prev, newPart]);
    setActivePartId(newId);

    // Update current display metrics/geometry to the latest added part
    setMetrics(m);
    setGeometry(geom);

    if (m.source === 'pdf') {
      setBrepStatus('pdf');
    } else if (file) {
      setBrepStatus('loading');
      const loadingTimeout = setTimeout(() => {
        setBrepStatus(prev => prev === 'loading' ? 'ready' : prev);
      }, 3500);
      try {
        const fd = new FormData();
        fd.append('file', file);
        const resp = await fetch('/api/analyze', { method: 'POST', body: fd });
        clearTimeout(loadingTimeout);
        if (resp.ok) {
          const brepGeom = await resp.json();
          setGeometry(brepGeom);
          setBrepStatus('ready');
          setParts(prev => prev.map(p => p.id === newId ? { ...p, geometry: brepGeom, brepStatus: 'ready' } : p));
        } else {
          setBrepStatus('offline');
          setParts(prev => prev.map(p => p.id === newId ? { ...p, brepStatus: 'offline' } : p));
        }
      } catch {
        clearTimeout(loadingTimeout);
        setBrepStatus('offline');
        setParts(prev => prev.map(p => p.id === newId ? { ...p, brepStatus: 'offline' } : p));
      }
    }

    // Auto-switch to Quote tab when adding parts
    if (parts.length >= 1) {
      setTab('quote');
    }
  };

  // ── Context Switching: Selecting an existing part
  const handleSelectPart = (id) => {
    if (activePartId === id) return;
    const part = parts.find(p => p.id === id);
    if (!part) return;
    setActivePartId(id);
    setMetrics(part.metrics);
    setGeometry(part.geometry);
    setBrepStatus(part.brepStatus || 'idle');
  };

  // ── Remove a specific part ──
  const handleRemovePart = (partId) => {
    setParts(prev => {
      const updated = prev.filter(p => p.id !== partId);
      // If no parts left, reset everything
      if (updated.length === 0) {
        setMetrics(null);
        setGeometry(null);
        setBrepStatus('idle');
        setActivePartId(null);
        return [];
      }
      
      // If we removed the currently active part, fallback to the last part
      if (partId === activePartId) {
        const last = updated[updated.length - 1];
        setActivePartId(last.id);
        setMetrics(last.metrics);
        setGeometry(last.geometry);
        setBrepStatus(last.brepStatus || 'idle');
      }
      return updated;
    });
  };

  const handleSendChat = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || isAiTyping) return;
    
    const newMsgs = [...chatMessages, { role: 'user', text: chatInput }];
    setChatMessages(newMsgs);
    setChatInput('');
    setIsAiTyping(true);
    
    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message: chatInput, metrics: metrics })
        });
        const data = await resp.json();
        
        if (data.metrics) {
            setMetrics(data.metrics);
        }
        
        setChatMessages([...newMsgs, { 
            role: 'assistant', 
            text: data.response || "Updated."
        }]);
    } catch (err) {
        setChatMessages([...newMsgs, { 
            role: 'assistant', 
            text: "Network error trying to reach ACCU AI." 
        }]);
    } finally {
        setIsAiTyping(false);
    }
  };

  return (
    <div className="h-screen bg-[#080c14] text-white flex flex-col font-sans overflow-hidden">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="h-14 px-5 flex items-center justify-between flex-shrink-0 z-50"
        style={{
          background: 'rgba(8,12,20,0.95)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          backdropFilter: 'blur(24px)',
        }}>
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{
              background: 'linear-gradient(135deg, #22d3ee, #3b82f6, #6366f1)',
              boxShadow: '0 0 16px rgba(34,211,238,0.35)',
            }}>
            <Box size={16} className="text-white" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="text-[15px] font-black tracking-tight leading-none"
              style={{
                background: 'linear-gradient(90deg, #fff 0%, #e0f7fa 40%, #22d3ee 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>
              AccuDesign
            </h1>
            <p className="text-[9px] text-gray-600 tracking-wider font-medium leading-none mt-0.5">
              MANUFACTURING QUOTES
            </p>
          </div>
        </div>

        {/* Status badges */}
        <div className="flex items-center gap-2">
          {/* Parts count badge */}
          {parts.length > 1 && (
            <span className="text-[10px] font-mono font-medium px-2.5 py-1 rounded-full flex items-center gap-1.5"
              style={{
                background: 'rgba(16,185,129,0.08)',
                border: '1px solid rgba(16,185,129,0.25)',
                color: '#6ee7b7',
              }}>
              <Layers size={10} />
              {parts.length} Parts
            </span>
          )}
          {metrics && (
            <span className="text-[10px] font-mono font-medium px-2.5 py-1 rounded-full flex items-center gap-1.5"
              style={{
                background: 'rgba(74,222,128,0.08)',
                border: '1px solid rgba(74,222,128,0.25)',
                color: '#86efac',
              }}>
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block animate-pulse"
                style={{ boxShadow: '0 0 6px rgba(74,222,128,0.8)' }} />
              Geometry Ready
            </span>
          )}
          {brepStatus === 'loading' && (
            <span className="text-[10px] font-mono font-medium px-2.5 py-1 rounded-full flex items-center gap-1.5"
              style={{
                background: 'rgba(96,165,250,0.08)',
                border: '1px solid rgba(96,165,250,0.25)',
                color: '#93c5fd',
              }}>
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 inline-block animate-ping" />
              Analyzing…
            </span>
          )}
          {brepStatus === 'ready' && (
            <span className="text-[10px] font-mono font-medium px-2.5 py-1 rounded-full"
              style={{
                background: 'rgba(34,211,238,0.08)',
                border: '1px solid rgba(34,211,238,0.2)',
                color: '#67e8f9',
              }}>
              ✓ B-Rep Ready
            </span>
          )}
          {brepStatus === 'offline' && (
            <span className="text-[10px] font-mono font-medium px-2.5 py-1 rounded-full flex items-center gap-1"
              style={{
                background: 'rgba(251,191,36,0.08)',
                border: '1px solid rgba(251,191,36,0.2)',
                color: '#fcd34d',
              }}>
              ◐ Mesh Only
            </span>
          )}
          {brepStatus === 'pdf' && (
            <span className="text-[10px] font-mono font-medium px-2.5 py-1 rounded-full flex items-center gap-1.5"
              style={{
                background: 'rgba(168,85,247,0.08)',
                border: '1px solid rgba(168,85,247,0.25)',
                color: '#c084fc',
              }}>
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400 inline-block animate-pulse"
                style={{ boxShadow: '0 0 6px rgba(168,85,247,0.8)' }} />
              AI Analyzed
            </span>
          )}
          <span className="text-[10px] text-gray-600 font-mono px-2.5 py-1 rounded-full"
            style={{ border: '1px solid rgba(255,255,255,0.07)' }}>
            v0.5.0
          </span>
        </div>
      </header>

      {/* ── Main layout ──────────────────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── Sidebar ────────────────────────────────────────────────────────── */}
        <aside
          className="flex-shrink-0 flex flex-col z-40 sidebar-bg"
          style={{ width: sidebarWidth, minWidth: 280, maxWidth: '75vw' }}
          onMouseEnter={handleSidebarEnter}
          onMouseLeave={handleSidebarLeave}
        >
          {/* Tab bar */}
          <div className="flex flex-shrink-0"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.07)', background: 'rgba(0,0,0,0.3)' }}>
            <Tab active={tab === 'details'} onClick={() => setTab('details')}
              icon={Layers} label="Details" />
            <Tab active={tab === 'quote'} onClick={() => setTab('quote')}
              icon={DollarSign} label="Quote" badge={parts.length > 1 ? parts.length : 0} />
          </div>

          {/* ── Scrollable content — completely isolated scroll context ── */}
          <div className="flex-1 sidebar-scroll-container p-3 space-y-3 min-h-0">

            {tab === 'details' && (
              <>
                {/* File card */}
                <SectionCard icon={FileText} title="File">
                  {metrics ? (
                    <div className="py-1.5">
                      <p className="text-[11px] text-cyan-300 font-mono truncate font-medium leading-tight"
                        title={metrics.fileName}>{metrics.fileName}</p>
                      <p className="text-[10px] text-gray-600 mt-0.5 font-mono">
                        {(metrics.fileSize / 1024).toFixed(1)} KB · STEP / ISO 10303
                      </p>
                      {parts.length > 1 && (
                        <p className="text-[9px] text-emerald-400/80 font-mono mt-1 flex items-center gap-1">
                          <Layers size={9} /> {parts.length} parts in this quotation
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="py-3 flex flex-col items-center gap-1.5">
                      <ChevronRight size={14} className="text-gray-700 rotate-90" />
                      <p className="text-[10px] text-gray-700 text-center leading-relaxed">
                        Drop a .STEP file<br />in the viewer →
                      </p>
                    </div>
                  )}
                </SectionCard>

                {/* Parts list (when multiple) */}
                {parts.length > 1 && (
                  <SectionCard icon={Layers} title={`Parts (${parts.length})`} accent="rgba(16,185,129,0.1)">
                    <div className="space-y-1.5">
                      {parts.map((part, idx) => {
                        const isActive = part.id === activePartId;
                        return (
                          <div key={part.id}
                            onClick={() => handleSelectPart(part.id)}
                            className={`flex items-center justify-between gap-2 px-2 py-1.5 rounded-lg
                              border cursor-pointer transition-all duration-200
                              ${isActive 
                                ? 'bg-emerald-900/40 border-emerald-500/50 shadow-[0_0_10px_rgba(16,185,129,0.1)]' 
                                : 'bg-white/[0.03] border-white/[0.05] hover:border-emerald-500/30 hover:bg-white/[0.06]'}`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <span className={`w-5 h-5 rounded-md text-[9px] font-bold flex items-center justify-center flex-shrink-0
                                ${isActive ? 'bg-emerald-500/90 text-white shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-emerald-500/20 text-emerald-300'}`}>
                                {idx + 1}
                              </span>
                              <span className={`text-[10px] font-mono truncate transition-colors
                                ${isActive ? 'text-emerald-100 font-bold' : 'text-gray-300'}`}>
                                {part.fileName}
                              </span>
                            </div>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleRemovePart(part.id); }}
                              className="text-gray-600 hover:text-red-400 hover:bg-red-500/10 rounded-sm transition-all flex-shrink-0 p-1"
                              title="Remove this part"
                            >
                              <X size={12} />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </SectionCard>
                )}

                {/* Properties */}
                <SectionCard icon={FlaskConical} title="Properties">
                  {metrics ? (
                    <>
                      <MetricRow
                        label="Volume"
                        value={`${Number(metrics.volume).toLocaleString()} mm³`}
                        highlight
                      />
                      <MetricRow
                        label="Surface Area"
                        value={`${Number(metrics.surfaceArea).toLocaleString()} mm²`}
                      />
                    </>
                  ) : (
                    <p className="text-[10px] text-gray-700 py-2">Upload a file.</p>
                  )}
                </SectionCard>

                {/* Material Verification Summary */}
                {(() => {
                  const activePart = parts.find(p => p.id === activePartId);
                  const materialEstimate = activePart?.materialEstimate;
                  const pcfg = activePart?.config;

                  if (materialEstimate && pcfg) {
                    return (
                      <SectionCard icon={Eye} title="Material Verification" accent="rgba(16,185,129,0.1)">
                        <div className="space-y-0.5 mt-1">
                          <MetricRow label="Stock" value={materialEstimate.stock_type_name || pcfg.stockType} />
                          <MetricRow label="Material" value={materialEstimate.material_name || '-'} />
                          <MetricRow label="Dims (mm)"
                            value={`${parseFloat(geometry?.boundingBox?.sizeX || 0).toFixed(1)} × ${parseFloat(geometry?.boundingBox?.sizeY || 0).toFixed(1)} × ${parseFloat(geometry?.boundingBox?.sizeZ || 0).toFixed(1)}`} />
                          
                          <div className="mt-3 mb-1 border-t border-white/5 pt-2">
                             <p className="text-[9px] text-emerald-400/70 uppercase tracking-[0.15em] font-bold mb-1 px-1">Envelope</p>
                             {materialEstimate.standard_diameter_mm && <MetricRow label="Std Ø" value={`${materialEstimate.standard_diameter_mm} mm`} highlight />}
                             {materialEstimate.standard_af_mm && <MetricRow label="Hex AF" value={`${materialEstimate.standard_af_mm} mm`} highlight />}
                             {materialEstimate.standard_thickness_mm && <MetricRow label="Thick." value={`${materialEstimate.standard_thickness_mm} × ${materialEstimate.standard_width_mm} mm`} highlight />}
                             {materialEstimate.effective_length_mm > 0 && <MetricRow label="Eff. Len" value={`${materialEstimate.effective_length_mm} mm`} />}
                             <MetricRow label="Vol." value={`${Number(materialEstimate.envelope_volume_mm3).toLocaleString()} mm³`} />
                          </div>
                          
                          <div className="mt-3 border-t border-white/5 pt-2">
                             <p className="text-[9px] text-emerald-400/70 uppercase tracking-[0.15em] font-bold mb-1 px-1">Weight & Cost</p>
                             <MetricRow label="Wt/Part" value={`${materialEstimate.gross_weight_per_part_kg?.toFixed(3)} kg`} highlight />
                             <MetricRow label="Batch Wt" value={`${materialEstimate.total_batch_weight_kg?.toFixed(3)} kg`} />
                             <MetricRow label="Utilization" value={`${materialEstimate.material_utilization_pct}%`} />
                             <MetricRow label="Mat. Cost" value={`₹${Number(materialEstimate.estimated_material_cost_inr).toLocaleString()}`} highlight />
                             {materialEstimate.parts_per_bar > 0 && (
                                <MetricRow label="Parts/Bar" value={`${materialEstimate.parts_per_bar} (${materialEstimate.bars_needed} bar${materialEstimate.bars_needed > 1 ? 's' : ''})`} />
                             )}
                          </div>
                        </div>
                      </SectionCard>
                    );
                  }
                  return null;
                })()}

                {/* B-Rep status */}
                {brepStatus !== 'idle' && (
                <div className="rounded-lg px-3 py-2 text-[10px] font-mono"
                    style={{
                      background: brepStatus === 'ready'
                        ? 'rgba(34,211,238,0.06)'
                        : brepStatus === 'loading'
                          ? 'rgba(96,165,250,0.06)'
                          : brepStatus === 'pdf'
                            ? 'rgba(168,85,247,0.06)'
                            : 'rgba(251,191,36,0.06)',
                      border: `1px solid ${brepStatus === 'ready'
                        ? 'rgba(34,211,238,0.15)'
                        : brepStatus === 'loading'
                          ? 'rgba(96,165,250,0.15)'
                          : brepStatus === 'pdf'
                            ? 'rgba(168,85,247,0.15)'
                            : 'rgba(251,191,36,0.15)'}`,
                      color: brepStatus === 'ready' ? '#67e8f9'
                        : brepStatus === 'loading' ? '#93c5fd'
                          : brepStatus === 'pdf' ? '#c084fc'
                            : '#fcd34d',
                    }}>
                    {brepStatus === 'ready' && '✓ Exact B-Rep analysis complete'}
                    {brepStatus === 'loading' && '⟳ Running CadQuery B-Rep analysis…'}
                    {brepStatus === 'offline' && '◐ Using mesh geometry (backend offline)'}
                    {brepStatus === 'pdf' && '✓ AI-extracted geometry from PDF drawing'}
                  </div>
                )}
                
                {/* ── ACCU AI Chat Interface ── */}
                {brepStatus === 'pdf' && (
                  <SectionCard icon={MessageSquare} title="ACCU AI Copilot" accent="rgba(168,85,247,0.1)">
                    <div className="flex flex-col h-[280px]">
                      <div className="flex-1 overflow-y-auto pr-1 space-y-2 mb-2 custom-scrollbar">
                        {chatMessages.length === 0 ? (
                           <p className="text-[10px] text-gray-500 italic text-center mt-4">Upload a PDF to start chat.</p>
                        ) : (
                          chatMessages.map((msg, i) => (
                            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                              <div className={`text-[10px] rounded-lg px-2.5 py-1.5 max-w-[85%] leading-relaxed ${
                                msg.role === 'user' 
                                  ? 'bg-cyan-600/30 border border-cyan-500/20 text-cyan-100' 
                                  : 'bg-purple-500/10 border border-purple-500/20 text-gray-300'
                              }`}>
                                {msg.role === 'assistant' && (
                                    <span className="font-bold text-purple-400 block mb-0.5 text-[9px] uppercase tracking-wider">ACCU AI</span>
                                )}
                                <div dangerouslySetInnerHTML={{ __html: msg.text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>') }} />
                              </div>
                            </div>
                          ))
                        )}
                        {isAiTyping && (
                            <div className="flex justify-start">
                                <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg px-2.5 py-1.5 flex gap-1 items-center">
                                    <span className="w-1 h-1 bg-purple-400 rounded-full animate-bounce delay-75"></span>
                                    <span className="w-1 h-1 bg-purple-400 rounded-full animate-bounce delay-150"></span>
                                    <span className="w-1 h-1 bg-purple-400 rounded-full animate-bounce delay-300"></span>
                                </div>
                            </div>
                        )}
                      </div>
                      <form onSubmit={handleSendChat} className="relative flex items-center">
                        <input
                          type="text"
                          value={chatInput}
                          onChange={(e) => setChatInput(e.target.value)}
                          placeholder="Ask ACCU AI to modify interpretation..."
                          className="w-full bg-gray-900/80 border border-gray-700/50 rounded-lg pl-3 pr-8 py-1.5 text-[10px] text-gray-200 focus:outline-none focus:border-purple-500/50 font-mono"
                        />
                        <button 
                          type="submit" 
                          disabled={isAiTyping || !chatInput.trim()}
                          className="absolute right-1.5 p-1 text-gray-500 hover:text-cyan-400 disabled:opacity-50"
                        >
                          <Send size={12} />
                        </button>
                      </form>
                    </div>
                  </SectionCard>
                )}
                
              </>
            )}

            {tab === 'quote' && (
              <QuotePanel
                key={activePartId} // Key ensures full remount on part change to read isolated part state
                activePart={parts.find(p => p.id === activePartId)}
                onUpdatePartData={handleUpdatePartData}
                geometry={geometry}
                fileMetrics={metrics}
                captureScreenshot={captureScreenshot}
                parts={parts}
                onRemovePart={handleRemovePart}
              />
            )}
          </div>
        </aside>

        {/* ── Sidebar Resize Handle ── */}
        <div
          className="sidebar-resize-handle"
          onMouseDown={handleResizeStart}
          title="Drag to resize"
        />

        {/* ── 3D Viewer ────────────────────────────────────────────────────── */}
        <section
          ref={viewerRef}
          className="flex-1 relative overflow-hidden"
          style={{ background: '#080c14' }}
        >
          <Viewer
            onMetrics={handleMetrics}
            onAddPart={handleAddPart}
            hasExistingParts={parts.length > 0}
            activePart={parts.find(p => p.id === activePartId)}
          />
        </section>
      </div>
    </div>
  );
}
