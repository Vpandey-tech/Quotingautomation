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
      'Connecting to AccuDesign Quoting Cloud...',
      'Verifying precision manufacturing engine...',
      'Initializing B-Rep analysis & LME metal feed...',
      'Allocating secure session...'
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
    <div className="h-screen w-screen flex flex-col lg:flex-row relative overflow-hidden bg-[#f8fafc] text-slate-800 font-sans">
      
      {/* Background Grids & Radial Glows */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#2479c20d_1px,transparent_1px),linear-gradient(to_bottom,#2479c20d_1px,transparent_1px)] bg-[size:4rem_4rem]" />
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-accu-500/8 blur-[130px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-accuorange-500/8 blur-[130px]" />
      </div>

      {/* Left Column: Brand Board */}
      <div className="lg:w-1/2 flex flex-col justify-between p-8 lg:p-16 relative z-10 border-b lg:border-b-0 lg:border-r border-slate-200 bg-white/80 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-slate-50 border border-slate-200 shadow-sm">
            <img 
              src="https://res.cloudinary.com/dxrryep5y/image/upload/v1753295781/website_static_media/ad_logo.svg" 
              alt="ACCU DESIGN" 
              className="w-7 h-7 object-contain"
            />
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-900 uppercase font-heading">
            ACCU DESIGN
          </span>
        </div>

        <div className="my-auto py-12 space-y-8 max-w-md">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-mono font-bold bg-accu-50 text-accu-700 border border-accu-200 uppercase tracking-wider">
              <Leaf size={11} className="text-emerald-600" /> On-Demand Precision Manufacturing · Pune
            </div>
            <h1 className="text-3xl lg:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight font-heading">
              Instant Quoting &amp; Engineering Automation.
            </h1>
            <p className="text-slate-600 text-sm leading-relaxed">
              Upload 3D STEP CAD models or 2D engineering drawings. Automated B-Rep feature extraction, live LME metal pricing, and official PDF quotation generation.
            </p>
          </div>

          <div className="space-y-4 pt-4 border-t border-slate-100">
            <div className="flex gap-4">
              <div className="mt-1 w-8 h-8 rounded-lg flex items-center justify-center bg-slate-100 border border-slate-200 shrink-0">
                <Lock size={14} className="text-accu-600" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-800">Local &amp; Secure CAD Processing</h4>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                  All STEP geometry analysis runs directly in your browser with WebAssembly and isolated calculation threads.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="mt-1 w-8 h-8 rounded-lg flex items-center justify-center bg-slate-100 border border-slate-200 shrink-0">
                <Cpu size={14} className="text-accuorange-600" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-800">ACCU AI Precision Pricing</h4>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                  Automated hole detection, bend calculations, setup amortization, and live metal commodity exchange integration.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="text-[11px] text-slate-500 font-mono flex items-center gap-4 font-semibold">
          <span>PRECISION HUB: PUNE, INDIA</span>
          <span>•</span>
          <span>ACCU DESIGN v2.6.4</span>
        </div>
      </div>

      {/* Right Column: Login Form */}
      <div className="lg:w-1/2 flex flex-col justify-center items-center p-6 lg:p-16 relative z-10 bg-slate-50/50">
        <div className="w-full max-w-md space-y-8 bg-white p-8 rounded-2xl border border-slate-200 shadow-md">
          
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight font-heading">Sign In to Dashboard</h2>
            <p className="text-xs text-slate-500">Enter your authorized AccuDesign credentials to proceed.</p>
          </div>

          {errorMsg && (
            <div className="p-3.5 rounded-xl border border-red-200 bg-red-50 text-red-700 text-xs flex gap-2.5 items-start">
              <ShieldAlert size={16} className="shrink-0 mt-0.5 text-red-500" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-5">
            <div className="space-y-1.5">
              <label className="text-xs font-mono uppercase tracking-wider text-slate-700 font-bold">Email Address</label>
              <input
                type="email"
                required
                disabled={loading}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@accudesign.in"
                className="w-full px-4 py-3 rounded-xl bg-white border border-slate-300 focus:border-accu-500 focus:ring-1 focus:ring-accu-500 text-sm text-slate-800 placeholder-slate-400 outline-none transition-colors font-mono shadow-sm"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-mono uppercase tracking-wider text-slate-700 font-bold">Password</label>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  disabled={loading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-4 py-3 pr-10 rounded-xl bg-white border border-slate-300 focus:border-accu-500 focus:ring-1 focus:ring-accu-500 text-sm text-slate-800 placeholder-slate-400 outline-none transition-colors font-mono shadow-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 px-4 rounded-xl bg-accu-600 hover:bg-accu-700 text-white font-bold text-sm tracking-wider transition-all duration-200 shadow-md flex items-center justify-center gap-2 group cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span className="text-xs font-mono tracking-tight">{loadingStep}</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Branding Footer */}
        <div className="mt-8 text-center animate-fadeIn">
          <p className="text-[10px] uppercase tracking-[0.2em] font-semibold text-slate-400 font-sans">
            POWERED BY{" "}
            <span className="font-extrabold text-accu-600">
              ACCU DESIGN ENGINE
            </span>
          </p>
        </div>
      </div>

    </div>
  );
}
