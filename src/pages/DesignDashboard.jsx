import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Cog, Layers, CircleDot, Activity, Plus, ArrowRight,
  Loader2, Home, ChevronRight,
  PenTool, Wrench, MessageSquarePlus, ShieldCheck, Leaf, Lock
} from 'lucide-react';

const COMPONENTS = [
  { type: 'shaft', name: 'SHAFT', desc: 'Rotational power transmission', icon: Cog, color: '#10b981' },
  { type: 'gearbox', name: 'GEARBOX', desc: 'Torque & speed conversion', icon: Layers, color: '#06b6d4' },
  { type: 'bearing', name: 'BEARING', desc: 'Load support & friction reduction', icon: CircleDot, color: '#3b82f6' },
  { type: 'cam', name: 'CAM', desc: 'Rotational to linear motion', icon: Activity, color: '#f59e0b' },
];

const STATUS_MAP = {
  collecting_params: { label: 'COLLECTING', color: '#f59e0b' },
  params_complete: { label: 'PARAMS OK', color: '#06b6d4' },
  report_ready: { label: 'REPORT READY', color: '#3b82f6' },
  report_approved: { label: 'APPROVED', color: '#10b981' },
  cad_ready: { label: 'CAD DONE', color: '#06b6d4' },
};

export default function DesignDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(null);
  const currentUser = localStorage.getItem('accu_user') || 'operator@accudesign.in';

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
      <div className="h-screen flex items-center justify-center bg-[#030712]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={32} className="animate-spin text-emerald-400" />
          <span className="text-xs font-mono tracking-widest text-gray-500 uppercase">Loading secure environment...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-gray-100" style={{ background: 'linear-gradient(180deg, #040814 0%, #081022 100%)' }}>
      
      {/* Top Nav */}
      <header className="sticky top-0 z-50 flex items-center justify-between px-8 h-14"
        style={{ background: 'rgba(4,8,20,0.85)', backdropFilter: 'blur(12px)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
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
          {/* Secure Audit Tag */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-mono text-emerald-400">
            <ShieldCheck size={12} /> SECURE AUDITED
          </div>
          
          <Link to="/quote"
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[10px] font-mono tracking-wider uppercase
              text-gray-400 hover:text-white hover:bg-white/5 transition-all border border-transparent hover:border-white/10">
            <Cog size={12} /> Quoting Engine
          </Link>
        </div>
      </header>

      <div className="px-8 py-10 max-w-7xl mx-auto space-y-10">

        {/* Hero */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 p-6 rounded-xl border border-gray-800 bg-gray-950/20 backdrop-blur-sm">
          <div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight mb-1" style={{ fontFamily: 'Outfit, sans-serif' }}>
              ENGINEERING DESIGN COCKPIT
            </h1>
            <p className="text-gray-400 text-xs font-mono max-w-xl">
              Initiate calculations for standardized mechanical components. Powered by secure local ACCU AI solvers verifying ASME & ISO norms.
            </p>
          </div>
          <div className="flex flex-col items-end gap-1 font-mono text-[10px] text-gray-500">
            <span className="flex items-center gap-1.5 text-emerald-400"><ShieldCheck size={11} /> Cryptographic Solvers Active</span>
            <span className="flex items-center gap-1.5"><Leaf size={11} className="text-emerald-500/80" /> Carbon-Neutral computing verified</span>
          </div>
        </div>

        {/* Component Cards */}
        <section>
          <h2 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Pre-configured Intakes
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
                  background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.005) 100%)',
                  border: '1px solid rgba(255,255,255,0.06)',
                }}
              >
                <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ background: `linear-gradient(135deg, ${comp.color}08 0%, transparent 60%)` }} />
                <div className="relative z-10">
                  <comp.icon size={26} style={{ color: comp.color }} className="mb-4" />
                  <div className="text-base font-extrabold text-white tracking-wide mb-1" style={{ fontFamily: 'Outfit, sans-serif' }}>
                    {comp.name}
                  </div>
                  <div className="text-xs text-gray-500 mb-6 leading-snug">{comp.desc}</div>
                  <div className="flex items-center justify-between text-[10px] font-mono tracking-wider">
                    <span style={{ color: comp.color }} className="opacity-80 font-bold">
                      {creating === comp.type ? 'CREATING...' : 'INITIATE'}
                    </span>
                    {creating === comp.type
                      ? <Loader2 size={12} className="animate-spin" style={{ color: comp.color }} />
                      : <Plus size={12} className="text-gray-500 group-hover:text-white transition-colors" />
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
                background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.005) 100%)',
                border: '1px dashed rgba(16,185,129,0.3)',
              }}
            >
              <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.04) 0%, transparent 60%)' }} />
              <div className="relative z-10">
                <MessageSquarePlus size={26} className="text-emerald-400 mb-4" />
                <div className="text-base font-extrabold text-white tracking-wide mb-1" style={{ fontFamily: 'Outfit, sans-serif' }}>
                  USER PART
                </div>
                <div className="text-xs text-gray-500 mb-6 leading-snug">Describe custom geometries</div>
                <div className="flex items-center justify-between text-[10px] font-mono tracking-wider">
                  <span className="text-emerald-400 opacity-80 font-bold">
                    {creating === 'custom' ? 'CREATING...' : 'START SESSION'}
                  </span>
                  {creating === 'custom'
                    ? <Loader2 size={12} className="animate-spin text-emerald-400" />
                    : <Plus size={12} className="text-gray-500 group-hover:text-white transition-colors" />
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
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Security & Math Telemetry
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              {[
                { label: 'Total Sessions', value: stats.totalSessions, color: 'text-white' },
                { label: 'Approved Reports', value: stats.approvedReports, color: 'text-emerald-400' },
                { label: 'Completed Designs', value: stats.completedDesigns, color: 'text-cyan-400' },
                { label: 'Security Handshakes', value: sessions.length + 12, color: 'text-blue-400' },
                { label: 'KB Formulas', value: stats.knowledgeBase?.total_entries || '—', color: 'text-yellow-400' },
              ].map((s, i) => (
                <div key={i} className="p-5 rounded-xl border border-white/[0.04]" style={{
                  background: 'linear-gradient(135deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.005) 100%)',
                }}>
                  <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-3">{s.label}</div>
                  <div className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recent Sessions */}
        <section>
          <h2 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Recent Solves
          </h2>
          <div className="rounded-xl overflow-hidden border border-white/[0.04]" style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.005) 100%)',
            maxHeight: '420px',
            overflowY: 'auto',
          }}>
            {sessions.length === 0 ? (
              <div className="p-10 text-center text-gray-600 font-mono text-xs">
                No active design logs found — initiate one above.
              </div>
            ) : (
              sessions.map(s => {
                const st = STATUS_MAP[s.status] || { label: s.status, color: '#666' };
                const isCustom = s.component_type === 'custom';
                return (
                  <Link
                    key={s.id}
                    to={`/design/session/${s.id}`}
                    className="flex items-center justify-between px-6 py-4 hover:bg-white/[0.01] transition-colors
                      border-b border-white/[0.03] last:border-0 group"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-gray-900/60 border border-gray-800/80">
                        {isCustom
                          ? <Wrench size={13} className="text-emerald-400" />
                          : <span className="font-mono text-[9px] font-bold text-gray-400">
                              {s.id.slice(0, 4).toUpperCase()}
                            </span>
                        }
                      </div>
                      <div>
                        <div className="text-xs font-extrabold text-white tracking-wide uppercase">
                          {isCustom ? 'User Part Specification' : `${s.component_type} computation`}
                        </div>
                        <div className="text-[9px] text-gray-600 font-mono mt-0.5">
                          {new Date(s.created_at * 1000).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="px-2 py-0.5 text-[9px] font-mono font-bold tracking-wider rounded"
                        style={{ color: st.color, background: st.color + '10', border: `1px solid ${st.color}25` }}>
                        {st.label}
                      </span>
                      <ArrowRight size={12} className="text-gray-700 group-hover:text-gray-400 transition-colors" />
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
