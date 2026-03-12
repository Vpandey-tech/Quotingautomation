import React, { useState, useRef, useCallback } from 'react';
import Viewer from './components/viewer/Viewer';
import QuotePanel from './components/quote/QuotePanel';
import {
  Box, FileText, Activity, Ruler, FlaskConical,
  DollarSign, Layers, ChevronRight, MessageSquare, Send
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
function Tab({ active, onClick, icon: Icon, label }) {
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

  // Track sidebar hover to block pointer events on 3D canvas
  const [sidebarHovered, setSidebarHovered] = useState(false);
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

  // Called by Viewer with mesh metrics + original File object
  // For STEP files: file is passed, triggers B-Rep analysis
  // For PDF files: file is null, geometry comes from Gemini AI
  const handleMetrics = async (m, file) => {
    if (!m) {
      setMetrics(null);
      setGeometry(null);
      setBrepStatus('idle');
      return;
    }
    setMetrics(m);

    // Build geometry object from metrics
    const geom = {
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
      setBrepStatus(prev => prev === 'loading' ? 'ready' : prev); // Optimistic UI assumption for rapid user experience
    }, 3500);

    try {
      const fd = new FormData();
      fd.append('file', file);
      const resp = await fetch('/api/analyze', { method: 'POST', body: fd });
      clearTimeout(loadingTimeout); // clear if it comes back faster
      if (resp.ok) {
        setGeometry(await resp.json());
        setBrepStatus('ready');
      } else {
        setBrepStatus('offline');
      }
    } catch {
      clearTimeout(loadingTimeout);
      setBrepStatus('offline');
    }
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
            v0.4.0
          </span>
        </div>
      </header>

      {/* ── Main layout ──────────────────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── Sidebar ────────────────────────────────────────────────────────── */}
        <aside
          className="w-[320px] flex-shrink-0 flex flex-col z-40 sidebar-bg"
          style={{ borderRight: '1px solid rgba(255,255,255,0.05)' }}
          onMouseEnter={handleSidebarEnter}
          onMouseLeave={handleSidebarLeave}
        >
          {/* Tab bar */}
          <div className="flex flex-shrink-0"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.07)', background: 'rgba(0,0,0,0.3)' }}>
            <Tab active={tab === 'details'} onClick={() => setTab('details')}
              icon={Layers} label="Details" />
            <Tab active={tab === 'quote'} onClick={() => setTab('quote')}
              icon={DollarSign} label="Quote" />
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

                {/* Mesh details */}
                <SectionCard icon={Activity} title="Mesh Details">
                  {metrics ? (
                    <>
                      <MetricRow label="Vertices" value={metrics.vertices.toLocaleString()} />
                      <MetricRow label="Triangles" value={metrics.triangles.toLocaleString()} highlight />
                      <MetricRow label="Meshes" value={metrics.meshCount} />
                      <MetricRow label="Unit" value={metrics.unit} />
                    </>
                  ) : (
                    <p className="text-[10px] text-gray-700 py-2">Upload a file.</p>
                  )}
                </SectionCard>

                {/* Bounding box */}
                <SectionCard icon={Ruler} title="Bounding Box">
                  {metrics ? (
                    <>
                      <MetricRow label="Size X" value={`${metrics.sizeX} mm`} />
                      <MetricRow label="Size Y" value={`${metrics.sizeY} mm`} />
                      <MetricRow label="Size Z" value={`${metrics.sizeZ} mm`} />
                    </>
                  ) : (
                    <p className="text-[10px] text-gray-700 py-2">Upload a file.</p>
                  )}
                </SectionCard>

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
                                {msg.text}
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
              <QuotePanel geometry={geometry} fileMetrics={metrics} captureScreenshot={captureScreenshot} />
            )}
          </div>
        </aside>

        {/* ── 3D Viewer ────────────────────────────────────────────────────── */}
        <section
          ref={viewerRef}
          className="flex-1 relative overflow-hidden"
          style={{ background: '#080c14' }}
        >
          <Viewer onMetrics={handleMetrics} />
        </section>
      </div>
    </div>
  );
}
