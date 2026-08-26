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

  // Direct 1-click start: creates session and opens chat interface directly
  const handleStartSession = async (type) => {
    setCreating(type);
    try {
      const res = await fetch('/api/design/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ component_type: type }),
      });
      const session = await res.json();
      navigate(`/design/session/${session.id}`);
    } catch (e) {
      console.error(e);
      setCreating(null);
    }
  };

  const deleteSession = async (id, e) => {
    e.preventDefault(); e.stopPropagation();
    if (!window.confirm('Delete this design session?')) return;
    await fetch(`/api/design/sessions/${id}`, { method: 'DELETE' });
    setSessions(prev => prev.filter(s => s.id !== id));
  };

  if (loading) return (
    <div className="h-screen flex items-center justify-center bg-[#f8fafc]">
      <div className="flex flex-col items-center gap-3">
        <Loader2 size={32} className="animate-spin text-accu-600" />
        <span className="text-xs font-mono tracking-widest text-slate-500 uppercase font-semibold">Loading design cockpit...</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 font-sans">

      {/* ── Top Nav ─────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 flex items-center justify-between px-8 h-14 bg-white/90 backdrop-blur-md border-b border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2 text-slate-500 hover:text-slate-900 transition-colors">
            <Home size={13} />
            <span className="text-[10px] font-mono tracking-wider uppercase font-bold">Workspace</span>
          </Link>
          <ChevronRight size={12} className="text-slate-400" />
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-accu-50 border border-accu-200 flex items-center justify-center text-accu-600">
              <PenTool size={13} />
            </div>
            <span className="text-sm font-bold text-slate-900 tracking-tight font-heading">
              Design Cockpit
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[10px] font-mono text-emerald-700 font-bold">
            <ShieldCheck size={12} /> SECURE AUDITED
          </div>
          <Link to="/quote"
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-[10px] font-mono font-bold tracking-wider uppercase text-slate-700 hover:text-accu-700 hover:bg-accu-50 transition-all border border-slate-200 bg-white shadow-sm">
            <Cog size={12} className="text-accu-600" /> Quoting Engine
          </Link>
        </div>
      </header>

      <div className="px-8 py-10 max-w-7xl mx-auto space-y-8">

        {/* ── Hero ─────────────────────────────────────────────────────────── */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 p-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight mb-1 font-heading">
              ENGINEERING DESIGN COCKPIT
            </h1>
            <p className="text-slate-500 text-xs font-mono max-w-xl">
              Text-to-CAD pipeline powered by deterministic OpenCASCADE builders.
              1 AI call for spec extraction · 0 AI calls for geometry · Verified STEP output.
            </p>
          </div>
          <div className="flex flex-col items-start md:items-end gap-1 font-mono text-[10px] text-slate-500 font-semibold">
            <span className="flex items-center gap-1.5 text-emerald-600"><ShieldCheck size={11} /> Deterministic CAD Engine Active</span>
            <span className="flex items-center gap-1.5"><Leaf size={11} className="text-emerald-600" /> AP242 STEP · ISO 2768-m · ASME B106.1M</span>
          </div>
        </div>

        {/* ── Component Catalogue ──────────────────────────────────────────── */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-mono text-slate-600 uppercase tracking-widest font-bold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-accu-500" />
              Select Component Family to Design
            </h2>
            <span className="text-[11px] font-mono text-slate-400">Direct 1-Click Entry · Conversational Spec &amp; CAD</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
            {COMPONENTS.map(comp => (
              <button
                key={comp.type}
                onClick={() => handleStartSession(comp.type)}
                disabled={creating === comp.type}
                className="group relative rounded-2xl p-4 text-left transition-all duration-300 hover:-translate-y-1 hover:shadow-lg disabled:opacity-50 bg-white border border-slate-200 hover:border-accu-400 shadow-sm"
              >
                <div className="relative z-10 space-y-2">
                  <div className="text-2xl leading-none">{comp.icon}</div>
                  <div className="font-extrabold text-slate-900 text-[10pt] tracking-wide font-heading">
                    {comp.name}
                  </div>
                  <div className="text-[8pt] text-slate-500 leading-snug font-sans" style={{ whiteSpace: 'pre-line' }}>
                    {comp.desc}
                  </div>
                  <div className="flex items-center justify-between pt-1 text-[9px] font-mono font-bold">
                    <span style={{ color: comp.color }}>
                      {creating === comp.type ? 'STARTING...' : 'OPEN CHAT →'}
                    </span>
                    {creating === comp.type
                      ? <Loader2 size={10} className="animate-spin" style={{ color: comp.color }} />
                      : <Plus size={10} className="text-slate-400 group-hover:text-slate-800 transition-colors" />}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </section>

        {/* ── Stats ────────────────────────────────────────────────────────── */}
        {stats && (
          <section>
            <h2 className="text-xs font-mono text-slate-600 uppercase tracking-widest mb-4 flex items-center gap-2 font-bold">
              <span className="w-2 h-2 rounded-full bg-accu-500" /> Design Telemetry
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              {[
                { label: 'Total Sessions',    value: stats.totalSessions,    color: 'text-slate-900' },
                { label: 'Approved Reports',  value: stats.approvedReports,  color: 'text-emerald-600' },
                { label: 'Completed Designs', value: stats.completedDesigns, color: 'text-accu-600' },
                { label: 'Active Sessions',   value: sessions.filter(s => s.status === 'collecting_params').length, color: 'text-accuorange-600' },
                { label: 'KB Formulas',       value: stats.knowledgeBase?.total_entries || '—', color: 'text-indigo-600' },
              ].map((s, i) => (
                <div key={i} className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm">
                  <div className="text-[9px] font-mono text-slate-500 uppercase tracking-widest mb-2 font-bold">{s.label}</div>
                  <div className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Recent Sessions ──────────────────────────────────────────────── */}
        <section>
          <h2 className="text-xs font-mono text-slate-600 uppercase tracking-widest mb-4 flex items-center gap-2 font-bold">
            <span className="w-2 h-2 rounded-full bg-accu-500" /> Recent Design Sessions
          </h2>
          <div className="rounded-2xl overflow-hidden border border-slate-200 bg-white shadow-sm"
            style={{ maxHeight: 450, overflowY: 'auto' }}>
            {sessions.length === 0 ? (
              <div className="p-10 text-center text-slate-400 font-mono text-xs">
                No design sessions yet — select a component above to begin.
              </div>
            ) : sessions.map(s => {
              const st   = STATUS_MAP[s.status] || { label: s.status, color: '#666' };
              const meta = { shaft:'⚙', flange:'🔩', plate_hole_pattern:'🪟', bracket:'📐', spacer:'🧱', lever:'↕', housing:'🏠', bearing:'⭕', gearbox:'⚙⚙', cam:'🌀', custom:'✦' };
              return (
                <Link key={s.id} to={`/design/session/${s.id}`}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-0 group">
                  <div className="flex items-center gap-3.5">
                    <div className="w-9 h-9 rounded-xl flex items-center justify-center text-sm bg-slate-50 border border-slate-200">
                      {meta[s.component_type] || '•'}
                    </div>
                    <div>
                      <div className="text-[10pt] font-bold text-slate-900 uppercase tracking-wide">
                        {s.component_type.replace(/_/g,' ')}
                      </div>
                      <div className="text-[8.5pt] text-slate-400 font-mono mt-0.5">
                        #{s.id} · {new Date(s.created_at * 1000).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="px-2.5 py-0.5 text-[8.5pt] font-mono font-bold tracking-wider rounded-md"
                      style={{ color: st.color, background: st.color + '15', border: `1px solid ${st.color}30` }}>
                      {st.label}
                    </span>
                    <button onClick={(e) => deleteSession(s.id, e)}
                      className="opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity text-red-500 hover:text-red-700 p-1 rounded">
                      <X size={13} />
                    </button>
                    <ArrowRight size={13} className="text-slate-400 group-hover:text-accu-600 transition-colors" />
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
