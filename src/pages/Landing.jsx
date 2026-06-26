import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Cog, PenTool, ArrowRight, Shield, Zap, ShieldCheck, Leaf, LogOut, Lock, UserCheck
} from 'lucide-react';

export default function Landing() {
  const navigate = useNavigate();
  const currentUser = localStorage.getItem('accu_user') || 'operator@accudesign.in';
  
  const handleLogout = () => {
    localStorage.removeItem('accu_auth');
    localStorage.removeItem('accu_user');
    navigate('/login');
  };

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center relative overflow-hidden"
      style={{ background: 'linear-gradient(135deg, #040812 0%, #081022 40%, #050a16 100%)' }}>

      {/* Grid Overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f293706_1px,transparent_1px),linear-gradient(to_bottom,#1f293706_1px,transparent_1px)] bg-[size:3rem_3rem] pointer-events-none" />

      {/* Ambient glow - green/cyan for sustainability & security */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full opacity-[0.06] pointer-events-none"
        style={{ background: 'radial-gradient(circle, #10b981 0%, transparent 70%)' }} />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full opacity-[0.04] pointer-events-none"
        style={{ background: 'radial-gradient(circle, #06b6d4 0%, transparent 70%)' }} />

      {/* Top Session & Logout Panel */}
      <div className="absolute top-6 left-6 right-6 flex items-center justify-between z-20">
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-emerald-500/10 bg-emerald-500/[0.02] backdrop-blur-md">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-mono tracking-widest text-emerald-400 uppercase flex items-center gap-1.5">
            <UserCheck size={10} /> Secure Session: {currentUser}
          </span>
        </div>
        
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[10px] font-mono tracking-wider uppercase
            text-gray-500 hover:text-red-400 hover:bg-red-500/5 transition-all border border-transparent hover:border-red-500/10"
        >
          <LogOut size={12} /> Log Out
        </button>
      </div>

      {/* Header */}
      <div className="relative z-10 text-center mb-12">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(6,180,212,0.05))', border: '1px solid rgba(16,185,129,0.2)' }}>
            <ShieldCheck size={20} className="text-emerald-400" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white uppercase" style={{ fontFamily: 'Outfit, sans-serif' }}>
            ACCU DESIGN
          </h1>
        </div>
        <p className="text-gray-500 text-xs font-mono tracking-widest uppercase">
          SECURE & CARBON-NEUTRAL ENGINEERING INTERACTION CORE
        </p>
      </div>

      {/* Cards */}
      <div className="relative z-10 flex flex-col md:flex-row gap-6 px-8 max-w-4xl w-full">

        {/* Design Tool Card */}
        <button
          onClick={() => navigate('/design')}
          className="flex-1 group relative rounded-2xl p-8 text-left transition-all duration-300
            hover:shadow-[0_8px_40px_rgba(16,185,129,0.08)] hover:-translate-y-1"
          style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.005) 100%)',
            border: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
            style={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.04) 0%, transparent 60%)' }} />

          <div className="relative z-10">
            <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6"
              style={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.12), rgba(16,185,129,0.02))', border: '1px solid rgba(16,185,129,0.15)' }}>
              <PenTool size={22} className="text-emerald-400" />
            </div>

            <h2 className="text-xl font-bold text-white mb-2 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Secure Engineering Design
            </h2>
            <p className="text-gray-400 text-sm leading-relaxed mb-8">
              Audited design algorithms for shafts, bearings, and gears. Generates precise ASME/ISO calculation reports and local STEP files.
            </p>

            <div className="flex flex-wrap gap-2 mb-6">
              {['Shafts', 'Bearings', 'Gears', 'CAMs'].map(t => (
                <span key={t} className="px-2.5 py-1 text-[9px] font-mono font-bold uppercase tracking-wider rounded-md
                  text-emerald-300/70 bg-emerald-500/5 border border-emerald-500/10">
                  {t}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold group-hover:gap-3 transition-all">
              <span>Enter Design Cockpit</span>
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </button>

        {/* Quoting Engine Card */}
        <button
          onClick={() => navigate('/quote')}
          className="flex-1 group relative rounded-2xl p-8 text-left transition-all duration-300
            hover:shadow-[0_8px_40px_rgba(6,182,212,0.08)] hover:-translate-y-1"
          style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.005) 100%)',
            border: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
            style={{ background: 'linear-gradient(135deg, rgba(6,182,212,0.04) 0%, transparent 60%)' }} />

          <div className="relative z-10">
            <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6"
              style={{ background: 'linear-gradient(135deg, rgba(6,182,212,0.12), rgba(6,182,212,0.02))', border: '1px solid rgba(6,182,212,0.15)' }}>
              <Cog size={22} className="text-cyan-400" />
            </div>

            <h2 className="text-xl font-bold text-white mb-2 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Precision Quoting Engine
            </h2>
            <p className="text-gray-400 text-sm leading-relaxed mb-8">
              Verify B-Rep geometries instantly. Encrypted cost estimation under audited industrial pricing tables.
            </p>

            <div className="flex flex-wrap gap-2 mb-6">
              {['STEP Analysis', 'B-Rep Math', 'Secure Pricing', 'Audit Log'].map(t => (
                <span key={t} className="px-2.5 py-1 text-[9px] font-mono font-bold uppercase tracking-wider rounded-md
                  text-cyan-300/70 bg-cyan-500/5 border border-cyan-500/10">
                  {t}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2 text-cyan-400 text-sm font-semibold group-hover:gap-3 transition-all">
              <span>Open Quoting Engine</span>
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </button>
      </div>

      {/* Footer badges */}
      <div className="relative z-10 flex flex-wrap justify-center items-center gap-6 mt-16">
        <div className="flex items-center gap-1.5 text-gray-600 text-[10px] font-mono tracking-widest uppercase">
          <ShieldCheck size={12} className="text-emerald-500/60" /> ISO 27001 & ASME Compliant
        </div>
        <div className="flex items-center gap-1.5 text-gray-600 text-[10px] font-mono tracking-widest uppercase">
          <Leaf size={12} className="text-emerald-500/60" /> Carbon-Neutral Computing
        </div>
        <div className="flex items-center gap-1.5 text-gray-600 text-[10px] font-mono tracking-widest uppercase">
          <Lock size={12} className="text-cyan-500/60" /> ACCU AI Secured Core
        </div>
      </div>
    </div>
  );
}
