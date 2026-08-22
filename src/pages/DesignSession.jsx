import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Loader2, Send, CheckCircle2, AlertTriangle, Download, Calculator,
  Box, ChevronRight, PenTool, ArrowRight, Cog,
  Edit3, ShieldCheck, X, Save, Sparkles, Info,
  AlertTriangle as TriangleAlert, Layers, Zap, Lock, Home, BarChart3, FileText
} from 'lucide-react';

// ── Component family meta (icons + hints) ────────────────────────────────────
const FAMILY_META = {
  shaft:             { color: '#10b981', icon: '⚙', hint: 'Drive shafts, axles, spindles with keyways & keyslots' },
  flange:            { color: '#06b6d4', icon: '🔩', hint: 'Circular flanges with bolt-circle hole patterns (PCD)' },
  plate_hole_pattern:{ color: '#3b82f6', icon: '🪟', hint: 'Flat baseplates with rectangular or circular hole grids' },
  bracket:           { color: '#f59e0b', icon: '📐', hint: 'L-shape, U-shape or flat mounting brackets' },
  spacer:            { color: '#8b5cf6', icon: '🧱', hint: 'Bushings, standoffs, collars with inner bore' },
  lever:             { color: '#ef4444', icon: '↕', hint: 'Lever arms with pivot bore and load-end bore' },
  housing:           { color: '#64748b', icon: '🏠', hint: 'Protective enclosures, casings, gearbox shells' },
  bearing:           { color: '#0ea5e9', icon: '⭕', hint: 'Ball or roller bearings sized by load, speed, life' },
  gearbox:           { color: '#a3e635', icon: '⚙⚙', hint: 'Spur / helical gear transmission — power, ratio, stages' },
  cam:               { color: '#fb923c', icon: '🌀', hint: 'Cam disc motion profiles — rise, dwell, lift' },
  custom:            { color: '#e2e8f0', icon: '✦', hint: 'Any other mechanical part via freeform description' },
};

// ── Field hints per parameter key ─────────────────────────────────────────────
const FIELD_HINTS = {
  outer_diameter_mm:     'Typical flanges: 80–400 mm',
  inner_bore_diameter_mm:'Enter 0 for solid (no bore)',
  thickness_mm:          'Min 6mm for structural integrity',
  bolt_circle_diameter_mm:'PCD must be smaller than outer diameter',
  num_bolts:             'Standard patterns: 4, 6, or 8 bolts',
  wall_thickness_mm:     'Minimum 1.0mm; CNC min 0.8mm',
  diameter_mm:           'Final diameter after machining allowance',
  length_mm:             'Total end-to-end length in mm',
  power_kw:              'Motor rated power at operating load',
  speed_rpm:             'Shaft operating speed under load',
  radial_load_n:         '1 kN = 1000 N; 1 tonne-force ≈ 9810 N',
  desired_life_hours:    'Industrial standard: 20 000 h',
  outer_length_mm:       'External bounding length of the housing',
  pivot_bore_diameter_mm:'Bore for pivot pin or shaft passing through lever',
  hole_diameter_mm:      'Clearance hole = bolt size + 0.5–1.0 mm',
};

// ── Workflow steps ─────────────────────────────────────────────────────────────
const STEPS = [
  { id: 'gather',  label: 'Specifications', icon: FileText },
  { id: 'report',  label: 'Analysis',       icon: BarChart3 },
  { id: 'cad',     label: '3D CAD',         icon: Box },
];

function currentStep(status) {
  if (status === 'cad_ready')                    return 2;
  if (['report_approved','report_ready'].includes(status)) return 1;
  return 0;
}

export default function DesignSession() {
  const { id } = useParams();
  const navigate = useNavigate();
  const scrollRef  = useRef(null);
  const inputRef   = useRef(null);

  const [session,   setSession]   = useState(null);
  const [report,    setReport]    = useState(null);
  const [loading,   setLoading]   = useState(true);

  const [inputValue,      setInputValue]      = useState('');
  const [submitting,      setSubmitting]      = useState(false);
  const [genReport,       setGenReport]       = useState(false);
  const [genCad,          setGenCad]          = useState(false);
  const [approving,       setApproving]       = useState(false);
  const [cadError,        setCadError]        = useState(null);

  // Batch form — keyed by field, pre-filled with defaults
  const [formValues,  setFormValues]  = useState({});
  const [formErrors,  setFormErrors]  = useState({});

  // Inline param editing
  const [editKey,   setEditKey]   = useState(null);
  const [editVal,   setEditVal]   = useState('');
  const [saving,    setSaving]    = useState(false);
  const [savedKey,  setSavedKey]  = useState(null);

  // ── Data fetching ───────────────────────────────────────────────────────────
  const fetchSession = useCallback(async () => {
    try {
      const res = await fetch(`/api/design/sessions/${id}`);
      if (!res.ok) { navigate('/design'); return; }
      const data = await res.json();
      setSession(data);
      if (['report_ready','report_approved','cad_ready'].includes(data.status)) {
        const rr = await fetch(`/api/design/sessions/${id}/report`);
        if (rr.ok) setReport(await rr.json());
      }
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [id, navigate]);

  useEffect(() => { fetchSession(); }, [fetchSession]);

  // Auto-scroll chat
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [session]);

  // Pre-fill batch form defaults whenever clarification_questions changes
  useEffect(() => {
    if (!session?.clarification_questions) return;
    setFormValues(prev => {
      const next = { ...prev };
      for (const q of session.clarification_questions) {
        if (!(q.field in next) && q.default_value != null) {
          next[q.field] = String(q.default_value);
        }
      }
      return next;
    });
  }, [session?.clarification_questions]);

  // ── Handlers ────────────────────────────────────────────────────────────────
  const handleChatSubmit = async (e) => {
    e.preventDefault();
    const txt = inputValue.trim();
    if (!txt || submitting) return;
    setInputValue('');
    setSubmitting(true);
    try {
      const res = await fetch(`/api/design/sessions/${id}/spec-intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: txt }),
      });
      await fetchSession();
      if (!res.ok) console.error(await res.json());
    } catch (e) { console.error(e); }
    setSubmitting(false);
  };

  const validateForm = () => {
    if (!session?.clarification_questions) return true;
    const errs = {};
    for (const q of session.clarification_questions) {
      const val = formValues[q.field];
      if (q.type === 'number' && val != null && val !== '') {
        const n = parseFloat(val);
        if (isNaN(n)) { errs[q.field] = 'Must be a number'; continue; }
        if (q.min != null && n < q.min) { errs[q.field] = `Min ${q.min}`; continue; }
        if (q.max != null && n > q.max) { errs[q.field] = `Max ${q.max}`; }
      }
    }
    setFormErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleBatchSubmit = async (e) => {
    if (e) e.preventDefault();
    if (submitting || !validateForm()) return;
    setSubmitting(true);
    // Fill defaults for any still-empty fields
    const answers = {};
    for (const q of (session?.clarification_questions || [])) {
      const raw = formValues[q.field];
      if (raw != null && String(raw).trim() !== '') {
        answers[q.field] = q.type === 'number' ? parseFloat(raw) : raw;
      } else if (q.default_value != null) {
        answers[q.field] = q.default_value;
      }
    }
    try {
      await fetch(`/api/design/sessions/${id}/params/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers }),
      });
      setFormValues({});
      setFormErrors({});
      await fetchSession();
    } catch (e) { console.error(e); }
    setSubmitting(false);
  };

  const startEdit = (k, v) => { setEditKey(k); setEditVal(String(v ?? '')); };
  const cancelEdit = () => { setEditKey(null); setEditVal(''); };

  const saveEdit = async () => {
    if (!editKey) return;
    setSaving(true);
    const keyDone = editKey;
    try {
      const res = await fetch(`/api/design/sessions/${id}/params`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ params: { [editKey]: isNaN(parseFloat(editVal)) ? editVal : parseFloat(editVal) } }),
      });
      if (res.ok) {
        setSavedKey(keyDone);
        setTimeout(() => setSavedKey(prev => prev === keyDone ? null : prev), 2500);
      }
      cancelEdit();
      await fetchSession();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleGenerateReport = async () => {
    setGenReport(true);
    try {
      const res = await fetch(`/api/design/sessions/${id}/generate-report`, { method: 'POST' });
      if (res.ok) { const d = await res.json(); setReport(d); }
      await fetchSession();
    } catch (e) { console.error(e); }
    setGenReport(false);
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      await fetch(`/api/design/sessions/${id}/approve-report`, { method: 'POST' });
      await fetchSession();
    } catch (e) { console.error(e); }
    setApproving(false);
  };

  const handleGenerateCad = async () => {
    setGenCad(true); setCadError(null);
    try {
      const res = await fetch(`/api/design/sessions/${id}/generate-cad`, { method: 'POST' });
      if (res.ok) { await fetchSession(); }
      else { const d = await res.json(); setCadError(d.explanation || 'CAD generation failed.'); }
    } catch (e) { console.error(e); }
    setGenCad(false);
  };

  const sendToQuoting = async () => {
    try {
      const res = await fetch(`/api/design/sessions/${id}/send-to-quoting`, { method: 'POST' });
      if (res.ok) {
        const d = await res.json();
        sessionStorage.setItem('design_transfer', JSON.stringify(d));
        navigate(`/quote?design_session=${id}`);
      }
    } catch (e) { console.error(e); }
  };

  // ── Derived state ──────────────────────────────────────────────────────────
  if (loading) return (
    <div className="h-screen flex items-center justify-center" style={{ background: '#060a13' }}>
      <div className="flex flex-col items-center gap-3">
        <Loader2 size={28} className="animate-spin text-cyan-400" />
        <span className="font-mono text-[9pt] text-gray-500 uppercase tracking-widest">Loading session...</span>
      </div>
    </div>
  );
  if (!session) return null;

  const meta            = FAMILY_META[session.component_type] || FAMILY_META.custom;
  const qs              = session.clarification_questions || [];
  const params          = session.params || {};
  const paramEntries    = Object.entries(params).filter(([,v]) => v != null && v !== '');
  const allDone         = session.all_params_collected || session.status !== 'collecting_params';
  const hasReport       = !!report?.result;
  const isApproved      = ['report_approved','cad_ready'].includes(session.status);
  const isCadReady      = session.status === 'cad_ready';
  const stepIdx         = currentStep(session.status);
  const tokenUsage      = session.token_usage || {};
  const totalCalls      = (tokenUsage.intake_calls||0) + (tokenUsage.delta_parser_calls||0) + (tokenUsage.failure_corrector_calls||0);

  // Progress in the batch form
  const answeredCount   = qs.filter(q => {
    const v = formValues[q.field];
    return v != null && String(v).trim() !== '';
  }).length;
  const totalCount      = qs.length;
  const pct             = totalCount > 0 ? Math.round((answeredCount / totalCount) * 100) : 100;

  return (
    <div className="h-screen flex flex-col" style={{ background: '#060a13', fontFamily: "'Inter', sans-serif" }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="h-13 shrink-0 flex items-center justify-between px-5"
        style={{ background: 'rgba(6,10,19,0.95)', borderBottom: '1px solid rgba(255,255,255,0.07)', backdropFilter: 'blur(16px)' }}>

        <div className="flex items-center gap-2.5">
          <Link to="/design" className="text-gray-500 hover:text-gray-300 transition-colors">
            <PenTool size={14} />
          </Link>
          <ChevronRight size={10} className="text-gray-700" />
          <span className="font-mono text-[10px] px-2 py-0.5 rounded border"
            style={{ color: meta.color, borderColor: meta.color + '40', background: meta.color + '12' }}>
            #{id}
          </span>
          <span className="font-bold text-white text-sm tracking-widest uppercase"
            style={{ fontFamily: 'Outfit, sans-serif' }}>
            {FAMILY_META[session.component_type]?.icon} {session.component_type.replace(/_/g,' ')}
          </span>
        </div>

        {/* Step rail */}
        <div className="hidden md:flex items-center gap-0">
          {STEPS.map((s, i) => {
            const done    = i < stepIdx;
            const active  = i === stepIdx;
            return (
              <React.Fragment key={s.id}>
                <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[9pt] font-mono transition-all ${
                  done   ? 'text-emerald-400' :
                  active ? 'text-white bg-white/10' :
                           'text-gray-600'
                }`}>
                  {done ? <CheckCircle2 size={11} /> : <s.icon size={11} />}
                  {s.label}
                </div>
                {i < STEPS.length - 1 && (
                  <ChevronRight size={10} className={done ? 'text-emerald-600' : 'text-gray-700'} />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* LLM budget badge */}
        <div className="flex items-center gap-2 font-mono text-[9pt]">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded"
            style={{ background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.3)', color: '#a5b4fc' }}>
            <Sparkles size={10} className="text-indigo-400" />
            <span>AI Calls: <strong className="text-white">{totalCalls}</strong> / Budget ≤ 3</span>
          </div>
        </div>
      </header>

      {/* ── Body: Left chat | Right workflow ───────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* LEFT — Chat + Guided Intake */}
        <div className="flex flex-col" style={{ width: '46%', minWidth: 340, borderRight: '1px solid rgba(255,255,255,0.06)' }}>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">

            {/* ── Welcome assistant bubble ── */}
            <AssistantBubble>
              <div className="flex items-start gap-2.5">
                <div className="text-2xl shrink-0">{meta.icon}</div>
                <div>
                  <p className="font-bold text-white text-[10pt] mb-0.5">
                    {session.component_type.replace(/_/g,' ').toUpperCase()} Design Session
                  </p>
                  <p className="text-gray-400 text-[9.5pt] leading-relaxed">{meta.hint}</p>
                  {session.custom_description && (
                    <p className="mt-2 text-cyan-300 text-[9pt] italic border-l-2 border-cyan-500/40 pl-2">
                      "{session.custom_description}"
                    </p>
                  )}
                </div>
              </div>
            </AssistantBubble>

            {/* ── Extracted spec card (all values inline-editable) ── */}
            {paramEntries.length > 0 && (
              <div className="rounded-xl p-3.5 space-y-2 text-[9pt] font-mono"
                style={{ background: 'rgba(16,185,129,0.05)', border: '1px solid rgba(16,185,129,0.18)' }}>
                <div className="flex items-center gap-1.5 text-emerald-400 font-bold uppercase tracking-wider text-[8.5pt] mb-1">
                  <CheckCircle2 size={11} /> Extracted Specifications
                  <span className="ml-auto text-gray-600 text-[8pt] normal-case">Click any value to edit</span>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {paramEntries.map(([k, v]) => {
                    const isEditing = editKey === k;
                    const isDirty = isEditing && editVal !== String(v ?? '');
                    const isJustSaved = savedKey === k;

                    return (
                      <div key={k} className={`rounded-lg p-2 flex items-center justify-between gap-1 group cursor-pointer transition-all ${
                        isJustSaved ? 'bg-emerald-950/40 ring-1 ring-emerald-400/60' : 'hover:bg-white/5'
                      }`}
                        style={{
                          background: isJustSaved ? 'rgba(16,185,129,0.12)' : 'rgba(0,0,0,0.25)',
                          border: isJustSaved ? '1px solid rgba(16,185,129,0.4)' : isDirty ? '1px solid rgba(251,191,36,0.6)' : '1px solid rgba(255,255,255,0.06)'
                        }}
                        onClick={() => editKey !== k && startEdit(k, v)}>
                        <span className="text-gray-500 truncate text-[8.5pt]">{k.replace(/_mm$/,' mm').replace(/_/g,' ')}</span>
                        {isEditing ? (
                          <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                            <input
                              autoFocus
                              value={editVal}
                              onChange={e => setEditVal(e.target.value)}
                              onKeyDown={e => e.key === 'Enter' && saveEdit()}
                              className={`w-20 text-[8.5pt] px-1.5 py-0.5 rounded bg-black/60 outline-none transition-colors ${
                                isDirty ? 'border border-amber-400 text-amber-300 ring-1 ring-amber-400/40' : 'border border-cyan-400 text-cyan-300'
                              }`}
                            />
                            <button onClick={saveEdit} disabled={saving}
                              title="Save (Enter)"
                              className="text-emerald-400 hover:text-emerald-300 disabled:opacity-50">
                              {saving ? <Loader2 size={10} className="animate-spin" /> : <Save size={10} />}
                            </button>
                            <button onClick={cancelEdit} title="Cancel (Esc)" className="text-gray-500 hover:text-gray-300">
                              <X size={10} />
                            </button>
                          </div>
                        ) : isJustSaved ? (
                          <span className="font-bold text-emerald-400 flex items-center gap-1 text-[9pt] animate-pulse">
                            {String(v)} <CheckCircle2 size={10} className="text-emerald-400" />
                          </span>
                        ) : (
                          <span className="font-bold text-cyan-300 group-hover:text-cyan-200 flex items-center gap-1 text-[9pt]">
                            {String(v)}
                            <Edit3 size={9} className="opacity-0 group-hover:opacity-60 transition-opacity" />
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* ── Batched Questions Card ── */}
            {qs.length > 0 && !allDone && (
              <div className="rounded-xl p-4 space-y-3"
                style={{ background: 'linear-gradient(135deg,rgba(30,27,75,0.45),rgba(17,24,39,0.55))', border: '1px solid rgba(129,140,248,0.35)' }}>
                {/* Header + progress */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[10pt] text-indigo-300 uppercase tracking-wider font-mono flex items-center gap-1.5">
                      <Sparkles size={12} className="text-indigo-400" />
                      Missing Specifications ({totalCount - answeredCount} remaining)
                    </span>
                    <span className="text-[8.5pt] font-mono text-gray-500">{pct}% done</span>
                  </div>
                  {/* progress bar */}
                  <div className="w-full h-1 rounded-full bg-white/10 overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%`, background: pct === 100 ? '#10b981' : '#6366f1' }} />
                  </div>
                </div>

                <form onSubmit={handleBatchSubmit} className="space-y-3">
                  {qs.map((q) => (
                    <FieldInput
                      key={q.field}
                      q={q}
                      value={formValues[q.field] ?? ''}
                      error={formErrors[q.field]}
                      onChange={val => {
                        setFormValues(prev => ({ ...prev, [q.field]: val }));
                        setFormErrors(prev => { const n={...prev}; delete n[q.field]; return n; });
                      }}
                    />
                  ))}

                  <button type="submit" disabled={submitting}
                    className="w-full mt-1 py-2.5 text-[10pt] font-mono font-bold uppercase tracking-wider rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                    style={{ background: pct === 100 ? 'rgba(16,185,129,0.85)' : 'rgba(99,102,241,0.85)', color: 'white' }}>
                    {submitting
                      ? <><Loader2 size={13} className="animate-spin" /> Processing...</>
                      : <><ArrowRight size={13} /> {pct === 100 ? 'Submit & Lock Specifications' : 'Submit (defaults fill blanks)'}</>}
                  </button>
                </form>
              </div>
            )}

            {/* ── All specs collected confirmation ── */}
            {allDone && (
              <AssistantBubble>
                <div className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold text-emerald-300 text-[10pt]">All specifications locked ✓</p>
                    <p className="text-gray-400 text-[9.5pt] mt-0.5">Generate your engineering analysis report on the right →</p>
                  </div>
                </div>
              </AssistantBubble>
            )}

          </div>

          {/* ── Chat input bar ── */}
          <form onSubmit={handleChatSubmit}
            className="p-3 shrink-0 flex items-center gap-2"
            style={{ borderTop: '1px solid rgba(255,255,255,0.06)', background: 'rgba(0,0,0,0.25)' }}>
            <input
              ref={inputRef}
              type="text"
              placeholder={allDone
                ? "Type parameter edits, e.g. 'change diameter to 40mm'…"
                : "Describe your part in natural language to auto-fill specs…"}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              disabled={submitting}
              className="flex-1 px-3.5 py-2 text-[9.5pt] font-mono rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-cyan-400 disabled:opacity-50 transition-colors"
            />
            <button type="submit" disabled={!inputValue.trim() || submitting}
              className="px-3 py-2 rounded-xl font-bold transition-all disabled:opacity-30 flex items-center gap-1.5"
              style={{ background: 'rgba(34,211,238,0.9)', color: '#000' }}>
              {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            </button>
          </form>
        </div>

        {/* RIGHT — Engineering Analysis + CAD */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">

          {/* ── DFM / CAD error banner ── */}
          {cadError && (
            <div className="rounded-xl p-4 border border-rose-500/40 bg-rose-950/20 space-y-2">
              <div className="flex items-center gap-2 font-mono font-bold text-[10pt] text-rose-400">
                <TriangleAlert size={14} /> CAD Validation Failed — DFM / Topology Issue
              </div>
              <p className="font-mono text-[9.5pt] leading-relaxed text-rose-300/90">{cadError}</p>
              <p className="text-gray-500 text-[8.5pt]">Edit the highlighted parameters on the left to correct the geometry.</p>
            </div>
          )}

          {/* ── Step 1: Gather specs (right-side summary) ── */}
          {!allDone && (
            <PanelCard icon={FileText} title="Step 1 — Gather Specifications" active>
              <div className="text-center py-5 space-y-3">
                <div className="text-4xl">{meta.icon}</div>
                <p className="font-mono text-[9.5pt] text-gray-400">
                  {Object.keys(params).length > 0
                    ? `${Object.keys(params).length} values extracted. Fill in the remaining ${qs.length} fields on the left.`
                    : 'Type a natural-language description or fill in the form on the left to define your part.'}
                </p>
                {Object.keys(params).length > 0 && qs.length > 0 && (
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[8.5pt] font-mono"
                    style={{ background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)', color: '#a5b4fc' }}>
                    <span>{Object.keys(params).length} fields extracted · {qs.length} still needed</span>
                  </div>
                )}
              </div>
            </PanelCard>
          )}

          {/* ── Step 2: Engineering Analysis Report ── */}
          <PanelCard
            icon={BarChart3}
            title="Step 2 — Engineering Analysis"
            locked={!allDone}
            badge={hasReport ? { text: 'CALCULATED', color: '#34d399' } : undefined}
            action={hasReport && !isApproved ? (
              <button onClick={handleApprove} disabled={approving}
                className="px-3 py-1 text-[9pt] font-mono font-bold tracking-wider rounded transition-all"
                style={{ background: 'rgba(16,185,129,0.2)', border: '1px solid rgba(16,185,129,0.4)', color: '#6ee7b7' }}>
                {approving ? <Loader2 size={11} className="inline animate-spin mr-1" /> : <ShieldCheck size={11} className="inline mr-1" />}
                APPROVE REPORT
              </button>
            ) : isApproved ? (
              <span className="text-[9pt] font-mono px-2 py-0.5 rounded text-emerald-400"
                style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)' }}>
                ✓ APPROVED
              </span>
            ) : null}
          >
            {hasReport ? (
              <div className="space-y-4">
                {/* Safety block */}
                <SafetyBlock safety={report.result?.safety} />

                {/* Calculations grid */}
                {report.result?.calculations?.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-[8.5pt] font-mono font-bold text-gray-500 uppercase tracking-wider">Calculated Values</div>
                    <div className="grid grid-cols-2 gap-2">
                      {report.result.calculations.map((c, i) => (
                        <div key={i} className="p-2.5 rounded-lg space-y-0.5"
                          style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.06)' }}>
                          <div className="text-[8.5pt] font-mono text-gray-500 truncate">{c.name}</div>
                          <div className="text-[11pt] font-mono font-bold text-white">
                            {/* Use c.result (correct key from math_engine) */}
                            {c.result != null ? c.result : c.value}
                            {' '}<span className="text-[9pt] font-normal text-gray-400">{c.unit}</span>
                          </div>
                          {c.formula && (
                            <div className="text-[8pt] text-gray-600 truncate font-mono">{c.formula}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Standards */}
                {report.result?.standards?.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[8.5pt] font-mono font-bold text-gray-500 uppercase tracking-wider">Applied Standards</div>
                    {report.result.standards.map((s, i) => (
                      <div key={i} className="text-[8.5pt] font-mono text-gray-600 flex items-center gap-1.5">
                        <ShieldCheck size={9} className="text-gray-700" /> {s}
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex gap-2 pt-1">
                  <a href={`/api/design/sessions/${id}/download-pdf`} download>
                    <button className="px-3 py-1.5 text-[9pt] font-mono text-gray-400 hover:text-white rounded-lg transition-all flex items-center gap-1"
                      style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)' }}>
                      <Download size={11} /> PDF Report
                    </button>
                  </a>
                </div>
              </div>
            ) : allDone ? (
              <div className="text-center py-6 space-y-3">
                <p className="font-mono text-[9.5pt] text-gray-500">
                  All parameters ready. Click to run engineering formulas using Shigley's & ISO standards.
                </p>
                <button onClick={handleGenerateReport} disabled={genReport}
                  className="px-5 py-2.5 text-[10pt] font-mono font-bold tracking-wider rounded-xl transition-all flex items-center gap-2 mx-auto disabled:opacity-50"
                  style={{ background: 'rgba(34,211,238,0.15)', border: '1px solid rgba(34,211,238,0.4)', color: '#67e8f9' }}>
                  {genReport
                    ? <><Loader2 size={13} className="animate-spin" /> Calculating...</>
                    : <><Calculator size={13} /> GENERATE REPORT</>}
                </button>
              </div>
            ) : (
              <div className="py-5 text-center font-mono text-[9.5pt] text-gray-600 flex items-center justify-center gap-2">
                <Lock size={12} /> Complete specifications on the left first.
              </div>
            )}
          </PanelCard>

          {/* ── Step 3: 3D CAD & Quoting ── */}
          <PanelCard
            icon={Box}
            title="Step 3 — 3D CAD & Quoting Handoff"
            locked={!hasReport && !isApproved}
          >
            {isCadReady ? (
              <div className="space-y-3">
                <div className="rounded-lg p-3 flex items-center gap-3"
                  style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)' }}>
                  <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                  <div>
                    <div className="font-mono font-bold text-[10pt] text-emerald-300">AP242 STEP Solid Verified</div>
                    <div className="font-mono text-[8.5pt] text-gray-500">Watertight manifold · Positive OCC volume · Bounding box validated</div>
                  </div>
                </div>
                {/* OCC measured metrics */}
                {session.cad_result && (
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { label: 'Volume (OCC)', value: session.cad_result.volume?.toFixed(1), unit: 'mm³' },
                      { label: 'Surface Area (OCC)', value: session.cad_result.surface_area?.toFixed(1), unit: 'mm²' },
                    ].map(m => (
                      <div key={m.label} className="p-2.5 rounded-lg"
                        style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.06)' }}>
                        <div className="text-[8.5pt] font-mono text-gray-500">{m.label}</div>
                        <div className="text-[11pt] font-mono font-bold text-white">
                          {m.value} <span className="text-[8.5pt] text-gray-400">{m.unit}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex gap-2 pt-1">
                  <a href={`/api/design/sessions/${id}/download-cad`} download className="flex-1">
                    <button className="w-full px-4 py-2 text-[10pt] font-mono font-bold rounded-xl transition-all flex items-center justify-center gap-2"
                      style={{ background: 'rgba(34,211,238,0.12)', border: '1px solid rgba(34,211,238,0.35)', color: '#67e8f9' }}>
                      <Download size={13} /> DOWNLOAD STEP
                    </button>
                  </a>
                  <button onClick={sendToQuoting}
                    className="flex-1 px-4 py-2 text-[10pt] font-mono font-bold rounded-xl transition-all flex items-center justify-center gap-2"
                    style={{ background: 'rgba(99,102,241,0.2)', border: '1px solid rgba(99,102,241,0.45)', color: '#a5b4fc' }}>
                    <Cog size={13} /> SEND TO QUOTING
                  </button>
                </div>
              </div>
            ) : (isApproved || hasReport) ? (
              <div className="text-center py-6 space-y-3">
                <p className="font-mono text-[9.5pt] text-gray-500">
                  Deterministic OpenCASCADE build — no LLM involved in geometry generation.
                </p>
                <button onClick={handleGenerateCad} disabled={genCad}
                  className="px-5 py-2.5 text-[10pt] font-mono font-bold tracking-wider rounded-xl transition-all flex items-center gap-2 mx-auto disabled:opacity-50"
                  style={{ background: 'rgba(34,211,238,0.15)', border: '1px solid rgba(34,211,238,0.4)', color: '#67e8f9' }}>
                  {genCad
                    ? <><Loader2 size={13} className="animate-spin" /> Building STEP solid...</>
                    : <><Box size={13} /> GENERATE CAD MODEL</>}
                </button>
              </div>
            ) : (
              <div className="py-5 text-center font-mono text-[9.5pt] text-gray-600 flex items-center justify-center gap-2">
                <Lock size={12} /> Generate and approve the analysis report first.
              </div>
            )}
          </PanelCard>

        </div>
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function AssistantBubble({ children }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[94%] rounded-xl px-4 py-3 text-[9.5pt] font-mono leading-relaxed"
        style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
        {children}
      </div>
    </div>
  );
}

function PanelCard({ icon: Icon, title, locked, badge, action, active, children }) {
  return (
    <div className={`rounded-xl overflow-hidden transition-all duration-300 ${locked ? 'opacity-35 pointer-events-none' : ''} ${active ? 'ring-1 ring-indigo-500/30' : ''}`}
      style={{ background: 'linear-gradient(135deg,rgba(255,255,255,0.03),rgba(255,255,255,0.01))', border: '1px solid rgba(255,255,255,0.07)' }}>
      <div className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(0,0,0,0.18)' }}>
        <div className="flex items-center gap-2">
          <Icon size={13} className="text-cyan-400" />
          <span className="text-[10pt] font-bold text-white uppercase tracking-widest" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {title}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {badge && (
            <span className="px-2 py-0.5 text-[8.5pt] font-mono font-bold tracking-wider rounded"
              style={{ color: badge.color, background: badge.color + '18', border: `1px solid ${badge.color}35` }}>
              {badge.text}
            </span>
          )}
          {action}
          {locked && <Lock size={11} className="text-gray-600" />}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function FieldInput({ q, value, error, onChange }) {
  const hint = FIELD_HINTS[q.field];

  return (
    <div className="space-y-1">
      {/* Label row */}
      <label className="flex items-center justify-between text-[9pt] font-mono">
        <span className="text-gray-200 font-semibold">{q.label}</span>
        {q.unit && (
          <span className="text-[8pt] px-1.5 py-0.5 rounded font-mono"
            style={{ background: 'rgba(255,255,255,0.06)', color: '#94a3b8', border: '1px solid rgba(255,255,255,0.1)' }}>
            {q.unit}
          </span>
        )}
      </label>

      {/* Input control */}
      {q.options && q.options.length > 0 ? (
        /* Select chips */
        <div className="flex flex-wrap gap-1.5">
          {q.options.map(opt => {
            const sel = value === opt.value;
            return (
              <button key={opt.value} type="button"
                onClick={() => onChange(opt.value)}
                className={`px-2.5 py-1 text-[8.5pt] font-mono rounded-lg border transition-all ${
                  sel
                    ? 'font-bold'
                    : 'bg-white/5 border-white/10 text-gray-400 hover:text-white hover:bg-white/10'
                }`}
                style={sel ? { background: 'rgba(99,102,241,0.75)', borderColor: 'rgba(129,140,248,0.7)', color: 'white' } : {}}>
                {opt.label || opt.value}
              </button>
            );
          })}
        </div>
      ) : (
        /* Number / text input */
        <div className="relative">
          <input
            type={q.type === 'number' ? 'number' : 'text'}
            step="any"
            placeholder={q.default_value != null ? `Default: ${q.default_value}` : q.question}
            value={value}
            onChange={e => onChange(e.target.value)}
            className={`w-full px-3 py-2 text-[9.5pt] font-mono rounded-lg bg-black/40 text-white focus:outline-none transition-colors ${
              error ? 'border-rose-500' : value ? 'border-indigo-400/60' : 'border-white/10'
            }`}
            style={{ border: `1px solid ${error ? '#f43f5e' : value ? 'rgba(99,102,241,0.5)' : 'rgba(255,255,255,0.1)'}` }}
          />
          {/* Filled indicator dot */}
          {value && !error && (
            <span className="absolute right-2.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-emerald-400" />
          )}
        </div>
      )}

      {/* Hint */}
      {hint && !error && (
        <div className="flex items-center gap-1 text-[8pt] font-mono text-gray-600">
          <Info size={8} /> {hint}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-1 text-[8pt] font-mono text-rose-400">
          <AlertTriangle size={9} /> {error}
        </div>
      )}
    </div>
  );
}

function SafetyBlock({ safety }) {
  if (!safety) return null;
  const safe = safety.is_safe !== false;
  return (
    <div className="rounded-lg p-3 space-y-2"
      style={{
        background: safe ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)',
        border: `1px solid ${safe ? 'rgba(16,185,129,0.22)' : 'rgba(239,68,68,0.22)'}`,
      }}>
      <div className="flex items-center gap-6">
        {safety.fos_actual != null && (
          <div>
            <div className="text-[8.5pt] font-mono text-gray-500 uppercase">Actual FOS</div>
            <div className={`text-xl font-bold font-mono ${safe ? 'text-emerald-400' : 'text-red-400'}`}>
              {safety.fos_actual}
            </div>
          </div>
        )}
        {safety.fos_required != null && (
          <div>
            <div className="text-[8.5pt] font-mono text-gray-500 uppercase">Required</div>
            <div className="text-xl font-bold font-mono text-white">{safety.fos_required}</div>
          </div>
        )}
        <div className="ml-auto">
          <span className={`px-2 py-0.5 text-[9pt] font-mono font-bold tracking-wider rounded ${safe ? 'text-emerald-400' : 'text-red-400'}`}
            style={{ background: safe ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)', border: `1px solid ${safe ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.35)'}` }}>
            {safe ? 'SAFE' : 'CRITICAL'}
          </span>
        </div>
      </div>
      {safety.warnings?.map((w, i) => (
        <div key={i} className="flex items-start gap-2 text-[9pt] font-mono text-amber-400">
          <AlertTriangle size={11} className="shrink-0 mt-0.5" /> {w}
        </div>
      ))}
      {safety.recommendations?.map((r, i) => (
        <div key={i} className="flex items-start gap-2 text-[8.5pt] font-mono text-gray-500">
          <Info size={9} className="shrink-0 mt-0.5" /> {r}
        </div>
      ))}
    </div>
  );
}
