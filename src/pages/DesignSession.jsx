import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Loader2, Send, CheckCircle2, AlertTriangle, Download, Calculator,
  Box, ChevronRight, Home, PenTool, Lock, ArrowRight, Cog,
  Edit3, ShieldCheck, X, Save, RefreshCw, Brain
} from 'lucide-react';

const STATUS_LABELS = {
  collecting_params: 'COLLECTING',
  params_complete: 'PARAMS OK',
  report_ready: 'REPORT READY',
  report_approved: 'APPROVED',
  cad_ready: 'CAD DONE',
};

export default function DesignSession() {
  const { id } = useParams();
  const navigate = useNavigate();
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState(null);
  const [paramDefs, setParamDefs] = useState([]);

  // Chat-like param intake
  const [chatMessages, setChatMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [generatingCad, setGeneratingCad] = useState(false);
  const [approvingReport, setApprovingReport] = useState(false);

  // Edit & AI Validation
  const [editingParam, setEditingParam] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState(null);

  // Load session
  const fetchSession = async () => {
    try {
      const res = await fetch(`/api/design/sessions/${id}`);
      if (!res.ok) { navigate('/design'); return; }
      const data = await res.json();
      setSession(data);

      // Load param definitions (empty for custom)
      if (data.component_type !== 'custom') {
        const pRes = await fetch(`/api/design/components/${data.component_type}/params`);
        const pData = await pRes.json();
        setParamDefs(pData.params || []);
      }

      if (['report_ready', 'report_approved', 'cad_ready'].includes(data.status)) {
        const rRes = await fetch(`/api/design/sessions/${id}/report`);
        if (rRes.ok) setReport(await rRes.json());
      }
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { fetchSession(); }, [id]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [chatMessages]);

  useEffect(() => {
    if (!submitting && inputRef.current) inputRef.current.focus();
  }, [submitting, session?.next_param]);

  // Build chat history from session params
  // Build chat from params (standard components)
  useEffect(() => {
    if (!session) return;
    if (session.component_type === 'custom') return; // custom uses own chat
    if (!paramDefs.length) return;
    const msgs = [];
    for (const pd of paramDefs) {
      const val = session.params?.[pd.key];
      if (val !== undefined && val !== null) {
        msgs.push({ role: 'assistant', text: pd.question });
        const label = pd.type === 'select'
          ? (pd.options?.find(o => o.value === String(val))?.label || val)
          : `${val} ${pd.unit || ''}`;
        msgs.push({ role: 'user', text: String(label) });
      }
    }
    if (session.next_param) {
      msgs.push({ role: 'assistant', text: session.next_param.question });
    } else if (session.all_params_collected) {
      msgs.push({ role: 'assistant', text: '✓ All parameters collected. Ready for report generation.' });
    }
    setChatMessages(msgs);
  }, [session?.params, session?.next_param, paramDefs]);

  // Custom part chat — uses /chat endpoint with iterative questions
  const [customQuestion, setCustomQuestion] = useState(null);
  const [customProgress, setCustomProgress] = useState('0/15');

  useEffect(() => {
    if (!session || session.component_type !== 'custom') return;
    // On first load, send empty chat to get first question
    if (Object.keys(session.params || {}).length === 0 && !customQuestion) {
      setChatMessages([{ role: 'assistant', text: 'Welcome! Let me collect details about your custom part. I\'ll ask a series of questions.' }]);
      // Trigger first question
      fetch(`/api/design/sessions/${id}/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: session.custom_description || 'start' }),
      }).then(r => r.json()).then(data => {
        if (data.next_question) {
          setCustomQuestion(data.next_question);
          setCustomProgress(data.progress || '1/15');
          setChatMessages(prev => [...prev, { role: 'assistant', text: data.next_question.q }]);
        }
      }).catch(console.error);
    } else if (Object.keys(session.params || {}).length > 0 && !customQuestion) {
      // Rebuild chat from existing params
      const msgs = [];
      for (const [k, v] of Object.entries(session.params)) {
        msgs.push({ role: 'assistant', text: `(${k})` });
        msgs.push({ role: 'user', text: String(v) });
      }
      if (session.all_params_collected) {
        msgs.push({ role: 'assistant', text: '✓ All information collected! Ready for report.' });
      }
      setChatMessages(msgs);
    }
  }, [session?.component_type]);

  const handleCustomSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || submitting) return;
    const val = inputValue.trim();
    setSubmitting(true);
    setInputValue('');
    setChatMessages(prev => [...prev, { role: 'user', text: val }]);
    try {
      const res = await fetch(`/api/design/sessions/${id}/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: val }),
      });
      const data = await res.json();
      if (data.error) {
        setChatMessages(prev => [...prev, { role: 'error', text: data.error }]);
      } else if (data.all_done) {
        setChatMessages(prev => [...prev, { role: 'assistant', text: data.message }]);
        setCustomQuestion(null);
        await fetchSession();
      } else if (data.next_question) {
        setCustomQuestion(data.next_question);
        setCustomProgress(data.progress || '');
        setChatMessages(prev => [...prev, { role: 'assistant', text: data.next_question.q }]);
      }
    } catch (e) {
      setChatMessages(prev => [...prev, { role: 'error', text: 'Network error' }]);
    }
    setSubmitting(false);
  };

  // Submit parameter
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || !session?.next_param || submitting) return;

    const np = session.next_param;
    let value = inputValue.trim();

    // For select types, try matching by label or value
    if (np.type === 'select') {
      const match = np.options?.find(o =>
        o.value === value || o.label.toLowerCase().includes(value.toLowerCase())
      );
      if (match) value = match.value;
    }

    setSubmitting(true);
    setInputValue('');

    try {
      const res = await fetch(`/api/design/sessions/${id}/params`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: np.key, value }),
      });
      if (!res.ok) {
        const err = await res.json();
        setChatMessages(prev => [...prev, { role: 'error', text: err.detail || 'Invalid value' }]);
      }
      await fetchSession();
    } catch (e) {
      setChatMessages(prev => [...prev, { role: 'error', text: 'Network error' }]);
    }
    setSubmitting(false);
  };

  // Select option click
  const handleOptionClick = async (optionValue) => {
    if (!session?.next_param || submitting) return;
    setSubmitting(true);
    try {
      await fetch(`/api/design/sessions/${id}/params`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: session.next_param.key, value: optionValue }),
      });
      await fetchSession();
    } catch (e) { console.error(e); }
    setSubmitting(false);
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    setValidation(null);
    try {
      const res = await fetch(`/api/design/sessions/${id}/generate-report`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      }
      await fetchSession();
    } catch (e) { console.error(e); }
    setGeneratingReport(false);
  };

  const handleApprove = async () => {
    setApprovingReport(true);
    try {
      await fetch(`/api/design/sessions/${id}/approve-report`, { method: 'POST' });
      await fetchSession();
    } catch (e) { console.error(e); }
    setApprovingReport(false);
  };

  const handleGenerateCad = async () => {
    setGeneratingCad(true);
    try {
      await fetch(`/api/design/sessions/${id}/generate-cad`, { method: 'POST' });
      await fetchSession();
    } catch (e) { console.error(e); }
    setGeneratingCad(false);
  };

  // ── Edit a parameter ──
  const handleStartEdit = (key, currentValue) => {
    setEditingParam(key);
    setEditValue(String(currentValue));
  };

  const handleSaveEdit = async () => {
    if (!editingParam) return;
    setSavingEdit(true);
    try {
      const res = await fetch(`/api/design/sessions/${id}/params`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: editingParam, value: editValue }),
      });
      if (res.ok) {
        setEditingParam(null);
        setEditValue('');
        setReport(null);
        setValidation(null);
        await fetchSession();
      } else {
        const err = await res.json();
        alert(err.detail || 'Invalid value');
      }
    } catch (e) { console.error(e); }
    setSavingEdit(false);
  };

  // ── AI Validation Agent ──
  const handleValidate = async () => {
    setValidating(true);
    try {
      const res = await fetch(`/api/design/sessions/${id}/validate`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setValidation(data.validation);
      }
    } catch (e) { console.error(e); }
    setValidating(false);
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ background: '#060a13' }}>
        <Loader2 size={32} className="animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!session) return null;

  const isCustom = session.component_type === 'custom';
  const np = session.next_param;
  const allDone = session.all_params_collected || (isCustom && session.status !== 'collecting_params');
  const isCollecting = session.status === 'collecting_params';
  const hasReport = report?.result != null;
  const isApproved = session.status === 'report_approved' || session.status === 'cad_ready';
  const isCadReady = session.status === 'cad_ready';

  const filledCount = Object.keys(session.params || {}).length;
  const totalRequired = isCustom ? 15 : paramDefs.filter(p => p.required).length;

  return (
    <div className="h-screen flex flex-col" style={{ background: '#060a13' }}>

      {/* Header */}
      <header className="h-12 flex items-center justify-between px-5 shrink-0"
        style={{ background: 'rgba(6,10,19,0.9)', borderBottom: '1px solid rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)' }}>
        <div className="flex items-center gap-2.5">
          <Link to="/design" className="text-gray-500 hover:text-gray-300 transition-colors">
            <PenTool size={14} />
          </Link>
          <ChevronRight size={10} className="text-gray-700" />
          <span className="font-mono text-[10pt] text-cyan-400/60 border border-cyan-400/20 px-1.5 py-0.5 rounded">
            #{id}
          </span>
          <span className="text-sm font-bold text-white tracking-widest uppercase" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {isCustom ? 'User Part' : session.component_type}
          </span>
          <ChevronRight size={10} className="text-gray-700" />
          <span className="font-mono text-[9pt] px-2 py-0.5 rounded tracking-wider"
            style={{ color: '#22d3ee', background: 'rgba(34,211,238,0.1)', border: '1px solid rgba(34,211,238,0.2)' }}>
            {STATUS_LABELS[session.status] || session.status}
          </span>
        </div>
      </header>

      {/* Main: Chat Left + Report Right */}
      <div className="flex-1 flex overflow-hidden">

        {/* LEFT: Chat Panel — 45% width */}
        <div className="flex flex-col" style={{ width: '45%', minWidth: 340, borderRight: '1px solid rgba(255,255,255,0.06)' }}>

          {/* Param Progress */}
          <div className="px-4 py-3 shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(255,255,255,0.015)' }}>
            {isCustom ? (
              <div>
                <div className="w-full h-1.5 rounded-full mb-2" style={{ background: 'rgba(255,255,255,0.05)' }}>
                  <div className="h-full rounded-full transition-all" style={{
                    width: `${(filledCount / totalRequired) * 100}%`,
                    background: allDone ? '#34d399' : 'linear-gradient(90deg, #7c3aed, #818cf8)',
                  }} />
                </div>
                <div className="font-mono text-[10pt] text-gray-500">
                  {allDone
                    ? <span className="text-violet-400 flex items-center gap-1"><CheckCircle2 size={10} /> Custom part info complete</span>
                    : <span className="text-violet-400/80">{customProgress} — Gathering details...</span>
                  }
                </div>
              </div>
            ) : (
              <div>
                <div className="flex gap-1 mb-2">
                  {paramDefs.filter(p => p.required).map((p) => {
                    const filled = session.params?.[p.key] != null;
                    const isNext = np?.key === p.key;
                    return (
                      <div key={p.key} className="flex-1 py-1.5 px-1 text-center rounded transition-all" style={{
                        background: filled ? 'rgba(34,211,238,0.08)' : isNext ? 'rgba(245,158,11,0.06)' : 'rgba(255,255,255,0.02)',
                        border: `1px solid ${filled ? 'rgba(34,211,238,0.25)' : isNext ? 'rgba(245,158,11,0.25)' : 'rgba(255,255,255,0.04)'}`,
                      }}>
                        <div className="font-mono text-[9pt] text-gray-600 truncate">{p.label.split(' ')[0]}</div>
                        <div className={`font-mono text-[10pt] font-bold mt-0.5 ${filled ? 'text-cyan-400' : isNext ? 'text-amber-400' : 'text-gray-700'}`}>
                          {filled ? '✓' : isNext ? '→' : '—'}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="font-mono text-[10pt] text-gray-500">
                  {allDone
                    ? <span className="text-cyan-400 flex items-center gap-1"><CheckCircle2 size={10} /> All {totalRequired} parameters collected</span>
                    : <span className="text-amber-400/80">{filledCount}/{totalRequired} — Awaiting: {np?.label}</span>
                  }
                </div>
              </div>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3" ref={scrollRef}
            style={{ scrollbarWidth: 'thin', scrollbarColor: '#1e3448 transparent' }}>
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-3 py-2 text-[10pt] leading-relaxed rounded-lg ${
                  msg.role === 'user'
                    ? 'text-white'
                    : msg.role === 'error'
                    ? 'text-red-400'
                    : 'text-gray-400'
                }`} style={{
                  background: msg.role === 'user' ? 'rgba(34,211,238,0.12)' : msg.role === 'error' ? 'rgba(239,68,68,0.08)' : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${msg.role === 'user' ? 'rgba(34,211,238,0.2)' : msg.role === 'error' ? 'rgba(239,68,68,0.2)' : 'rgba(255,255,255,0.05)'}`,
                }}>
                  {msg.text}
                </div>
              </div>
            ))}
            {submitting && (
              <div className="flex justify-start">
                <div className="px-3 py-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <Loader2 size={14} className="animate-spin text-cyan-400" />
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-3 shrink-0" style={{ borderTop: '1px solid rgba(255,255,255,0.05)', background: 'rgba(255,255,255,0.015)' }}>
            {isCustom && isCollecting ? (
              <form onSubmit={handleCustomSubmit} className="flex gap-2">
                <input ref={inputRef} value={inputValue} onChange={e => setInputValue(e.target.value)}
                  placeholder="Type your answer..."
                  className="flex-1 px-3 py-2 text-[10pt] font-mono text-white rounded-lg outline-none
                    focus:ring-1 focus:ring-violet-400/40 placeholder:text-gray-600"
                  style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}
                  disabled={submitting} autoComplete="off" />
                <button type="submit" disabled={submitting || !inputValue.trim()}
                  className="px-3 py-2 rounded-lg transition-all disabled:opacity-30"
                  style={{ background: 'rgba(167,139,250,0.15)', border: '1px solid rgba(167,139,250,0.3)' }}>
                  {submitting ? <Loader2 size={14} className="animate-spin text-violet-400" /> : <Send size={14} className="text-violet-400" />}
                </button>
              </form>
            ) : isCollecting && np ? (
              <div className="space-y-2">
                {np.type === 'select' ? (
                  <div className="space-y-1.5">
                    {np.options?.map(opt => (
                      <button key={opt.value} onClick={() => handleOptionClick(opt.value)}
                        disabled={submitting}
                        className="w-full text-left px-3 py-2 text-[10pt] font-mono rounded-lg transition-all
                          hover:bg-cyan-400/10 text-gray-400 hover:text-cyan-300 disabled:opacity-50"
                        style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
                        {opt.label}
                      </button>
                    ))}
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="flex gap-2">
                    <input ref={inputRef} value={inputValue} onChange={e => setInputValue(e.target.value)}
                      placeholder={`Enter ${np.label} (${np.unit || 'value'})...`}
                      className="flex-1 px-3 py-2 text-[10pt] font-mono text-white rounded-lg outline-none
                        focus:ring-1 focus:ring-cyan-400/40 placeholder:text-gray-600"
                      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}
                      disabled={submitting} autoComplete="off" />
                    <button type="submit" disabled={submitting || !inputValue.trim()}
                      className="px-3 py-2 rounded-lg transition-all disabled:opacity-30"
                      style={{ background: 'rgba(34,211,238,0.15)', border: '1px solid rgba(34,211,238,0.3)' }}>
                      {submitting ? <Loader2 size={14} className="animate-spin text-cyan-400" /> : <Send size={14} className="text-cyan-400" />}
                    </button>
                  </form>
                )}
                {np.type === 'number' && np.min != null && (
                  <div className="text-[9pt] font-mono text-gray-600 px-1">Range: {np.min} — {np.max} {np.unit}</div>
                )}
              </div>
            ) : (
              <div className="text-center py-1 text-[10pt] font-mono text-cyan-400 flex items-center justify-center gap-2">
                <CheckCircle2 size={12} /> Intake complete — review report →
              </div>
            )}
          </div>
        </div>

        {/* RIGHT: Workflow Stages */}
        <div className="flex-1 overflow-y-auto p-5" style={{ scrollbarWidth: 'thin', scrollbarColor: '#1e3448 transparent' }}>
          <div className="space-y-4">

            {/* Stage 1: Report */}
            <StageCard
              icon={Calculator} title="Engineering Calculations"
              locked={!allDone && !hasReport}
              badge={hasReport ? (isApproved ? { text: 'APPROVED', color: '#34d399' } : { text: 'REVIEW', color: '#f59e0b' }) : null}
              action={!hasReport && allDone ? (
                <button onClick={handleGenerateReport} disabled={generatingReport}
                  className="px-3 py-1.5 text-[10pt] font-mono font-bold tracking-wider rounded-lg transition-all
                    text-cyan-300 hover:text-white disabled:opacity-50"
                  style={{ background: 'rgba(34,211,238,0.12)', border: '1px solid rgba(34,211,238,0.3)' }}>
                  {generatingReport ? <><Loader2 size={12} className="inline animate-spin mr-1" />GENERATING</> : 'GENERATE REPORT'}
                </button>
              ) : null}
            >
              {hasReport ? (
                <div className="space-y-4">
                  {/* Editable Parameters Summary */}
                  <div className="px-3 py-2.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)' }}>
                    <div className="text-[10pt] font-mono text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <Edit3 size={10} /> Input Parameters <span className="text-gray-700">(click to edit)</span>
                    </div>
                    <div className="grid grid-cols-2 lg:grid-cols-3 gap-1.5">
                      {Object.entries(session.params || {}).map(([k, v]) => (
                        <div key={k} className="group relative">
                          {editingParam === k ? (
                            <div className="flex gap-1">
                              <input value={editValue} onChange={e => setEditValue(e.target.value)}
                                className="flex-1 px-2 py-1 text-[10pt] font-mono text-white rounded bg-transparent outline-none"
                                style={{ border: '1px solid rgba(34,211,238,0.4)' }}
                                autoFocus onKeyDown={e => e.key === 'Enter' && handleSaveEdit()} />
                              <button onClick={handleSaveEdit} disabled={savingEdit}
                                className="p-1 rounded text-emerald-400 hover:bg-emerald-400/10">
                                {savingEdit ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                              </button>
                              <button onClick={() => setEditingParam(null)} className="p-1 rounded text-gray-500 hover:bg-white/5">
                                <X size={12} />
                              </button>
                            </div>
                          ) : (
                            <button onClick={() => handleStartEdit(k, v)}
                              className="w-full text-left px-2 py-1.5 rounded transition-all hover:bg-white/[0.03] group"
                              style={{ border: '1px solid transparent' }}>
                              <div className="text-[10pt] font-mono text-gray-500 truncate">{k}</div>
                              <div className="text-[10pt] font-mono text-cyan-400 font-bold truncate flex items-center gap-1">
                                {String(v)}
                                <Edit3 size={10} className="text-gray-700 opacity-0 group-hover:opacity-100 transition-opacity" />
                              </div>
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Calculations grid — 2 columns */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
                    {report.result.calculations?.map((c, i) => (
                      <div key={i} className="px-3 py-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)' }}>
                        <div className="flex items-center justify-between">
                          <span className="text-[10pt] font-semibold text-gray-300">{c.name}</span>
                          <span className="font-mono text-[10pt] font-bold text-cyan-400">{c.result} {c.unit}</span>
                        </div>
                        <div className="font-mono text-[10pt] text-gray-600 mt-0.5">{c.formula}</div>
                        <div className="text-[10pt] text-gray-500 mt-0.5">{c.description}</div>
                      </div>
                    ))}
                  </div>

                  {/* Safety Assessment */}
                  <SafetyBlock safety={report.result.safety} />

                  {/* Internal Validation */}
                  {validation && (
                    <div className="rounded-lg p-3 space-y-2" style={{
                      background: validation.validation_status === 'PASS' ? 'rgba(52,211,153,0.05)' : validation.validation_status === 'FAIL' ? 'rgba(239,68,68,0.05)' : 'rgba(245,158,11,0.05)',
                      border: `1px solid ${validation.validation_status === 'PASS' ? 'rgba(52,211,153,0.2)' : validation.validation_status === 'FAIL' ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)'}`,
                    }}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <ShieldCheck size={14} className={validation.validation_status === 'PASS' ? 'text-emerald-400' : 'text-amber-400'} />
                          <span className="text-[10pt] font-mono font-bold text-white uppercase tracking-wider">Engineering Assessment</span>
                        </div>
                        <span className={`px-2 py-0.5 text-[10pt] font-mono font-bold rounded ${validation.validation_status === 'PASS' ? 'text-emerald-400' : 'text-amber-400'}`}
                          style={{ background: validation.validation_status === 'PASS' ? 'rgba(52,211,153,0.1)' : 'rgba(245,158,11,0.1)' }}>
                          {validation.validation_status}
                        </span>
                      </div>
                      <div className="text-[10pt] text-gray-400">{validation.overall_assessment}</div>
                      {validation.checks?.slice(0, 5).map((c, i) => (
                        <div key={i} className="flex items-start gap-2 text-[10pt] font-mono">
                          <span className={`shrink-0 mt-0.5 ${c.status === 'OK' ? 'text-emerald-400' : c.status === 'ERROR' ? 'text-red-400' : 'text-amber-400'}`}>
                            {c.status === 'OK' ? '✓' : c.status === 'ERROR' ? '✗' : '⚠'}
                          </span>
                          <div>
                            <span className="text-gray-300">{c.item}</span>
                            {c.note && <span className="text-gray-500 block mt-0.5">{c.note}</span>}
                          </div>
                        </div>
                      ))}
                      {validation.recommendations?.length > 0 && (
                        <div className="mt-2 pt-2" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                          {validation.recommendations.map((r, i) => (
                            <div key={i} className="text-[10pt] font-mono text-gray-400 flex items-start gap-2">
                              <span className="text-cyan-400 shrink-0 mt-0.5">→</span>
                              <span>{r}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Standards */}
                  {report.result.standards?.length > 0 && (
                    <div className="px-3 py-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)' }}>
                      <div className="text-[10pt] font-mono text-gray-500 uppercase tracking-wider mb-1">Standards Referenced</div>
                      {report.result.standards.map((s, i) => (
                        <div key={i} className="text-[10pt] text-gray-400">• {s}</div>
                      ))}
                    </div>
                  )}

                  {/* Action buttons */}
                  {hasReport && !isApproved && (
                    <div className="flex items-center justify-between">
                      <div className="flex gap-2">
                        <button onClick={handleValidate} disabled={validating}
                          className="px-3 py-1.5 text-[10pt] font-mono font-bold tracking-wider rounded-lg transition-all
                            text-violet-300 hover:text-white disabled:opacity-50"
                          style={{ background: 'rgba(167,139,250,0.12)', border: '1px solid rgba(167,139,250,0.3)' }}>
                          {validating ? <><Loader2 size={12} className="inline animate-spin mr-1" />CHECKING</> : <><ShieldCheck size={12} className="inline mr-1" />SYSTEM CHECK</>}
                        </button>
                        <button onClick={handleGenerateReport} disabled={generatingReport}
                          className="px-3 py-1.5 text-[10pt] font-mono font-bold tracking-wider rounded-lg transition-all
                            text-amber-300 hover:text-white disabled:opacity-50"
                          style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)' }}>
                          <RefreshCw size={12} className="inline mr-1" />RE-GENERATE
                        </button>
                      </div>
                      <button onClick={handleApprove} disabled={approvingReport}
                        className="px-4 py-2 text-[10pt] font-mono font-bold tracking-wider rounded-lg transition-all
                          text-emerald-300 hover:text-white disabled:opacity-50"
                        style={{ background: 'rgba(52,211,153,0.12)', border: '1px solid rgba(52,211,153,0.3)' }}>
                        {approvingReport ? <><Loader2 size={12} className="inline animate-spin mr-1" />APPROVING</> : <><CheckCircle2 size={12} className="inline mr-1" />APPROVE REPORT</>}
                      </button>
                    </div>
                  )}
                </div>
              ) : allDone ? (
                <div className="space-y-4">
                  {session.assumptions?.length > 0 && (
                    <div className="px-4 py-3 rounded-lg" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)' }}>
                      <div className="text-[10pt] font-mono text-gray-300 uppercase tracking-wider mb-2 flex items-center gap-2">
                        <Brain size={14} className="text-cyan-400" /> Engineering Assumptions
                      </div>
                      <div className="text-[10pt] text-gray-500 mb-4 font-mono">
                        The system has automatically filled standard engineering defaults based on best practices. You can edit them or proceed.
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {session.assumptions.map(a => {
                          const isEdited = session.params[a.key] !== undefined && session.params[a.key] !== a.default_value;
                          const displayVal = session.params[a.key] !== undefined ? session.params[a.key] : a.default_value;
                          return (
                            <div key={a.key} className="group relative">
                              {editingParam === a.key ? (
                                <div className="flex gap-2">
                                  <input value={editValue} onChange={e => setEditValue(e.target.value)}
                                    className="flex-1 px-3 py-2 text-[10pt] font-mono text-white rounded bg-transparent outline-none"
                                    style={{ border: '1px solid rgba(34,211,238,0.4)' }}
                                    autoFocus onKeyDown={e => e.key === 'Enter' && handleSaveEdit()} />
                                  <button onClick={handleSaveEdit} disabled={savingEdit}
                                    className="p-2 rounded text-emerald-400 hover:bg-emerald-400/10">
                                    {savingEdit ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                  </button>
                                  <button onClick={() => setEditingParam(null)} className="p-2 rounded text-gray-500 hover:bg-white/5">
                                    <X size={14} />
                                  </button>
                                </div>
                              ) : (
                                <button onClick={() => handleStartEdit(a.key, displayVal)}
                                  className="w-full text-left px-3 py-2 rounded transition-all hover:bg-white/[0.03] group"
                                  style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
                                  <div className="text-[10pt] font-mono text-gray-400 flex items-center justify-between">
                                    <span className="truncate">{a.label}</span>
                                    {isEdited && <span className="text-[9pt] text-amber-400 px-1.5 rounded bg-amber-400/10 border border-amber-400/20">EDITED</span>}
                                  </div>
                                  <div className="text-[10pt] font-mono font-bold mt-1 flex items-center gap-1" style={{ color: isEdited ? '#fcd34d' : '#22d3ee' }}>
                                    {String(displayVal)} {a.unit || ''}
                                    <Edit3 size={12} className="text-gray-700 opacity-0 group-hover:opacity-100 transition-opacity ml-1" />
                                  </div>
                                  <div className="text-[9pt] text-gray-600 mt-1.5 leading-tight">{a.reason}</div>
                                </button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  <div className="text-center py-4 font-mono text-[10pt] text-gray-600">
                    Review assumptions above, then click GENERATE REPORT to compute engineering calculations.
                  </div>
                </div>
              ) : (
                <div className="text-center py-6 font-mono text-[10pt] text-gray-700">
                  Complete parameter intake in the chat to unlock.
                </div>
              )}
            </StageCard>

            {/* Stage 2: CAD */}
            <StageCard icon={Box} title="CAD Generation" locked={!isApproved}>
              {isCadReady ? (
                <div className="text-center space-y-3">
                  <div className="font-mono text-[10pt] text-cyan-400">✓ Model generated successfully.</div>
                  <div className="flex gap-3 justify-center">
                    <a href={`/api/design/sessions/${id}/download-cad`} download>
                      <button className="px-4 py-2 text-[10pt] font-mono font-bold tracking-wider rounded-lg
                        text-cyan-300 hover:text-white transition-all"
                        style={{ background: 'rgba(34,211,238,0.12)', border: '1px solid rgba(34,211,238,0.3)' }}>
                        <Download size={12} className="inline mr-1" /> DOWNLOAD STEP
                      </button>
                    </a>
                    <button onClick={async () => {
                      try {
                        // Auto-transfer design data to quoting engine
                        const res = await fetch(`/api/design/sessions/${id}/send-to-quoting`, { method: 'POST' });
                        if (res.ok) {
                          const data = await res.json();
                          // Store transfer data for the quoting page to pick up
                          sessionStorage.setItem('design_transfer', JSON.stringify(data));
                          navigate(`/quote?design_session=${id}`);
                        } else {
                          alert('Transfer failed — please ensure report is approved and CAD is generated.');
                        }
                      } catch (e) {
                        console.error(e);
                        alert('Transfer error — check server connection.');
                      }
                    }}
                      className="px-4 py-2 text-[10pt] font-mono font-bold tracking-wider rounded-lg
                        text-indigo-300 hover:text-white transition-all"
                      style={{ background: 'rgba(129,140,248,0.12)', border: '1px solid rgba(129,140,248,0.3)' }}>
                      <Cog size={12} className="inline mr-1" /> SEND TO QUOTING
                    </button>
                  </div>
                </div>
              ) : isApproved ? (
                <div className="text-center py-4">
                  <button onClick={handleGenerateCad} disabled={generatingCad}
                    className="px-4 py-2 text-[10pt] font-mono font-bold tracking-wider rounded-lg transition-all
                      text-cyan-300 hover:text-white disabled:opacity-50"
                    style={{ background: 'rgba(34,211,238,0.12)', border: '1px solid rgba(34,211,238,0.3)' }}>
                    {generatingCad ? <><Loader2 size={12} className="inline animate-spin mr-1" />GENERATING CAD</> : <><Box size={12} className="inline mr-1" />GENERATE CAD MODEL</>}
                  </button>
                </div>
              ) : (
                <div className="text-center py-4 font-mono text-[10pt] text-gray-700">
                  Approve report to unlock.
                </div>
              )}
            </StageCard>

          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────────────────── */
function StageCard({ icon: Icon, title, locked, badge, action, children }) {
  return (
    <div className={`rounded-xl overflow-hidden transition-all ${locked ? 'opacity-40 pointer-events-none' : ''}`}
      style={{
        background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)',
        border: '1px solid rgba(255,255,255,0.06)',
      }}>
      <div className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: 'rgba(0,0,0,0.15)' }}>
        <div className="flex items-center gap-2">
          <Icon size={14} className="text-cyan-400" />
          <span className="text-[10pt] font-bold text-white uppercase tracking-widest" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {title}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {badge && (
            <span className="px-2 py-0.5 text-[9pt] font-mono font-bold tracking-wider rounded"
              style={{ color: badge.color, background: badge.color + '15', border: `1px solid ${badge.color}30` }}>
              {badge.text}
            </span>
          )}
          {action}
          {locked && <Lock size={12} className="text-gray-600" />}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function SafetyBlock({ safety }) {
  if (!safety) return null;
  const safe = safety.is_safe;
  return (
    <div className="rounded-lg p-3 space-y-2" style={{
      background: safe ? 'rgba(52,211,153,0.05)' : 'rgba(239,68,68,0.05)',
      border: `1px solid ${safe ? 'rgba(52,211,153,0.2)' : 'rgba(239,68,68,0.2)'}`,
    }}>
      <div className="flex items-center gap-6">
        <div>
          <div className="text-[9pt] font-mono text-gray-500 uppercase">Actual FOS</div>
          <div className={`text-xl font-bold font-mono ${safe ? 'text-emerald-400' : 'text-red-400'}`}>
            {safety.fos_actual}
          </div>
        </div>
        <div>
          <div className="text-[9pt] font-mono text-gray-500 uppercase">Required</div>
          <div className="text-xl font-bold font-mono text-white">{safety.fos_required}</div>
        </div>
        <div className="ml-auto">
          <span className={`px-2 py-0.5 text-[9pt] font-mono font-bold tracking-wider rounded ${safe ? 'text-emerald-400' : 'text-red-400'}`}
            style={{ background: safe ? 'rgba(52,211,153,0.1)' : 'rgba(239,68,68,0.1)', border: `1px solid ${safe ? 'rgba(52,211,153,0.3)' : 'rgba(239,68,68,0.3)'}` }}>
            {safe ? 'SAFE' : 'CRITICAL'}
          </span>
        </div>
      </div>
      {safety.warnings?.map((w, i) => (
        <div key={i} className="flex items-start gap-2 text-[10pt] font-mono text-amber-400">
          <AlertTriangle size={11} className="shrink-0 mt-0.5" /> {w}
        </div>
      ))}
      {safety.recommendations?.map((r, i) => (
        <div key={i} className="text-[10pt] font-mono text-gray-500">• {r}</div>
      ))}
    </div>
  );
}
