import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Cog, Layers, CircleDot, Activity, Plus, ArrowRight,
  Loader2, Home, ChevronRight, PenTool, ShieldCheck,
  Leaf, Wrench, MessageSquarePlus, X, Send, Sparkles,
  Box, Triangle, Circle, Square, Minus, BarChart3
} from 'lucide-react';

// All 11 component families with full metadata
const COMPONENTS = [
  {
    type: 'shaft',
    name: 'SHAFT',
    desc: 'Drive shafts, axles, spindles\nPower, speed, keyways, FOS',
    icon: '⚙',
    color: '#10b981',
  },
  {
    type: 'flange',
    name: 'FLANGE',
    desc: 'Circular disc with bolt-circle\nPCD, bore, thickness, bolt size',
    icon: '🔩',
    color: '#06b6d4',
  },
  {
    type: 'plate_hole_pattern',
    name: 'BASE PLATE',
    desc: 'Flat plates with hole grids\nRectangular or circular patterns',
    icon: '🪟',
    color: '#3b82f6',
  },
  {
    type: 'bracket',
    name: 'BRACKET',
    desc: 'L-shape, U-shape or flat\nMounting plates with holes',
    icon: '📐',
    color: '#f59e0b',
  },
  {
    type: 'spacer',
    name: 'SPACER',
    desc: 'Bushings, standoffs, collars\nOuter dia, bore, length',
    icon: '🧱',
    color: '#8b5cf6',
  },
  {
    type: 'lever',
    name: 'LEVER',
    desc: 'Lever arms & linkages\nPivot bore + load-end bore',
    icon: '↕',
    color: '#ef4444',
  },
  {
    type: 'housing',
    name: 'HOUSING',
    desc: 'Enclosures, casings, shells\nHollow or solid blocks',
    icon: '🏠',
    color: '#64748b',
  },
  {
    type: 'bearing',
    name: 'BEARING',
    desc: 'Ball / roller bearing selection\nLoad, speed, L10 life',
    icon: '⭕',
    color: '#0ea5e9',
  },
  {
    type: 'gearbox',
    name: 'GEARBOX',
    desc: 'Spur / helical transmissions\nPower, ratio, multi-stage',
    icon: '⚙⚙',
    color: '#a3e635',
  },
  {
    type: 'cam',
    name: 'CAM',
    desc: 'Cam disc motion profiles\nRise, dwell, lift, profile type',
    icon: '🌀',
    color: '#fb923c',
  },
  {
    type: 'custom',
    name: 'CUSTOM PART',
    desc: 'Describe any part in natural language\nAI extracts geometry automatically',
    icon: '✦',
    color: '#e2e8f0',
    dashed: true,
  },
];

const STATUS_MAP = {
  collecting_params: { label: 'COLLECTING',   color: '#f59e0b' },
  params_complete:   { label: 'PARAMS OK',     color: '#06b6d4' },
  report_ready:      { label: 'REPORT READY',  color: '#3b82f6' },
  report_approved:   { label: 'APPROVED',      color: '#10b981' },
  cad_ready:         { label: 'CAD DONE',      color: '#06b6d4' },
};

export default function DesignDashboard() {
  const navigate = useNavigate();
  const [stats,    setStats]    = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [creating, setCreating] = useState(null);

  // New-design modal state
  const [modal,        setModal]        = useState(null); // null | component object
  const [promptText,   setPromptText]   = useState('');
  const [submittingPrompt, setSubmittingPrompt] = useState(false);
  const promptRef = useRef(null);

  const currentUser = localStorage.getItem('accu_user') || 'operator@accudesign.in';

  useEffect(() => {
    Promise.all([
      fetch('/api/design/stats').then(r => r.ok ? r.json() : null),
      fetch('/api/design/sessions').then(r => r.ok ? r.json() : []),
    ]).then(([s, sess]) => {
      setStats(s);
      setSessions(Array.isArray(sess) ? sess : []);
    }).catch(() => setSessions([])).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (modal && promptRef.current) promptRef.current.focus();
  }, [modal]);

  // Open modal for a component family
  const openModal = (comp) => {
    setModal(comp);
    setPromptText('');
  };
  const closeModal = () => { setModal(null); setPromptText(''); };

  // Create session with just the component type (guided form)
  const handleGuidedCreate = async (type) => {
    setCreating(type);
    try {
      const res = await fetch('/api/design/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ component_type: type }),
      });
      const session = await res.json();
      navigate(`/design/session/${session.id}`);
    } catch (e) { console.error(e); setCreating(null); }
  };

  // Create session with a natural-language prompt (1 LLM call)
  const handlePromptCreate = async () => {
    if (!promptText.trim() || !modal) return;
    setSubmittingPrompt(true);
    try {
      const res = await fetch('/api/design/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ component_type: modal.type, custom_description: promptText.trim() }),
      });
      const session = await res.json();
      navigate(`/design/session/${session.id}`);
    } catch (e) { console.error(e); setSubmittingPrompt(false); }
  };

  const deleteSession = async (id, e) => {
    e.preventDefault(); e.stopPropagation();
    if (!window.confirm('Delete this design session?')) return;
    await fetch(`/api/design/sessions/${id}`, { method: 'DELETE' });
    setSessions(prev => prev.filter(s => s.id !== id));
  };

  if (loading) return (
    <div className="h-screen flex items-center justify-center bg-[#030712]">
      <div className="flex flex-col items-center gap-3">
        <Loader2 size={32} className="animate-spin text-emerald-400" />
        <span className="text-xs font-mono tracking-widest text-gray-500 uppercase">Loading secure environment...</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen text-gray-100" style={{ background: 'linear-gradient(180deg, #040814 0%, #081022 100%)', fontFamily: "'Inter', sans-serif" }}>

      {/* ── Modal overlay ────────────────────────────────────────────────────── */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)' }}
          onClick={closeModal}>
          <div className="relative w-full max-w-lg rounded-2xl p-6 space-y-5"
            style={{ background: 'linear-gradient(135deg,#0d1525,#0a1020)', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 32px 64px rgba(0,0,0,0.6)' }}
            onClick={e => e.stopPropagation()}>

            <button onClick={closeModal}
              className="absolute top-4 right-4 text-gray-500 hover:text-white transition-colors">
              <X size={16} />
            </button>

            {/* Component header */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl"
                style={{ background: modal.color + '18', border: `1px solid ${modal.color}35` }}>
                {modal.icon}
              </div>
              <div>
                <div className="font-bold text-white text-[13pt]" style={{ fontFamily: 'Outfit,sans-serif' }}>
                  {modal.name}
                </div>
                <div className="text-gray-500 text-[8.5pt] font-mono mt-0.5" style={{ whiteSpace: 'pre-line' }}>
                  {modal.desc}
                </div>
              </div>
            </div>

            <div style={{ border: '1px solid rgba(255,255,255,0.07)' }} />

            {/* Option A: Natural language prompt */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-[9pt] font-mono font-bold text-indigo-300 uppercase tracking-wider">
                <Sparkles size={11} className="text-indigo-400" />
                Option A — Describe in Natural Language
                <span className="ml-auto text-gray-600 normal-case font-normal">1 AI call</span>
              </div>
              <textarea
                ref={promptRef}
                rows={3}
                value={promptText}
                onChange={e => setPromptText(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handlePromptCreate(); }}
                placeholder={`e.g. "I need a 150mm ${modal.type.replace(/_/g,' ')} with 20mm thickness, M10 bolts on 110mm PCD, in EN8 steel, qty 5"`}
                className="w-full px-3 py-2.5 text-[9.5pt] font-mono rounded-xl bg-black/40 border border-white/10 text-white focus:outline-none focus:border-indigo-400 resize-none transition-colors"
              />
              <button onClick={handlePromptCreate} disabled={!promptText.trim() || submittingPrompt}
                className="w-full py-2.5 text-[10pt] font-mono font-bold uppercase tracking-wider rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-40"
                style={{ background: 'rgba(99,102,241,0.8)', color: 'white' }}>
                {submittingPrompt
                  ? <><Loader2 size={13} className="animate-spin" /> Extracting specs...</>
                  : <><Sparkles size={13} /> Extract & Start Session</>}
              </button>
              <p className="text-[8pt] font-mono text-gray-600 text-center">Ctrl+Enter to submit · AI extracts all dimensions automatically</p>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex-1 h-px bg-white/10" />
              <span className="text-[8.5pt] font-mono text-gray-600">OR</span>
              <div className="flex-1 h-px bg-white/10" />
            </div>

            {/* Option B: Guided form */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-[9pt] font-mono font-bold text-emerald-300 uppercase tracking-wider">
                <BarChart3 size={11} className="text-emerald-400" />
                Option B — Guided Parameter Form
                <span className="ml-auto text-gray-600 normal-case font-normal">0 AI calls</span>
              </div>
              <button onClick={() => handleGuidedCreate(modal.type)} disabled={creating === modal.type}
                className="w-full py-2.5 text-[10pt] font-mono font-bold uppercase tracking-wider rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.4)', color: '#34d399' }}>
                {creating === modal.type
                  ? <><Loader2 size={13} className="animate-spin" /> Creating...</>
                  : <><ArrowRight size={13} /> Fill Guided Form</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Top Nav ─────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 flex items-center justify-between px-8 h-14"
        style={{ background: 'rgba(4,8,20,0.9)', backdropFilter: 'blur(12px)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2 text-gray-500 hover:text-gray-300 transition-colors">
            <Home size={13} />
            <span className="text-[10px] font-mono tracking-wider uppercase">Workspace</span>
          </Link>
          <ChevronRight size={12} className="text-gray-700" />
          <div className="flex items-center gap-2">
            <PenTool size={14} className="text-emerald-400" />
            <span className="text-sm font-bold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Design Cockpit
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-mono text-emerald-400">
            <ShieldCheck size={12} /> SECURE AUDITED
          </div>
          <Link to="/quote"
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[10px] font-mono tracking-wider uppercase text-gray-400 hover:text-white hover:bg-white/5 transition-all border border-transparent hover:border-white/10">
            <Cog size={12} /> Quoting Engine
          </Link>
        </div>
      </header>

      <div className="px-8 py-10 max-w-7xl mx-auto space-y-10">

        {/* ── Hero ─────────────────────────────────────────────────────────── */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 p-6 rounded-xl border border-gray-800 bg-gray-950/20 backdrop-blur-sm">
          <div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight mb-1" style={{ fontFamily: 'Outfit, sans-serif' }}>
              ENGINEERING DESIGN COCKPIT
            </h1>
            <p className="text-gray-400 text-xs font-mono max-w-xl">
              Text-to-CAD pipeline powered by deterministic OpenCASCADE builders.
              1 AI call for spec extraction · 0 AI calls for geometry · Verified STEP output.
            </p>
          </div>
          <div className="flex flex-col items-end gap-1 font-mono text-[10px] text-gray-500">
            <span className="flex items-center gap-1.5 text-emerald-400"><ShieldCheck size={11} /> Deterministic CAD Engine Active</span>
            <span className="flex items-center gap-1.5"><Leaf size={11} className="text-emerald-500/80" /> AP242 STEP · ISO 2768-m · ASME B106.1M</span>
          </div>
        </div>

        {/* ── Component Catalogue ──────────────────────────────────────────── */}
        <section>
          <h2 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Select Component Family to Design
            <span className="ml-auto text-gray-700 normal-case">Click to start · Natural language or guided form</span>
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
            {COMPONENTS.map(comp => (
              <button
                key={comp.type}
                onClick={() => openModal(comp)}
                disabled={creating === comp.type}
                className="group relative rounded-xl p-4 text-left transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(0,0,0,0.5)] disabled:opacity-50"
                style={{
                  background: 'linear-gradient(135deg,rgba(255,255,255,0.03),rgba(255,255,255,0.005))',
                  border: comp.dashed ? `1px dashed ${comp.color}40` : '1px solid rgba(255,255,255,0.07)',
                }}
              >
                {/* Hover glow */}
                <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ background: `linear-gradient(135deg,${comp.color}10,transparent 60%)` }} />
                <div className="relative z-10 space-y-2">
                  <div className="text-2xl leading-none">{comp.icon}</div>
                  <div className="font-extrabold text-white text-[10pt] tracking-wide" style={{ fontFamily: 'Outfit,sans-serif' }}>
                    {comp.name}
                  </div>
                  <div className="text-[8pt] text-gray-500 leading-snug" style={{ whiteSpace: 'pre-line' }}>
                    {comp.desc}
                  </div>
                  <div className="flex items-center justify-between pt-1 text-[9px] font-mono">
                    <span style={{ color: comp.color }} className="font-bold opacity-80">
                      {creating === comp.type ? 'CREATING...' : 'START →'}
                    </span>
                    {creating === comp.type
                      ? <Loader2 size={10} className="animate-spin" style={{ color: comp.color }} />
                      : <Plus size={10} className="text-gray-700 group-hover:text-white transition-colors" />}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </section>

        {/* ── Stats ────────────────────────────────────────────────────────── */}
        {stats && (
          <section>
            <h2 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Design Telemetry
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              {[
                { label: 'Total Sessions',    value: stats.totalSessions,    color: 'text-white' },
                { label: 'Approved Reports',  value: stats.approvedReports,  color: 'text-emerald-400' },
                { label: 'Completed Designs', value: stats.completedDesigns, color: 'text-cyan-400' },
                { label: 'Active Sessions',   value: sessions.filter(s => s.status === 'collecting_params').length, color: 'text-indigo-400' },
                { label: 'KB Formulas',       value: stats.knowledgeBase?.total_entries || '—', color: 'text-yellow-400' },
              ].map((s, i) => (
                <div key={i} className="p-5 rounded-xl border border-white/[0.04]"
                  style={{ background: 'linear-gradient(135deg,rgba(255,255,255,0.02),rgba(255,255,255,0.005))' }}>
                  <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-3">{s.label}</div>
                  <div className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Recent Sessions ──────────────────────────────────────────────── */}
        <section>
          <h2 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Recent Design Sessions
          </h2>
          <div className="rounded-xl overflow-hidden border border-white/[0.04]"
            style={{ background: 'linear-gradient(135deg,rgba(255,255,255,0.02),rgba(255,255,255,0.005))', maxHeight: 450, overflowY: 'auto' }}>
            {sessions.length === 0 ? (
              <div className="p-10 text-center text-gray-600 font-mono text-xs">
                No design sessions yet — select a component above to begin.
              </div>
            ) : sessions.map(s => {
              const st   = STATUS_MAP[s.status] || { label: s.status, color: '#666' };
              const meta = { shaft:'⚙', flange:'🔩', plate_hole_pattern:'🪟', bracket:'📐', spacer:'🧱', lever:'↕', housing:'🏠', bearing:'⭕', gearbox:'⚙⚙', cam:'🌀', custom:'✦' };
              return (
                <Link key={s.id} to={`/design/session/${s.id}`}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-white/[0.015] transition-colors border-b border-white/[0.04] last:border-0 group">
                  <div className="flex items-center gap-3.5">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-gray-900/60 border border-gray-800/80">
                      {meta[s.component_type] || '•'}
                    </div>
                    <div>
                      <div className="text-[10pt] font-bold text-white uppercase tracking-wide">
                        {s.component_type.replace(/_/g,' ')}
                      </div>
                      <div className="text-[8.5pt] text-gray-600 font-mono mt-0.5">
                        #{s.id} · {new Date(s.created_at * 1000).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 text-[8.5pt] font-mono font-bold tracking-wider rounded"
                      style={{ color: st.color, background: st.color + '12', border: `1px solid ${st.color}30` }}>
                      {st.label}
                    </span>
                    <button onClick={(e) => deleteSession(s.id, e)}
                      className="opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity text-red-500 hover:text-red-400 p-1 rounded">
                      <X size={11} />
                    </button>
                    <ArrowRight size={12} className="text-gray-700 group-hover:text-gray-400 transition-colors" />
                  </div>
                </Link>
              );
            })}
          </div>
        </section>

      </div>
    </div>
  );
}
