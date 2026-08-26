import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Cog, PenTool, ArrowRight, Zap, ShieldCheck, Leaf, LogOut, Lock, UserCheck, Layers
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
    <div className="h-screen w-screen flex flex-col items-center justify-center relative overflow-hidden bg-[#f8fafc] text-slate-800 font-sans">

      {/* Subtle Grid Overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#2479c20d_1px,transparent_1px),linear-gradient(to_bottom,#2479c20d_1px,transparent_1px)] bg-[size:3.5rem_3.5rem] pointer-events-none" />

      {/* Ambient glow - AccuDesign blue & subtle orange */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[650px] h-[650px] rounded-full opacity-[0.10] pointer-events-none"
        style={{ background: 'radial-gradient(circle, #2479C2 0%, transparent 70%)' }} />
      <div className="absolute bottom-1/4 right-1/4 w-[450px] h-[450px] rounded-full opacity-[0.06] pointer-events-none"
        style={{ background: 'radial-gradient(circle, #f1683a 0%, transparent 70%)' }} />

      {/* Top Session & Logout Panel */}
      <div className="absolute top-6 left-6 right-6 flex items-center justify-between z-20">
        <div className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-xl border border-slate-200 bg-white/90 backdrop-blur-md shadow-sm">
          <div className="w-2 h-2 rounded-full bg-accu-500 animate-pulse" />
          <span className="text-[10px] font-mono tracking-widest text-slate-700 uppercase flex items-center gap-1.5 font-bold">
            <UserCheck size={11} className="text-accu-600" /> Active Session: {currentUser}
          </span>
        </div>
        
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-[10px] font-mono tracking-wider uppercase
            text-slate-500 hover:text-red-600 hover:bg-red-50 transition-all border border-slate-200 bg-white/90 backdrop-blur-md shadow-sm"
        >
          <LogOut size={12} /> Log Out
        </button>
      </div>

      {/* Header with AccuDesign Logo */}
      <div className="relative z-10 text-center mb-10">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center bg-white border border-slate-200 shadow-md">
            <img 
              src="https://res.cloudinary.com/dxrryep5y/image/upload/v1753295781/website_static_media/ad_logo.svg" 
              alt="ACCU DESIGN" 
              className="w-8 h-8 object-contain"
            />
          </div>
          <div className="text-left">
            <h1 className="text-3xl lg:text-4xl font-black tracking-tight text-slate-900 uppercase font-heading">
              ACCU DESIGN
            </h1>
            <p className="text-accu-600 text-[10px] font-mono tracking-widest uppercase font-bold">
              ON-DEMAND PRECISION MANUFACTURING &amp; QUOTING
            </p>
          </div>
        </div>
      </div>

      {/* Cards */}
      <div className="relative z-10 flex flex-col md:flex-row gap-6 px-6 max-w-4xl w-full">

        {/* Quoting Engine Card - Highlighted primary tool */}
        <button
          onClick={() => navigate('/quote')}
          className="flex-1 group relative rounded-2xl p-8 text-left transition-all duration-300
            bg-white border border-slate-200 shadow-md hover:shadow-xl hover:-translate-y-1 hover:border-accu-400"
        >
          <div className="relative z-10">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-6 bg-accu-50 border border-accu-200 shadow-sm">
              <Cog size={26} className="text-accu-600 group-hover:rotate-45 transition-transform duration-500" />
            </div>

            <h2 className="text-xl font-bold text-slate-900 mb-2 tracking-tight font-heading">
              Instant Quoting Platform
            </h2>
            <p className="text-slate-600 text-sm leading-relaxed mb-6">
              Instantaneous CAD B-Rep analysis and 2D drawing evaluation. Generates official AccuDesign quotations in ₹ INR.
            </p>

            <div className="flex flex-wrap gap-2 mb-6">
              {['STEP Analysis', 'B-Rep Math', 'LME Live Prices', 'Official PDF'].map(t => (
                <span key={t} className="px-2.5 py-1 text-[9px] font-mono font-bold uppercase tracking-wider rounded-md
                  text-accu-700 bg-accu-50 border border-accu-200">
                  {t}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2 text-accuorange-600 text-sm font-bold group-hover:gap-3 transition-all">
              <span>Launch Quoting Engine</span>
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </button>

        {/* Design Tool Card */}
        <button
          onClick={() => navigate('/design')}
          className="flex-1 group relative rounded-2xl p-8 text-left transition-all duration-300
            bg-white border border-slate-200 shadow-md hover:shadow-xl hover:-translate-y-1 hover:border-slate-400"
        >
          <div className="relative z-10">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-6 bg-slate-50 border border-slate-200 shadow-sm">
              <PenTool size={24} className="text-slate-700" />
            </div>

            <h2 className="text-xl font-bold text-slate-900 mb-2 tracking-tight font-heading">
              Engineering Design Suite
            </h2>
            <p className="text-slate-600 text-sm leading-relaxed mb-6">
              Automated design calculation algorithms for shafts, bearings, and gears with ASME/ISO calculation reports.
            </p>

            <div className="flex flex-wrap gap-2 mb-6">
              {['Shafts', 'Bearings', 'Gears', 'CAMs'].map(t => (
                <span key={t} className="px-2.5 py-1 text-[9px] font-mono font-bold uppercase tracking-wider rounded-md
                  text-slate-700 bg-slate-100 border border-slate-200">
                  {t}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2 text-accu-600 text-sm font-bold group-hover:gap-3 transition-all">
              <span>Open Design Suite</span>
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </button>
      </div>

      {/* Footer badges */}
      <div className="relative z-10 flex flex-wrap justify-center items-center gap-6 mt-12">
        <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-mono tracking-widest uppercase font-semibold">
          <ShieldCheck size={13} className="text-accu-600" /> ISO 9001:2015 Precision Quality
        </div>
        <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-mono tracking-widest uppercase font-semibold">
          <Leaf size={13} className="text-emerald-600" /> Pune, Maharashtra, India
        </div>
        <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-mono tracking-widest uppercase font-semibold">
          <Lock size={13} className="text-accu-600" /> ACCU AI Quoting Automation
        </div>
      </div>
    </div>
  );
}
