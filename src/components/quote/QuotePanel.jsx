import React, { useState, useEffect } from 'react';
import {
    Wrench, ChevronDown, Plus, X,
    RefreshCw, AlertCircle, CheckCircle, Zap, FileText,
    User, Building, IndianRupee, Layers
} from 'lucide-react';

const API = '/api';

/* ─── Helpers ────────────────────────────────────────────────────────────── */
const fmt = (n, dec = 0) =>
    typeof n === 'number'
        ? n.toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec })
        : '—';

/* ─── LineItem row ───────────────────────────────────────────────────────── */
function LineItem({ label, value, highlight, large }) {
    return (
        <div className={`flex items-center justify-between ${large ? 'py-3' : 'py-1.5'}
            border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] px-1.5 rounded transition-colors`}>
            <span className={`${large ? 'text-[13px] font-medium' : 'text-[11px]'} text-gray-400`}>{label}</span>
            <span className={`font-mono ${large ? 'text-sm font-bold tracking-wide' : 'text-[12px] font-semibold'}
                ${highlight ? 'text-cyan-300 drop-shadow-[0_0_8px_rgba(103,232,249,0.5)]' : 'text-gray-100'}`}>
                {value}
            </span>
        </div>
    );
}

/* ─── Select dropdown ────────────────────────────────────────────────────── */
function Select({ label, value, onChange, options, disabled }) {
    return (
        <div className="space-y-1">
            <label className="text-[10px] text-gray-500 uppercase tracking-widest">{label}</label>
            <div className="relative group">
                <select
                    value={value}
                    onChange={e => onChange(e.target.value)}
                    disabled={disabled || options.length === 0}
                    className="w-full bg-gray-800/70 border border-gray-700/60 text-gray-200
                        text-[11px] rounded-lg px-3 py-2 appearance-none focus:outline-none
                        focus:border-cyan-500/50 cursor-pointer font-mono
                        group-hover:border-gray-600 transition-colors
                        disabled:opacity-40 disabled:cursor-not-allowed"
                >
                    {options.length === 0
                        ? <option>Loading…</option>
                        : options.map(o => (
                            <option key={o.value} value={o.value} className="bg-gray-900">{o.label}</option>
                        ))
                    }
                </select>
                <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2
                    text-gray-500 pointer-events-none group-hover:text-cyan-400 transition-colors" />
            </div>
        </div>
    );
}

/* ─── Text Input ─────────────────────────────────────────────────────────── */
function TextInput({ label, value, onChange, placeholder, icon: Icon, type = "text", min, max, step }) {
    return (
        <div className="space-y-1">
            <label className="text-[10px] text-gray-500 uppercase tracking-widest flex items-center justify-between">
                {label}
                {type === 'range' && <span className="text-cyan-400 font-mono">{value}%</span>}
            </label>
            <div className="relative flex items-center">
                {Icon && type !== 'range' && <Icon size={12} className="absolute left-3 text-gray-600" />}
                <input
                    type={type}
                    min={min}
                    max={max}
                    step={step}
                    value={value}
                    onChange={e => onChange(type === 'range' || type === 'number' ? parseFloat(e.target.value) : e.target.value)}
                    placeholder={placeholder}
                    className={`w-full bg-gray-800/70 text-gray-200 text-[11px] rounded-lg
                        ${type !== 'range' ? `border border-gray-700/60 py-2 focus:outline-none focus:border-cyan-500/50 hover:border-gray-600 ${Icon ? 'pl-8 pr-3' : 'px-3'}` : 'accent-cyan-500'}
                        font-mono placeholder:text-gray-700 transition-colors cursor-pointer`}
                />
            </div>
        </div>
    );
}

/* ─── MultiSelect with Chips ─────────────────────────────────────────────── */
function MultiSelect({ label, selectedIds = [], onChange, options = [], disabled }) {
    
    const unselectedOptions = options.filter(o => !selectedIds.includes(o.value));
    
    return (
        <div className="space-y-2">
            <label className="text-[10px] text-gray-500 uppercase tracking-widest">{label}</label>
            
            {/* Chips Area */}
            {selectedIds.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-2">
                    {selectedIds.map(id => {
                        const opt = options.find(o => o.value === id);
                        return (
                            <div key={id} className="flex items-center gap-1.5 bg-cyan-900/30 border border-cyan-500/30 text-cyan-300 text-[10px] px-2 py-1 rounded-full font-medium">
                                <span>{opt ? opt.label : id}</span>
                                <button
                                    onClick={() => onChange(selectedIds.filter(x => x !== id))}
                                    disabled={disabled}
                                    className="hover:text-cyan-100 hover:bg-cyan-500/20 rounded-full p-0.5 transition-colors"
                                >
                                    <X size={10} />
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}
            
            {/* Add Dropdown */}
            <div className="relative group">
                <select
                    value=""
                    onChange={e => {
                        if (e.target.value) {
                            onChange([...selectedIds, e.target.value]);
                        }
                    }}
                    disabled={disabled || unselectedOptions.length === 0}
                    className="w-full bg-gray-800/70 border border-gray-700/60 text-gray-400
                        text-[11px] rounded-lg px-3 py-2 appearance-none focus:outline-none
                        focus:border-cyan-500/50 cursor-pointer font-mono
                        group-hover:border-gray-600 transition-colors
                        disabled:opacity-40 disabled:cursor-not-allowed"
                >
                    <option value="" disabled>
                        {unselectedOptions.length === 0 ? 'No more options available' : '+ Add an option...'}
                    </option>
                    {unselectedOptions.map(o => (
                        <option key={o.value} value={o.value} className="bg-gray-900 text-gray-200">{o.label}</option>
                    ))}
                </select>
                <Plus size={14} className="absolute right-3 top-1/2 -translate-y-1/2
                    text-gray-500 pointer-events-none group-hover:text-cyan-400 transition-colors" />
            </div>
            
            {selectedIds.length >= 5 && label.includes('Process') && (
                <p className="text-[9px] text-amber-400/80 font-mono mt-1 flex items-center gap-1">
                    <AlertCircle size={9} /> ≥5 processes forces "Very Complex" tier.
                </p>
            )}
        </div>
    );
}

/* ─── Main component ─────────────────────────────────────────────────────── */
export default function QuotePanel({ geometry, fileMetrics, captureScreenshot }) {
    // ── Catalogue state
    const [materials, setMaterials] = useState({});
    const [processes, setProcesses] = useState({});
    const [tolerances, setTolerances] = useState({});
    const [catLoading, setCatLoading] = useState(true);

    // ── Pricing state
    const [prices, setPrices] = useState(null);
    const [priceSource, setPriceSource] = useState('');
    const [exchangeRate, setExchangeRate] = useState(null);
    const [priceLoading, setPriceLoading] = useState(false);

    // ── Selection state
    const [materialId, setMaterialId] = useState('aluminum_6061');
    const [processIds, setProcessIds] = useState(['cnc_milling_3ax']);
    const [surfaceTreatmentIds, setSurfaceTreatmentIds] = useState([]);
    const [toleranceId, setToleranceId] = useState('standard');
    const [quantity, setQuantity] = useState(1);
    const [profitMarginPct, setProfitMarginPct] = useState(22);

    // ── Client info
    const [clientName, setClientName] = useState('');
    const [clientCompany, setClientCompany] = useState('');
    const [hsnCode, setHsnCode] = useState('84669310'); // Default HSN code

    // ── Output state
    const [quote, setQuote] = useState(null);
    const [loading, setLoading] = useState(false);
    const [pdfLoading, setPdfLoading] = useState(false);
    const [error, setError] = useState('');

    const resultRef = React.useRef(null);

    // ── Auto-fill selections from PDF analysis if available
    useEffect(() => {
        if (fileMetrics?.source === 'pdf') {
            if (fileMetrics.materialId) setMaterialId(fileMetrics.materialId);
            if (fileMetrics.processId) setProcessIds([fileMetrics.processId]);
            if (fileMetrics.toleranceId) setToleranceId(fileMetrics.toleranceId);
            // Auto-fill client info extracted from PDF (admin can still edit)
            if (fileMetrics.clientName) setClientName(fileMetrics.clientName);
            if (fileMetrics.clientCompany) setClientCompany(fileMetrics.clientCompany);
            if (fileMetrics.hsnCode) setHsnCode(fileMetrics.hsnCode);
        }
    }, [fileMetrics]);

    useEffect(() => {
        if (quote && resultRef.current) {
            // Scroll down smoothly instantly when quote block appears
            setTimeout(() => {
                resultRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        }
    }, [quote]);

    // ── Load catalogue + prices on mount
    useEffect(() => {
        let cancelled = false;
        const loadAll = async () => {
            setCatLoading(true);
            try {
                const [matRes, procRes, tolRes] = await Promise.all([
                    fetch(`${API}/materials`),
                    fetch(`${API}/processes`),
                    fetch(`${API}/tolerances`),
                ]);
                const [matData, procData, tolData] = await Promise.all([
                    matRes.json(), procRes.json(), tolRes.json(),
                ]);
                if (cancelled) return;
                setMaterials(matData);
                setProcesses(procData);
                setTolerances(tolData);
            } catch {
                if (cancelled) return;
                setMaterials({
                    aluminum_6061: { name: 'Aluminum 6061' },
                    stainless_steel_304: { name: 'Stainless Steel 304' },
                    mild_steel: { name: 'Mild Steel (EN-8)' },
                    titanium_ti6al4v: { name: 'Titanium Ti-6Al-4V' },
                    copper: { name: 'Copper (C101)' },
                    brass_360: { name: 'Brass (C360)' },
                    inconel_718: { name: 'Inconel 718' },
                    aluminum_7075: { name: 'Aluminum 7075-T6' },
                    stainless_steel_316l: { name: 'SS 316L' },
                    tool_steel_d2: { name: 'Tool Steel D2' },
                    pla_plastic: { name: 'PLA (3D Print)' },
                    abs_plastic: { name: 'ABS (3D Print)' },
                });
                setProcesses({
                    cnc_turning: { name: 'CNC Turning' },
                    cnc_milling_2ax: { name: 'CNC Milling (2-Axis)' },
                    cnc_milling_3ax: { name: 'CNC Milling (3-Axis)' },
                    cnc_milling_5ax: { name: 'CNC Milling (5-Axis)' },
                    fdm_3d_print: { name: '3D Printing (FDM)' },
                    edm_wire: { name: 'EDM Wire Cutting' },
                    laser_cutting: { name: 'Laser Cutting' },
                });
                setTolerances({
                    rough: { label: 'Rough (±1.0 mm)' },
                    standard: { label: 'Standard (±0.5 mm)' },
                    precision: { label: 'Precision (±0.1 mm)' },
                    high: { label: 'High Precision (±0.025 mm)' },
                    ultra: { label: 'Ultra Precision (±0.01 mm)' },
                });
            } finally {
                if (!cancelled) setCatLoading(false);
            }
        };
        loadAll();
        loadPrices();
        return () => { cancelled = true; };
    }, []);

    const loadPrices = async () => {
        setPriceLoading(true);
        try {
            const r = await fetch(`${API}/prices`);
            if (!r.ok) throw new Error('Price fetch failed');
            const d = await r.json();
            setPrices(d.prices_inr || {});
            setPriceSource(d.price_source || 'fallback');
            setExchangeRate(d.exchange_rate || null);
        } catch {
            setPriceSource('error');
        } finally {
            setPriceLoading(false);
        }
    };

    // ── Generate quote
    const generateQuote = async () => {
        if (!geometry) {
            setError('Please upload a STEP file or PDF drawing first.');
            return;
        }
        setLoading(true);
        setError('');
        setQuote(null);
        try {
            const qty = Math.max(1, Math.min(10000, parseInt(String(quantity), 10) || 1));

            let screenshot = null;
            if (captureScreenshot) {
                try { screenshot = captureScreenshot(); } catch { }
            }

            const resp = await fetch(`${API}/quote`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    geometry,
                    material_id: materialId,
                    process_ids: processIds,
                    surface_treatment_ids: surfaceTreatmentIds,
                    profit_margin_pct: profitMarginPct,
                    tolerance_id: toleranceId,
                    quantity: qty,
                    client_name: clientName,
                    client_company: clientCompany,
                    hsn_code: hsnCode,
                    source_filename: fileMetrics?.fileName || '',
                    screenshot,
                }),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(err.detail || `Server error ${resp.status}`);
            }
            setQuote(await resp.json());
        } catch (e) {
            setError(e.message || 'Network error — is the backend running?');
        } finally {
            setLoading(false);
        }
    };

    // ── Download PDF
    const downloadPdf = async () => {
        if (!geometry) return;
        setPdfLoading(true);
        setError('');
        try {
            const qty = Math.max(1, Math.min(10000, parseInt(String(quantity), 10) || 1));

            let screenshot = null;
            if (captureScreenshot) {
                try { screenshot = captureScreenshot(); } catch { }
            }

            const resp = await fetch(`${API}/quote/pdf`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    geometry,
                    material_id: materialId,
                    process_ids: processIds,
                    surface_treatment_ids: surfaceTreatmentIds,
                    profit_margin_pct: profitMarginPct,
                    tolerance_id: toleranceId,
                    quantity: qty,
                    client_name: clientName,
                    client_company: clientCompany,
                    hsn_code: hsnCode,
                    source_filename: fileMetrics?.fileName || '',
                    screenshot,
                }),
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: 'PDF generation failed' }));
                throw new Error(err.detail || `Server error ${resp.status}`);
            }
            const blob = await resp.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `AccuDesign_Quote_${Date.now()}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (e) {
            setError(e.message || 'PDF generation failed');
        } finally {
            setPdfLoading(false);
        }
    };

    // ── Derived values
    const matOptions = Object.entries(materials).map(([k, v]) => ({ value: k, label: v.name }));
    const procOptions = Object.entries(processes).map(([k, v]) => ({ value: k, label: v.name }));
    const tolOptions = Object.entries(tolerances).map(([k, v]) => ({ value: k, label: v.label }));
    
    const surfaceOptions = [
        { value: 'anodize_clear', label: 'Anodize (Clear)' },
        { value: 'anodize_black', label: 'Anodize (Black)' },
        { value: 'powder_coat', label: 'Powder Coating' },
        { value: 'heat_treatment', label: 'Heat Treatment' },
        { value: 'bead_blast', label: 'Bead Blasting' },
        { value: 'passivation', label: 'Passivation' },
        { value: 'electroless_nickel', label: 'Electroless Nickel' },
    ];

    const livePriceInr = prices?.[materialId];
    const mat = materials[materialId];

    const sourceColor = {
        metals_dev: 'text-green-400',
        world_bank: 'text-blue-400',
        fallback: 'text-amber-400',
        error: 'text-red-400',
    }[priceSource] || 'text-gray-500';

    const sourceLabel = {
        metals_dev: '● LME Live',
        world_bank: '● World Bank',
        fallback: '◐ Estimated',
        error: '✕ Offline',
    }[priceSource] || '…';

    return (
        <div className="space-y-4">

            {/* ── Metal price banner (INR) ─────────────────────────────────── */}
            <div className="rounded-2xl bg-gradient-to-br from-white/[0.05] to-white/[0.01]
                border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.3)] backdrop-blur-md p-4
                transition-all hover:border-white/[0.15]">
                <div className="flex items-center justify-between mb-3 border-b border-white/[0.05] pb-2">
                    <div className="flex items-center gap-1.5">
                        <IndianRupee size={12} className="text-cyan-400" />
                        <span className="text-[10px] font-bold text-gray-300 uppercase tracking-widest">
                            Live Metal Prices (INR)
                        </span>
                    </div>
                    <button onClick={loadPrices} disabled={priceLoading}
                        className="text-gray-500 hover:text-cyan-400 transition-colors" title="Refresh prices">
                        <RefreshCw size={11} className={priceLoading ? 'animate-spin' : ''} />
                    </button>
                </div>
                {prices ? (
                    <div className="space-y-1">
                        <div className="flex justify-between items-center">
                            <span className="text-[10px] text-gray-500">{mat?.name || materialId}</span>
                            <span className="text-[11px] font-mono text-cyan-300 font-bold">
                                {livePriceInr != null ? `₹${fmt(livePriceInr)}/kg` : '—'}
                            </span>
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-[10px] text-gray-600">
                                {exchangeRate ? `USD→INR: ₹${exchangeRate.toFixed(2)}` : ''}
                            </span>
                            <span className={`text-[9px] font-mono ${sourceColor}`}>{sourceLabel}</span>
                        </div>
                    </div>
                ) : (
                    <p className="text-[10px] text-gray-600">
                        {priceLoading ? 'Fetching prices…' : 'Backend offline — start the FastAPI server'}
                    </p>
                )}
            </div>

            {/* ── Client Info ──────────────────────────────────────────────── */}
            <div className="rounded-2xl bg-gradient-to-br from-white/[0.05] to-white/[0.01]
                border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.3)] backdrop-blur-md p-4 space-y-3">
                <div className="flex items-center gap-2 border-b border-white/[0.05] pb-2">
                    <User size={14} className="text-cyan-400" />
                    <span className="text-[11px] font-bold text-gray-200 uppercase tracking-widest">
                        Client Details
                    </span>
                </div>
                <TextInput label="Client Name" value={clientName} onChange={setClientName}
                    placeholder="e.g. Vishal Jadhav" icon={User} />
                <TextInput label="Company" value={clientCompany} onChange={setClientCompany}
                    placeholder="e.g. Aerochamp Aviation Pvt. Ltd." icon={Building} />
                <TextInput label="HSN/SAC Code" value={hsnCode} onChange={setHsnCode}
                    placeholder="e.g. 84669310" icon={FileText} />
            </div>

            {/* ── PDF auto-fill indicator ─────────────────────────────────── */}
            {fileMetrics?.source === 'pdf' && (
                <div className="rounded-xl bg-purple-500/8 border border-purple-500/20 px-3 py-2.5
                    flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse flex-shrink-0"
                        style={{ boxShadow: '0 0 6px rgba(168,85,247,0.8)' }} />
                    <div>
                        <p className="text-[10px] text-purple-300 font-mono font-bold">
                            AI Auto-Fill Active
                        </p>
                        <p className="text-[9px] text-purple-400/70 font-mono">
                            Material, process & tolerance pre-selected from PDF analysis.
                            {fileMetrics.partName && ` Part: ${fileMetrics.partName}`}
                        </p>
                    </div>
                </div>
            )}

            {/* ── Configuration selectors ─────────────────────────────────── */}
            <div className="rounded-2xl bg-gradient-to-br from-white/[0.05] to-white/[0.01]
                border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.3)] backdrop-blur-md p-4 space-y-4">
                <div className="flex items-center gap-2 border-b border-white/[0.05] pb-2">
                    <Wrench size={14} className="text-cyan-400 drop-shadow-[0_0_8px_rgba(103,232,249,0.8)]" />
                    <span className="text-[11px] font-bold text-gray-200 uppercase tracking-widest">
                        Configuration
                    </span>
                    {catLoading && <RefreshCw size={10} className="ml-auto text-gray-600 animate-spin" />}
                </div>

                <Select label="Material" value={materialId} onChange={setMaterialId}
                    options={matOptions} disabled={catLoading} />
                <MultiSelect label="Manufacturing Processes" selectedIds={processIds} onChange={setProcessIds}
                    options={procOptions} disabled={catLoading} />
                <MultiSelect label="Surface Treatment" selectedIds={surfaceTreatmentIds} onChange={setSurfaceTreatmentIds}
                    options={surfaceOptions} disabled={catLoading} />
                <Select label="Tolerance" value={toleranceId} onChange={setToleranceId}
                    options={tolOptions} disabled={catLoading} />
                    
                <TextInput 
                    label="Profit Margin" 
                    type="range" 
                    min={15} max={30} step={1}
                    value={profitMarginPct} 
                    onChange={setProfitMarginPct} 
                />

                {/* Quantity */}
                <div className="space-y-1">
                    <label className="text-[10px] text-gray-500 uppercase tracking-widest">Quantity</label>
                    <input
                        type="number" min="1" max="10000"
                        value={quantity}
                        onChange={e => {
                            const v = parseInt(e.target.value, 10);
                            setQuantity(isNaN(v) ? 1 : Math.max(1, Math.min(10000, v)));
                        }}
                        className="w-full bg-gray-800/70 border border-gray-700/60 text-gray-200
                            text-[11px] rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500/50 font-mono"
                    />
                </div>

                {/* Generate button */}
                <button
                    onClick={generateQuote}
                    disabled={loading || !geometry}
                    className={`w-full py-3 mt-1 rounded-xl text-[12px] font-bold tracking-wider
                        transition-all duration-300 flex items-center justify-center gap-2
                        ${geometry
                            ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 shadow-[0_0_20px_rgba(34,211,238,0.3)] hover:shadow-[0_0_30px_rgba(34,211,238,0.5)] hover:scale-[1.02] active:scale-[0.98]'
                            : 'bg-white/5 text-gray-500 cursor-not-allowed border border-white/10'}`}
                >
                    {loading
                        ? <><RefreshCw size={14} className="animate-spin" /> Computing…</>
                        : <><Zap size={14} className="drop-shadow-md" />
                            {geometry ? 'Generate Quote (₹)' : 'Upload STEP/PDF First'}</>
                    }
                </button>

                {/* Error */}
                {error && (
                    <div className="flex items-start gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                        <AlertCircle size={12} className="text-red-400 mt-0.5 flex-shrink-0" />
                        <p className="text-[11px] text-red-400 leading-relaxed">{error}</p>
                    </div>
                )}
            </div>

            {/* ── Quote result (INR) ──────────────────────────────────────── */}
            {quote && (
                <div ref={resultRef} className="rounded-2xl bg-gradient-to-b from-cyan-900/30 to-black/60
                    border border-cyan-500/30 shadow-[0_0_30px_rgba(34,211,238,0.15)]
                    backdrop-blur-xl p-4 space-y-3">

                    {/* Header */}
                    <div className="flex items-center gap-2 border-b border-cyan-500/20 pb-2">
                        <CheckCircle size={15} className="text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.8)]" />
                        <span className="text-[11px] font-bold text-white uppercase tracking-widest">
                            Quote Result (₹ INR)
                        </span>
                        <span className={`ml-auto text-[9px] font-mono font-medium ${quote.price_source === 'metals_dev' ? 'text-green-300' :
                                quote.price_source === 'world_bank' ? 'text-blue-300' : 'text-amber-300'}`}>
                            {quote.price_source === 'metals_dev' ? '● LME Live' :
                                quote.price_source === 'world_bank' ? '● World Bank' : '◐ Estimated'}
                        </span>
                    </div>

                    {/* Quote Number */}
                    {quote.quote_number && (
                        <div className="bg-gray-900/70 rounded-lg px-3 py-2">
                            <p className="text-[9px] text-gray-500 uppercase tracking-widest">Quotation No.</p>
                            <p className="text-[12px] font-mono text-cyan-300 font-bold">{quote.quote_number}</p>
                        </div>
                    )}

                    {/* Cost breakdown (INR) */}
                    <div className="bg-gray-900/50 rounded-lg p-2 space-y-0.5">
                        <LineItem label="Material Cost" value={`₹${fmt(quote.breakdown?.material_cost)}`} />
                        <LineItem label="Machining Cost" value={`₹${fmt(quote.breakdown?.machining_cost)}`} />
                        {(quote.breakdown?.drilling_cost > 0) &&
                            <LineItem label="Drilling Surcharge" value={`₹${fmt(quote.breakdown.drilling_cost)}`} />}
                        <LineItem label="Setup (amort.)" value={`₹${fmt(quote.breakdown?.setup_cost)}`} />
                        <LineItem label="Overhead (18%)" value={`₹${fmt(quote.breakdown?.overhead)}`} />
                        <LineItem label="Profit Margin" value={`₹${fmt(quote.breakdown?.profit_margin)}`} />
                    </div>

                    {/* Totals (INR) */}
                    <div className="border-t border-gray-700/60 pt-2 space-y-0.5">
                        <LineItem label="Unit Price" value={`₹${fmt(quote.unit_price)}`} />
                        {quote.discount_pct > 0 &&
                            <LineItem
                                label={`Qty Discount (${quote.discount_pct}%)`}
                                value={`−₹${fmt((quote.unit_price || 0) - (quote.unit_price_discounted || 0))}`}
                            />}
                        <LineItem
                            label={`Order Total (×${quote.quantity})`}
                            value={`₹${fmt(quote.order_total)}`}
                        />
                    </div>

                    {/* GST */}
                    <div className="border-t border-gray-700/40 pt-2 space-y-0.5">
                        <LineItem label="SGST (9%)" value={`₹${fmt(quote.sgst)}`} />
                        <LineItem label="CGST (9%)" value={`₹${fmt(quote.cgst)}`} />
                        <LineItem
                            label="Grand Total (incl. GST)"
                            value={`₹${fmt(quote.grand_total)}`}
                            highlight large
                        />
                    </div>

                    {/* Part info */}
                    <div className="border-t border-gray-700/40 pt-2 space-y-0.5">
                        <LineItem label="Part Mass" value={`${fmt(quote.mass_kg, 3)} kg`} />
                        <LineItem label="Machining Time" value={`${fmt(quote.machining_hours, 2)} hr`} />
                        <LineItem label="Complexity" value={quote.complexity || '—'} />
                        {(quote.holes_count > 0) &&
                            <LineItem label="Holes Detected" value={String(quote.holes_count)} />}
                        <LineItem label="Metal Price" value={`₹${fmt(quote.metal_price_inr_kg)}/kg`} />
                        <LineItem label="Machine Rate" value={`₹${fmt(quote.machine_rate_inr_hr)}/hr`} />
                        <LineItem label="Exchange Rate" value={`₹${fmt(quote.exchange_rate, 2)}/USD`} />
                    </div>

                    {/* Download PDF */}
                    <button
                        onClick={downloadPdf}
                        disabled={pdfLoading}
                        className="w-full py-2.5 rounded-xl text-[12px] font-bold tracking-wider
                            transition-all duration-300 flex items-center justify-center gap-2
                            border border-cyan-500/30 bg-white/5 text-cyan-300
                            hover:bg-cyan-500/10 hover:border-cyan-400 active:scale-[0.98]
                            disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {pdfLoading
                            ? <><RefreshCw size={14} className="animate-spin" /> Generating PDF…</>
                            : <><FileText size={14} /> Download ACCU AI Quote (PDF)</>}
                    </button>
                </div>
            )}
        </div>
    );
}
