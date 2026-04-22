import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Cog, PenTool, ArrowRight, Sparkles, Shield, Zap
} from 'lucide-react';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center relative overflow-hidden"
      style={{ background: 'linear-gradient(135deg, #060a13 0%, #0b1120 40%, #0a0f1a 100%)' }}>

      {/* Ambient glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full opacity-[0.07]"
        style={{ background: 'radial-gradient(circle, #22d3ee 0%, transparent 70%)' }} />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] rounded-full opacity-[0.05]"
        style={{ background: 'radial-gradient(circle, #818cf8 0%, transparent 70%)' }} />

      {/* Header */}
      <div className="relative z-10 text-center mb-16">
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, rgba(34,211,238,0.2), rgba(34,211,238,0.05))', border: '1px solid rgba(34,211,238,0.3)' }}>
            <Sparkles size={20} className="text-cyan-400" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>
            ACCU DESIGN
          </h1>
        </div>
        <p className="text-gray-500 text-sm font-medium tracking-wide">
          Unified Engineering Workspace
        </p>
      </div>

      {/* Cards */}
      <div className="relative z-10 flex gap-6 px-8 max-w-4xl w-full">

        {/* Design Tool Card */}
        <button
          onClick={() => navigate('/design')}
          className="flex-1 group relative rounded-2xl p-8 text-left transition-all duration-300
            hover:shadow-[0_8px_40px_rgba(34,211,238,0.12)] hover:-translate-y-1"
          style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
            style={{ background: 'linear-gradient(135deg, rgba(34,211,238,0.06) 0%, transparent 60%)' }} />

          <div className="relative z-10">
            <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6"
              style={{ background: 'linear-gradient(135deg, rgba(34,211,238,0.15), rgba(34,211,238,0.05))', border: '1px solid rgba(34,211,238,0.2)' }}>
              <PenTool size={24} className="text-cyan-400" />
            </div>

            <h2 className="text-xl font-bold text-white mb-2 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Engineering Design
            </h2>
            <p className="text-gray-400 text-sm leading-relaxed mb-8">
              AI-guided mechanical design — shaft, bearing, gearbox, cam. Full calculation reports with ASME/ISO standards.
            </p>

            <div className="flex flex-wrap gap-2 mb-6">
              {['Shaft', 'Bearing', 'Gearbox', 'CAM'].map(t => (
                <span key={t} className="px-2.5 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider rounded-md
                  text-cyan-300/70 bg-cyan-400/5 border border-cyan-400/10">
                  {t}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2 text-cyan-400 text-sm font-semibold group-hover:gap-3 transition-all">
              <span>Open Design Tool</span>
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </button>

        {/* Quoting Engine Card */}
        <button
          onClick={() => navigate('/quote')}
          className="flex-1 group relative rounded-2xl p-8 text-left transition-all duration-300
            hover:shadow-[0_8px_40px_rgba(129,140,248,0.12)] hover:-translate-y-1"
          style={{
            background: 'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
            style={{ background: 'linear-gradient(135deg, rgba(129,140,248,0.06) 0%, transparent 60%)' }} />

          <div className="relative z-10">
            <div className="w-14 h-14 rounded-xl flex items-center justify-center mb-6"
              style={{ background: 'linear-gradient(135deg, rgba(129,140,248,0.15), rgba(129,140,248,0.05))', border: '1px solid rgba(129,140,248,0.2)' }}>
              <Cog size={24} className="text-indigo-400" />
            </div>

            <h2 className="text-xl font-bold text-white mb-2 tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Quoting Engine
            </h2>
            <p className="text-gray-400 text-sm leading-relaxed mb-8">
              Upload STEP files for instant B-Rep analysis, manufacturing cost estimation, and professional quote generation.
            </p>

            <div className="flex flex-wrap gap-2 mb-6">
              {['STEP Upload', 'B-Rep', 'CNC Quote', 'PDF Export'].map(t => (
                <span key={t} className="px-2.5 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider rounded-md
                  text-indigo-300/70 bg-indigo-400/5 border border-indigo-400/10">
                  {t}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-2 text-indigo-400 text-sm font-semibold group-hover:gap-3 transition-all">
              <span>Open Quoting Engine</span>
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </button>
      </div>

      {/* Footer badges */}
      <div className="relative z-10 flex items-center gap-6 mt-16">
        <div className="flex items-center gap-1.5 text-gray-600 text-[10px] font-mono tracking-wide">
          <Shield size={12} /> ISO/ASME Standards
        </div>
        <div className="flex items-center gap-1.5 text-gray-600 text-[10px] font-mono tracking-wide">
          <Zap size={12} /> CadQuery B-Rep Engine
        </div>
        <div className="flex items-center gap-1.5 text-gray-600 text-[10px] font-mono tracking-wide">
          <Sparkles size={12} /> Gemini AI Powered
        </div>
      </div>
    </div>
  );
}
