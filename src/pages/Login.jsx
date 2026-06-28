import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Lock, Leaf, ArrowRight, Loader2, Eye, EyeOff, ShieldAlert, Cpu } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Pre-configured accounts for smooth testing
  const accounts = [
    {
      role: 'Project Lead',
      email: 'admin@accudesign.in',
      pass: 'accu_admin_2026',
      desc: 'Full read/write & pricing override privileges'
    },
    {
      role: 'Senior Reviewer',
      email: 'senior@accudesign.in',
      pass: 'accu_senior_2026',
      desc: 'Auditing, engineering standards validation'
    }
  ];

  const handleLogin = (e) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMsg('Please fill in all security fields.');
      return;
    }

    // Verify credentials
    const matched = accounts.some(acc => acc.email.toLowerCase() === email.toLowerCase() && acc.pass === password);
    if (!matched) {
      setErrorMsg('Access Denied. Invalid workspace credentials.');
      return;
    }

    setErrorMsg('');
    setLoading(true);
    
    // Simulate high-security system handshake & initialization steps
    const steps = [
      'Establishing TLS 1.3 encrypted handshake...',
      'Verifying isolated container hash...',
      'Initializing ACCU AI secure calculation core...',
      'Allocating sandboxed session...'
    ];

    let currentStep = 0;
    setLoadingStep(steps[0]);

    const interval = setInterval(() => {
      currentStep++;
      if (currentStep < steps.length) {
        setLoadingStep(steps[currentStep]);
      } else {
        clearInterval(interval);
        localStorage.setItem('accu_auth', 'true');
        localStorage.setItem('accu_user', email);
        navigate('/');
        setLoading(false);
      }
    }, 600);
  };

  return (
    <div className="h-screen w-screen flex flex-col lg:flex-row relative overflow-hidden bg-[#030712] text-gray-100 font-sans">
      
      {/* Background Grids & Radial Glows (No Sparkles/AI star shapes) */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f29370a_1px,transparent_1px),linear-gradient(to_bottom,#1f29370a_1px,transparent_1px)] bg-[size:4rem_4rem]" />
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-emerald-500/5 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-cyan-500/5 blur-[120px]" />
      </div>

      {/* Left Column: Sustainable & High Security Brand Board */}
      <div className="lg:w-1/2 flex flex-col justify-between p-8 lg:p-16 relative z-10 border-b lg:border-b-0 lg:border-r border-gray-800/40 bg-gray-950/20 backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-gradient-to-br from-emerald-500/20 to-cyan-500/5 border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.1)]">
            <Shield size={18} className="text-emerald-400" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white font-sans uppercase">
            ACCU DESIGN
          </span>
        </div>

        <div className="my-auto py-12 space-y-8 max-w-md">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-wider">
              <Leaf size={10} /> 100% Sustainable Computing
            </div>
            <h1 className="text-3xl lg:text-4xl font-extrabold text-white tracking-tight leading-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
              The Secure Quoting & Design workspace.
            </h1>
            <p className="text-gray-400 text-sm leading-relaxed">
              Experience the highest benchmark of engineering calculations. Zero cloud leaks, fully local parameter storage, and audited energy-optimized calculation models.
            </p>
          </div>

          <div className="space-y-4 pt-4 border-t border-gray-800/50">
            <div className="flex gap-4">
              <div className="mt-1 w-8 h-8 rounded-lg flex items-center justify-center bg-gray-900 border border-gray-800 shrink-0">
                <Lock size={14} className="text-cyan-400" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-gray-200">End-to-End Cryptographic Security</h4>
                <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                  All STEP geometry analysis and drawing conversions run inside sandboxed threads with zero external exposure.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="mt-1 w-8 h-8 rounded-lg flex items-center justify-center bg-gray-900 border border-gray-800 shrink-0">
                <Cpu size={14} className="text-emerald-400" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-gray-200">ACCU AI Core Calculations</h4>
                <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                  Advanced geometric reasoning engineered for accuracy. No conversational fluff—just rapid, precise manufacturing metrics.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="text-[11px] text-gray-600 font-mono flex items-center gap-4">
          <span>COMPLIANCE: ASME Y14.5 / ISO 27001</span>
          <span>•</span>
          <span>ACCU-SECURE v2.6.4</span>
        </div>
      </div>

      {/* Right Column: Clean, Minimal Login Frame */}
      <div className="lg:w-1/2 flex flex-col justify-center items-center p-6 lg:p-16 relative z-10">
        <div className="w-full max-w-md space-y-8">
          
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-white tracking-tight">Security Gateway</h2>
            <p className="text-xs text-gray-500">Provide pre-authorized credentials to access the engineering dashboard.</p>
          </div>

          {errorMsg && (
            <div className="p-3.5 rounded-lg border border-red-500/20 bg-red-950/20 text-red-400 text-xs flex gap-2.5 items-start">
              <ShieldAlert size={16} className="shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-1.5">
              <label className="text-xs font-mono uppercase tracking-wider text-gray-400">Security Email / ID</label>
              <input
                type="email"
                required
                disabled={loading}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@accudesign.in"
                className="w-full px-4 py-3 rounded-lg bg-gray-900/60 border border-gray-800 focus:border-cyan-500/50 text-sm text-white placeholder-gray-600 outline-none transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-mono uppercase tracking-wider text-gray-400">Workspace Password</label>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  disabled={loading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-4 py-3 pr-10 rounded-lg bg-gray-900/60 border border-gray-800 focus:border-cyan-500/50 text-sm text-white placeholder-gray-600 outline-none transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-lg bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-gray-950 font-bold text-sm tracking-wide transition-all duration-200 shadow-lg shadow-emerald-500/10 flex items-center justify-center gap-2 group"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span className="text-xs font-mono tracking-tight">{loadingStep}</span>
                </>
              ) : (
                <>
                  <span>Authenticate Securely</span>
                  <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* TechNewity Labs Branding */}
        <div className="mt-6 text-center animate-fadeIn">
          <p className="text-[10px] uppercase tracking-[0.2em] font-semibold text-gray-500 font-sans">
            developed by{" "}
            <span className="font-extrabold bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400 bg-clip-text text-transparent drop-shadow-[0_0_8px_rgba(34,211,238,0.15)]">
              TechNewity Labs
            </span>
          </p>
        </div>
      </div>

    </div>
  );
}
