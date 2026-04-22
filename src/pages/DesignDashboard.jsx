import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Cog, Layers, CircleDot, Activity, Plus, ArrowRight,
  BarChart3, CheckCircle2, Box, Loader2, Home, ChevronRight,
  PenTool, Sparkles, Wrench, MessageSquarePlus
} from 'lucide-react';

const COMPONENTS = [
  { type: 'shaft', name: 'SHAFT', desc: 'Rotational power transmission', icon: Cog, color: '#22d3ee' },
  { type: 'gearbox', name: 'GEARBOX', desc: 'Torque & speed conversion', icon: Layers, color: '#818cf8' },
  { type: 'bearing', name: 'BEARING', desc: 'Load support & friction reduction', icon: CircleDot, color: '#34d399' },
  { type: 'cam', name: 'CAM', desc: 'Rotational to linear motion', icon: Activity, color: '#f59e0b' },
];

const STATUS_MAP = {
  collecting_params: { label: 'COLLECTING', color: '#f59e0b' },
  params_complete: { label: 'PARAMS OK', color: '#22d3ee' },
  report_ready: { label: 'REPORT READY', color: '#818cf8' },
  report_approved: { label: 'APPROVED', color: '#34d399' },
  cad_ready: { label: 'CAD DONE', color: '#22d3ee' },
};

export default function DesignDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch('/api/design/stats').then(r => r.json()),
      fetch('/api/design/sessions').then(r => r.json()),
    ]).then(([s, sess]) => {
      setStats(s);
      setSessions(sess);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  const handleCreate = async (type) => {
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

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ background: '#060a13' }}>
        <Loader2 size={32} className="animate-spin text-cyan-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(180deg, #060a13 0%, #0a0f1a 100%)' }}>

      {/* Top Nav */}
      <header className="sticky top-0 z-50 flex items-center justify-between px-8 h-14"
        style={{ background: 'rgba(6,10,19,0.85)', backdropFilter: 'blur(12px)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2 text-gray-500 hover:text-gray-300 transition-colors">
            <Home size={14} />
            <span className="text-[10px] font-mono tracking-wider uppercase">Home</span>
          </Link>
          <ChevronRight size={12} className="text-gray-700" />
          <div className="flex items-center gap-2">
            <PenTool size={14} className="text-cyan-400" />
            <span className="text-sm font-bold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Engineering Design
            </span>
          </div>
        </div>
        <Link to="/quote"
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[10px] font-mono tracking-wider uppercase
            text-gray-500 hover:text-white hover:bg-white/5 transition-all border border-transparent hover:border-white/10">
          <Cog size={12} /> Quoting Engine
        </Link>
      </header>

      <div className="px-8 py-10 max-w-7xl mx-auto space-y-12">

        {/* Hero */}
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight mb-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Design Cockpit
          </h1>
          <p className="text-gray-500 text-sm font-mono">
            Select a component to start a new engineering design session, or describe a custom part.
          </p>
        </div>

        {/* Component Cards */}
        <section>
          <h2 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" /> Component Intake
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {COMPONENTS.map(comp => (
              <button
                key={comp.type}
                onClick={() => handleCreate(comp.type)}
                disabled={creating === comp.type}
                className="group relative rounded-xl p-6 text-left transition-all duration-300
                  hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(0,0,0,0.5)] disabled:opacity-50"
                style={{
                  background: 'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ background: `linear-gradient(135deg, ${comp.color}08 0%, transparent 60%)` }} />
                <div className="relative z-10">
                  <comp.icon size={28} style={{ color: comp.color }} className="mb-4" />
                  <div className="text-lg font-bold text-white tracking-widest mb-1" style={{ fontFamily: 'Outfit, sans-serif' }}>
                    {comp.name}
                  </div>
                  <div className="text-xs text-gray-500 mb-6">{comp.desc}</div>
                  <div className="flex items-center justify-between text-xs font-mono tracking-wider">
                    <span style={{ color: comp.color }} className="opacity-70">
                      {creating === comp.type ? 'CREATING...' : 'INITIATE'}
                    </span>
                    {creating === comp.type
                      ? <Loader2 size={14} className="animate-spin" style={{ color: comp.color }} />
                      : <Plus size={14} className="text-gray-600 group-hover:text-white transition-colors" />
                    }
                  </div>
                </div>
              </button>
            ))}

            {/* Custom Part Card */}
            <button
              onClick={() => handleCreate('custom')}
              disabled={creating === 'custom'}
              className="group relative rounded-xl p-6 text-left transition-all duration-300
                hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(0,0,0,0.5)] disabled:opacity-50"
              style={{
                background: 'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)',
                border: '1px dashed rgba(167,139,250,0.3)',
              }}
            >
              <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ background: 'linear-gradient(135deg, rgba(167,139,250,0.06) 0%, transparent 60%)' }} />
              <div className="relative z-10">
                <MessageSquarePlus size={28} className="text-violet-400 mb-4" />
                <div className="text-lg font-bold text-white tracking-widest mb-1" style={{ fontFamily: 'Outfit, sans-serif' }}>
                  USER PART
                </div>
                <div className="text-xs text-gray-500 mb-6">Describe any custom part</div>
                <div className="flex items-center justify-between text-xs font-mono tracking-wider">
                  <span className="text-violet-400 opacity-70">
                    {creating === 'custom' ? 'CREATING...' : 'START SESSION'}
                  </span>
                  {creating === 'custom'
                    ? <Loader2 size={14} className="animate-spin text-violet-400" />
                    : <Plus size={14} className="text-gray-600 group-hover:text-white transition-colors" />
                  }
                </div>
              </div>
            </button>
          </div>
        </section>

        {/* Telemetry */}
        {stats && (
          <section>
            <h2 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" /> System Telemetry
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              {[
                { label: 'Total Sessions', value: stats.totalSessions, color: 'text-white' },
                { label: 'Approved Reports', value: stats.approvedReports, color: 'text-cyan-400' },
                { label: 'Completed Designs', value: stats.completedDesigns, color: 'text-emerald-400' },
                { label: 'Active Types', value: Object.values(stats.byComponentType || {}).filter(v => v > 0).length, color: 'text-indigo-400' },
                { label: 'KB Formulas', value: stats.knowledgeBase?.total_entries || '—', color: 'text-violet-400' },
              ].map((s, i) => (
                <div key={i} className="p-5 rounded-xl" style={{
                  background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)',
                  border: '1px solid rgba(255,255,255,0.05)',
                }}>
                  <div className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-3">{s.label}</div>
                  <div className={`text-3xl font-bold font-mono ${s.color}`}>{s.value}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recent Sessions — scrollable */}
        <section>
          <h2 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" /> Recent Sessions
          </h2>
          <div className="rounded-xl overflow-hidden" style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)',
            border: '1px solid rgba(255,255,255,0.05)',
            maxHeight: '420px',
            overflowY: 'auto',
          }}>
            {sessions.length === 0 ? (
              <div className="p-10 text-center text-gray-600 font-mono text-sm">
                No sessions yet — create one above to get started.
              </div>
            ) : (
              sessions.map(s => {
                const st = STATUS_MAP[s.status] || { label: s.status, color: '#666' };
                const comp = COMPONENTS.find(c => c.type === s.component_type);
                const isCustom = s.component_type === 'custom';
                return (
                  <Link
                    key={s.id}
                    to={`/design/session/${s.id}`}
                    className="flex items-center justify-between px-6 py-4 hover:bg-white/[0.02] transition-colors
                      border-b border-white/[0.03] last:border-0 group"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-9 h-9 rounded-lg flex items-center justify-center"
                        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
                        {isCustom
                          ? <Wrench size={14} className="text-violet-400" />
                          : <span className="font-mono text-[10px] font-bold text-gray-400">
                              {s.id.slice(0, 4).toUpperCase()}
                            </span>
                        }
                      </div>
                      <div>
                        <div className="text-sm font-bold text-white tracking-wide uppercase" style={{ fontFamily: 'Outfit, sans-serif' }}>
                          {isCustom ? 'User Part' : s.component_type}
                        </div>
                        <div className="text-[10px] text-gray-600 font-mono">
                          {new Date(s.created_at * 1000).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="px-2 py-0.5 text-[9px] font-mono font-bold tracking-wider rounded"
                        style={{ color: st.color, background: st.color + '15', border: `1px solid ${st.color}30` }}>
                        {st.label}
                      </span>
                      <ArrowRight size={14} className="text-gray-700 group-hover:text-gray-400 transition-colors" />
                    </div>
                  </Link>
                );
              })
            )}
          </div>
        </section>
      </div>

    </div>
  );
}
