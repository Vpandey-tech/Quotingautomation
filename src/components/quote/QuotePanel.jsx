import React, { useState, useEffect } from 'react';
import {
    Wrench, ChevronDown, Plus, X,
    RefreshCw, AlertCircle, CheckCircle, Zap, FileText,
    User, Building, IndianRupee, Layers, Scale, ToggleLeft,
    Minus, Eye, CircleDot, ShieldCheck
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
        <div className={`flex items-center justify-between gap-2 ${large ? 'py-3' : 'py-1.5'}
            border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] px-1.5 rounded transition-colors overflow-hidden`}>
            <span className={`${large ? 'text-[13px] font-medium' : 'text-[11px]'} text-gray-400 shrink-0`}>{label}</span>
            <span className={`font-mono text-right truncate min-w-0 ${large ? 'text-sm font-bold tracking-wide' : 'text-[11px] font-semibold'}
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

    // ── Senior Phase 5: New controls
    const [includeSetupCost, setIncludeSetupCost] = useState(true);
    const [holeCountOverride, setHoleCountOverride] = useState(-1); // -1 = auto
    const [stockType, setStockType] = useState('round_bar');
    const [materialEstimate, setMaterialEstimate] = useState(null);
    const [estimateLoading, setEstimateLoading] = useState(false);
    const [aiValidation, setAiValidation] = useState(null);
    const [aiValidating, setAiValidating] = useState(false);

    // ── Client info
    const [clientName, setClientName] = useState('');
    const [clientCompany, setClientCompany] = useState('');
    const [hsnCode, setHsnCode] = useState('84669310'); // Default HSN code

    // ── Output state
    const [quote, setQuote] = useState(null);
    const [multiQuote, setMultiQuote] = useState(null);
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
        if ((quote || multiQuote) && resultRef.current) {
            // Scroll down smoothly instantly when quote block appears
            setTimeout(() => {
                resultRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }, [quote, multiQuote]);

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

    // ── Fetch material estimate (pre-quote verification — Senior Req)
    const fetchMaterialEstimate = async () => {
        if (!geometry) return;
        setEstimateLoading(true);
        try {
            const bb = geometry.boundingBox || {};
            const resp = await fetch(`${API}/material-estimate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    size_x: parseFloat(bb.sizeX) || 1,
                    size_y: parseFloat(bb.sizeY) || 1,
                    size_z: parseFloat(bb.sizeZ) || 1,
                    material_id: materialId,
                    quantity: Math.max(1, quantity),
                    stock_type: stockType,
                    part_volume_mm3: parseFloat(geometry.volume) || 0,
                }),
            });
            if (resp.ok) {
                setMaterialEstimate(await resp.json());
            }
        } catch { /* silent */ }
        finally { setEstimateLoading(false); }
    };

    // Auto-refresh material estimate when key params change
    useEffect(() => {
        if (geometry) fetchMaterialEstimate();
        setAiValidation(null); // Reset AI validation on param change
    }, [geometry, materialId, stockType, quantity]);

    // ── Validate with Gemini AI (on-demand only)
    const validateWithAI = async () => {
        if (!materialEstimate) return;
        setAiValidating(true);
        setAiValidation(null);
        try {
            const bb = geometry?.boundingBox || {};
            const resp = await fetch(`${API}/validate-material`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    size_x: parseFloat(bb.sizeX) || 1,
                    size_y: parseFloat(bb.sizeY) || 1,
                    size_z: parseFloat(bb.sizeZ) || 1,
                    material_id: materialId,
                    quantity: Math.max(1, quantity),
                    stock_type: stockType,
                    part_volume_mm3: parseFloat(geometry?.volume) || 0,
                    our_stock_size: materialEstimate.standard_diameter_mm
                        ? `Ø${materialEstimate.standard_diameter_mm}mm`
                        : materialEstimate.standard_thickness_mm
                        ? `${materialEstimate.standard_thickness_mm}×${materialEstimate.standard_width_mm}mm`
                        : '',
                    our_envelope_vol: materialEstimate.envelope_volume_mm3 || 0,
                    our_gross_weight: materialEstimate.gross_weight_per_part_kg || 0,
                    our_batch_weight: materialEstimate.total_batch_weight_kg || 0,
                    our_utilization: materialEstimate.material_utilization_pct || 0,
                    our_material_cost: materialEstimate.estimated_material_cost_inr || 0,
                }),
            });
            if (resp.ok) {
                setAiValidation(await resp.json());
            } else {
                setAiValidation({ success: false, error: 'Validation failed' });
            }
        } catch {
            setAiValidation({ success: false, error: 'Network error' });
        } finally {
            setAiValidating(false);
        }
    };

    // ── Generate quote
    const generateQuote = async () => {
        if (!geometry && !fileMetrics?.allParts) {
            setError('Please upload a STEP file or PDF drawing first.');
            return;
        }
        setLoading(true);
        setError('');
        setQuote(null);
        setMultiQuote(null);
        try {
            const qty = Math.max(1, Math.min(10000, parseInt(String(quantity), 10) || 1));

            let screenshot = null;
            if (captureScreenshot) {
                try { screenshot = captureScreenshot(); } catch { }
            }

            // If it's a PDF with multiple parts (BOM), generate tabular quote
            if (fileMetrics?.source === 'pdf' && fileMetrics?.allParts?.length > 1) {
                const results = await Promise.all(fileMetrics.allParts.map(async (part, index) => {
                    const isBuyout = (part.part_category || '').toLowerCase().includes('buyout');
                    const partGeometry = {
                        volume: parseFloat(part.estimated_volume_mm3) || 0,
                        surfaceArea: parseFloat(part.estimated_surface_area_mm2) || 0,
                        boundingBox: {
                            sizeX: parseFloat(part.bounding_box?.sizeX) || 0,
                            sizeY: parseFloat(part.bounding_box?.sizeY) || 0,
                            sizeZ: parseFloat(part.bounding_box?.sizeZ) || 0,
                        },
                        holes: part.holes || [],
                        complexity: { tier: 'Moderate', score: 150 },
                    };
                    
                    const pName = part.name || part.description || `Part ${index+1}`;
                    const pDim = `${part.bounding_box?.sizeX||0}x${part.bounding_box?.sizeY||0}x${part.bounding_box?.sizeZ||0}`;
                    const pQty = part.quantity || 1;
                    const pCons = part.critical_considerations || '-';

                    if (isBuyout) {
                        return {
                            isBuyout: true,
                            item_number: part.item_number || '-',
                            name: pName,
                            material: part.material || '-',
                            dimensions: pDim,
                            qty: pQty,
                            process: 'Buyout Item',
                            machining_cost: 0,
                            material_cost: 0,
                            cycle_time: 0,
                            critical_considerations: pCons,
                            unit_price: 0,
                        };
                    }

                    const fallbackMatId = Object.keys(materials).length > 0 ? Object.keys(materials)[0] : 'aluminum_6061';
                    const fallbackProcId = Object.keys(processes).length > 0 ? Object.keys(processes)[0] : 'cnc_milling_3ax';

                    const resp = await fetch(`${API}/quote`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            geometry: partGeometry,
                            material_id: part.material_id || materialId || fallbackMatId,
                            process_ids: part.process_id ? [part.process_id] : (processIds.length ? processIds : [fallbackProcId]),
                            surface_treatment_ids: surfaceTreatmentIds,
                            profit_margin_pct: profitMarginPct,
                            tolerance_id: part.tolerance_id || toleranceId,
                            quantity: pQty,
                            client_name: clientName,
                            client_company: clientCompany,
                            hsn_code: hsnCode,
                            source_filename: fileMetrics?.fileName || '',
                            screenshot: null,
                            include_setup_cost: includeSetupCost,
                            hole_count_override: holeCountOverride,
                            stock_type: stockType, 
                        }),
                    });

                    if (!resp.ok) {
                        return { 
                            isBuyout: false, error: true, item_number: part.item_number, 
                            name: pName, material: part.material, dimensions: pDim, qty: pQty 
                        };
                    }
                    const qData = await resp.json();
                    
                    // Format for table
                    return {
                        isBuyout: false,
                        item_number: part.item_number || '-',
                        name: pName,
                        material: materials[part.material_id || materialId]?.name || part.material || '-',
                        dimensions: pDim,
                        qty: pQty,
                        process: processes[part.process_id || processIds[0]]?.name || 'Machining',
                        machining_cost: qData.breakdown?.machining_cost || 0,
                        material_cost: qData.breakdown?.material_cost || 0,
                        cycle_time: qData.machining_hours || 0,
                        critical_considerations: pCons,
                        unit_price: qData.unit_price || 0,
                        total_price: qData.order_total || 0,
                    };
                }));
                setMultiQuote({
                    parts: results,
                    quote_number: `AD/BOM/${Math.floor(Math.random()*9000)+1000}`
                });
            } else {
                // Single part quote processing
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
                        include_setup_cost: includeSetupCost,
                        hole_count_override: holeCountOverride,
                        stock_type: stockType,
                    }),
                });
                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({ detail: 'Unknown error' }));
                    throw new Error(err.detail || `Server error ${resp.status}`);
                }
                setQuote(await resp.json());
            }
        } catch (e) {
            setError(e.message || 'Network error — is the backend running?');
        } finally {
            setLoading(false);
        }
    };

    // ── Download PDF
    const downloadPdf = async () => {
        if (!geometry && !multiQuote) return;
        setPdfLoading(true);
        setError('');
        try {
            // NOTE: Batch PDF generation feature is WIP. For now, we fallback to first part or single logic.
            const qty = Math.max(1, Math.min(10000, parseInt(String(quantity), 10) || 1));

            let screenshot = null;
            if (captureScreenshot) {
                try { screenshot = captureScreenshot(); } catch { }
            }

            const reqBody = {
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
            };

            const resp = await fetch(`${API}/quote/pdf`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reqBody),
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

    // ── Download BOM PDF (multi-part assembly)
    const downloadBomPdf = async () => {
        if (!multiQuote) return;
        setPdfLoading(true);
        setError('');
        try {
            const resp = await fetch(`${API}/quote/bom-pdf`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    parts: multiQuote.parts,
                    quote_number: multiQuote.quote_number,
                    client_name: clientName,
                    client_company: clientCompany,
                    hsn_code: hsnCode,
                    source_filename: fileMetrics?.fileName || '',
                    profit_margin_pct: profitMarginPct,
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
            a.download = `AccuDesign_BOM_Quote_${Date.now()}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (e) {
            setError(e.message || 'BOM PDF generation failed');
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

                {/* Stock Type (Senior Req) */}
                <Select label="Stock Type" value={stockType} onChange={setStockType}
                    options={[
                        { value: 'round_bar', label: 'Round Bar' },
                        { value: 'plate', label: 'Plate / Flat Bar' },
                        { value: 'hex_bar', label: 'Hex Bar' },
                    ]} />

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

                {/* Setup Cost Toggle (Senior Req) */}
                <div className="flex items-center justify-between py-2 px-1">
                    <div className="flex items-center gap-2">
                        <ToggleLeft size={12} className="text-gray-500" />
                        <span className="text-[10px] text-gray-400 uppercase tracking-widest">Include Setup / Amortization</span>
                    </div>
                    <button
                        onClick={() => setIncludeSetupCost(!includeSetupCost)}
                        className={`relative w-9 h-5 rounded-full transition-colors duration-200 ${
                            includeSetupCost ? 'bg-cyan-500/60' : 'bg-gray-700'
                        }`}
                    >
                        <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${
                            includeSetupCost ? 'left-[18px]' : 'left-0.5'
                        }`} />
                    </button>
                </div>

                {/* Hole Count Override (Senior Req) */}
                {geometry && (
                    <div className="space-y-1.5">
                        <label className="text-[10px] text-gray-500 uppercase tracking-widest flex items-center gap-1.5">
                            <CircleDot size={10} /> Hole Count
                            <span className="text-gray-600 normal-case tracking-normal ml-1">
                                (AI detected: {geometry?.holes?.length || 0})
                            </span>
                        </label>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setHoleCountOverride(prev => Math.max(0, (prev < 0 ? (geometry?.holes?.length || 0) : prev) - 1))}
                                className="w-7 h-7 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 
                                    hover:border-cyan-500/50 hover:text-cyan-300 flex items-center justify-center transition-colors"
                            >
                                <Minus size={12} />
                            </button>
                            <input
                                type="number" min="0" max="200"
                                value={holeCountOverride < 0 ? (geometry?.holes?.length || 0) : holeCountOverride}
                                onChange={e => {
                                    const v = parseInt(e.target.value, 10);
                                    setHoleCountOverride(isNaN(v) ? -1 : Math.max(0, Math.min(200, v)));
                                }}
                                className="flex-1 bg-gray-800/70 border border-gray-700/60 text-gray-200
                                    text-[11px] rounded-lg px-3 py-1.5 text-center focus:outline-none 
                                    focus:border-cyan-500/50 font-mono"
                            />
                            <button
                                onClick={() => setHoleCountOverride(prev => (prev < 0 ? (geometry?.holes?.length || 0) : prev) + 1)}
                                className="w-7 h-7 rounded-lg bg-gray-800 border border-gray-700 text-gray-300
                                    hover:border-cyan-500/50 hover:text-cyan-300 flex items-center justify-center transition-colors"
                            >
                                <Plus size={12} />
                            </button>
                            {holeCountOverride >= 0 && (
                                <button
                                    onClick={() => setHoleCountOverride(-1)}
                                    className="text-[9px] text-amber-400/80 hover:text-amber-300 font-mono underline"
                                >Reset</button>
                            )}
                        </div>
                        {holeCountOverride >= 0 && holeCountOverride !== (geometry?.holes?.length || 0) && (
                            <p className="text-[9px] text-amber-400/70 font-mono flex items-center gap-1">
                                <AlertCircle size={9} /> Overridden from {geometry?.holes?.length || 0} → {holeCountOverride}
                            </p>
                        )}
                    </div>
                )}

                {/* ── Material Verification (INSIDE config — above Generate) ── */}
                {geometry && materialEstimate && (
                    <div className="rounded-xl bg-gradient-to-br from-emerald-900/15 to-black/40
                        border border-emerald-500/15 p-3 space-y-2 mt-1">
                        <div className="flex items-center gap-2 border-b border-emerald-500/10 pb-1.5">
                            <Eye size={12} className="text-emerald-400" />
                            <span className="text-[10px] font-bold text-gray-300 uppercase tracking-widest">
                                Material Verification
                            </span>
                            <span className="text-[8px] text-emerald-400/70 font-mono ml-auto">
                                {estimateLoading ? '⟳ ...' : '✓ Ready'}
                            </span>
                        </div>

                        <div className="space-y-0.5">
                            <LineItem label="Stock" value={materialEstimate.stock_type_name || stockType} />
                            <LineItem label="Material" value={materialEstimate.material_name || '—'} />
                            <LineItem label="Dims (mm)"
                                value={`${parseFloat(geometry.boundingBox?.sizeX || 0).toFixed(1)} × ${parseFloat(geometry.boundingBox?.sizeY || 0).toFixed(1)} × ${parseFloat(geometry.boundingBox?.sizeZ || 0).toFixed(1)}`} />
                        </div>

                        <div className="bg-black/25 rounded-lg p-2 space-y-0.5">
                            <p className="text-[8px] text-emerald-400/70 uppercase tracking-widest font-bold mb-0.5">Envelope</p>
                            {materialEstimate.standard_diameter_mm && (
                                <LineItem label="Std Ø" value={`${materialEstimate.standard_diameter_mm} mm`} highlight />
                            )}
                            {materialEstimate.standard_af_mm && (
                                <LineItem label="Hex AF" value={`${materialEstimate.standard_af_mm} mm`} highlight />
                            )}
                            {materialEstimate.standard_thickness_mm && (
                                <LineItem label="Thick." value={`${materialEstimate.standard_thickness_mm} × ${materialEstimate.standard_width_mm} mm`} highlight />
                            )}
                            {materialEstimate.effective_length_mm > 0 && (
                                <LineItem label="Eff. Len" value={`${materialEstimate.effective_length_mm} mm`} />
                            )}
                            <LineItem label="Vol." value={`${fmt(materialEstimate.envelope_volume_mm3)} mm³`} />
                        </div>

                        <div className="bg-black/25 rounded-lg p-2 space-y-0.5">
                            <p className="text-[8px] text-emerald-400/70 uppercase tracking-widest font-bold mb-0.5">Weight & Cost</p>
                            <LineItem label="Wt/Part" value={`${materialEstimate.gross_weight_per_part_kg?.toFixed(3)} kg`} highlight />
                            <LineItem label="Batch Wt" value={`${materialEstimate.total_batch_weight_kg?.toFixed(3)} kg`} />
                            <LineItem label="Utilization" value={`${materialEstimate.material_utilization_pct}%`} />
                            <LineItem label="Mat. Cost" value={`₹${fmt(materialEstimate.estimated_material_cost_inr)}`} highlight />
                            {materialEstimate.parts_per_bar > 0 && (
                                <LineItem label="Parts/Bar" value={`${materialEstimate.parts_per_bar} (${materialEstimate.bars_needed} bar${materialEstimate.bars_needed > 1 ? 's' : ''})`} />
                            )}
                        </div>

                        <p className="text-[8px] text-gray-600 font-mono leading-tight">
                            +{materialEstimate.allowances?.surface_allowance_mm}mm surf, +{materialEstimate.allowances?.saw_kerf_mm}mm kerf{materialEstimate.allowances?.end_grip_mm > 0 ? `, +${materialEstimate.allowances?.end_grip_mm}mm grip` : ''}, {materialEstimate.allowances?.scrap_factor_pct}% scrap
                        </p>

                        {/* Validate with AI button */}
                        <button
                            onClick={validateWithAI}
                            disabled={aiValidating || !materialEstimate}
                            className="w-full py-2 rounded-lg text-[10px] font-bold tracking-wider
                                transition-all duration-200 flex items-center justify-center gap-1.5
                                border border-purple-500/30 bg-purple-500/5 text-purple-300
                                hover:bg-purple-500/15 hover:border-purple-400/50 active:scale-[0.98]
                                disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            {aiValidating
                                ? <><RefreshCw size={11} className="animate-spin" /> Validating...</>
                                : <><ShieldCheck size={11} /> Validate with AI</>}
                        </button>

                        {/* AI Validation Result */}
                        {aiValidation && (
                            <div className={`rounded-lg p-2.5 space-y-1 border ${
                                aiValidation.success
                                    ? aiValidation.match_level === 'excellent' ? 'bg-emerald-500/10 border-emerald-500/25'
                                    : aiValidation.match_level === 'good' ? 'bg-blue-500/10 border-blue-500/25'
                                    : aiValidation.match_level === 'fair' ? 'bg-amber-500/10 border-amber-500/25'
                                    : 'bg-red-500/10 border-red-500/25'
                                    : 'bg-red-500/10 border-red-500/25'
                            }`}>
                                {aiValidation.success ? (
                                    <>
                                        <div className="flex items-center justify-between">
                                            <span className="text-[10px] font-bold text-gray-300 flex items-center gap-1">
                                                <ShieldCheck size={11} className={
                                                    aiValidation.match_level === 'excellent' ? 'text-emerald-400' :
                                                    aiValidation.match_level === 'good' ? 'text-blue-400' :
                                                    aiValidation.match_level === 'fair' ? 'text-amber-400' : 'text-red-400'
                                                } />
                                                AI Confidence
                                            </span>
                                            <span className={`text-[13px] font-bold font-mono ${
                                                aiValidation.confidence_score >= 85 ? 'text-emerald-300' :
                                                aiValidation.confidence_score >= 60 ? 'text-blue-300' :
                                                aiValidation.confidence_score >= 40 ? 'text-amber-300' : 'text-red-300'
                                            }`}>
                                                {aiValidation.confidence_score}%
                                            </span>
                                        </div>
                                        <div className="w-full bg-gray-800 rounded-full h-1.5 mt-0.5">
                                            <div
                                                className={`h-1.5 rounded-full transition-all duration-500 ${
                                                    aiValidation.confidence_score >= 85 ? 'bg-emerald-400' :
                                                    aiValidation.confidence_score >= 60 ? 'bg-blue-400' :
                                                    aiValidation.confidence_score >= 40 ? 'bg-amber-400' : 'bg-red-400'
                                                }`}
                                                style={{ width: `${aiValidation.confidence_score}%` }}
                                            />
                                        </div>
                                        <p className="text-[9px] text-gray-400 mt-1">
                                            Match: <span className="font-bold capitalize">{aiValidation.match_level}</span>
                                            {aiValidation.weight_diff_pct > 0 && ` (${aiValidation.weight_diff_pct}% diff)`}
                                        </p>
                                        {aiValidation.discrepancy_notes && aiValidation.discrepancy_notes !== 'Values align' && (
                                            <p className="text-[9px] text-amber-400/80 mt-0.5">
                                                ⚠ {aiValidation.discrepancy_notes}
                                            </p>
                                        )}
                                    </>
                                ) : (
                                    <p className="text-[9px] text-red-400 flex items-center gap-1">
                                        <AlertCircle size={10} /> {aiValidation.error}
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Generate button */}
                <button
                    onClick={generateQuote}
                    disabled={loading || (!geometry && !(fileMetrics?.allParts?.length > 1))}
                    className={`w-full py-3 mt-1 rounded-xl text-[12px] font-bold tracking-wider
                        transition-all duration-300 flex items-center justify-center gap-2
                        ${(geometry || fileMetrics?.allParts?.length > 1)
                            ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 shadow-[0_0_20px_rgba(34,211,238,0.3)] hover:shadow-[0_0_30px_rgba(34,211,238,0.5)] hover:scale-[1.02] active:scale-[0.98]'
                            : 'bg-white/5 text-gray-500 cursor-not-allowed border border-white/10'}`}
                >
                    {loading
                        ? <><RefreshCw size={14} className="animate-spin" /> Computing…</>
                        : <><Zap size={14} className="drop-shadow-md" />
                            {(geometry || fileMetrics?.allParts?.length > 1) ? 'Generate Quote (₹)' : 'Upload STEP/PDF First'}</>
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

            {/* ── Multi-Part Tabular Quote (for assemblies) ──────────────── */}
            {multiQuote && (
                <div ref={resultRef} className="rounded-2xl bg-gradient-to-b from-purple-900/30 to-black/60
                    border border-purple-500/30 shadow-[0_0_30px_rgba(168,85,247,0.15)]
                    backdrop-blur-xl p-4 space-y-3 relative overflow-hidden">
                    
                    {/* Header */}
                    <div className="flex items-center gap-2 border-b border-purple-500/20 pb-2">
                        <Layers size={15} className="text-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.8)]" />
                        <span className="text-[11px] font-bold text-white uppercase tracking-widest">
                            BOM Assembly Quote (₹ INR)
                        </span>
                    </div>

                    {/* Quote Number */}
                    {multiQuote.quote_number && (
                        <div className="bg-gray-900/70 rounded-lg px-3 py-2 flex justify-between items-center">
                            <div>
                                <p className="text-[9px] text-gray-500 uppercase tracking-widest">Quotation No.</p>
                                <p className="text-[12px] font-mono text-purple-300 font-bold">{multiQuote.quote_number}</p>
                            </div>
                            <div className="text-right">
                                <p className="text-[9px] text-gray-500 uppercase tracking-widest">Total Parts</p>
                                <p className="text-[12px] font-mono text-gray-300 font-bold">{multiQuote.parts.length}</p>
                            </div>
                        </div>
                    )}

                    {/* Tabular Data */}
                    <div className="overflow-x-auto custom-scrollbar rounded-lg border border-purple-500/10">
                        <table className="w-full text-left border-collapse whitespace-nowrap text-[10px]">
                            <thead>
                                <tr className="bg-purple-500/10 text-purple-200 border-b border-purple-500/20">
                                    <th className="px-2 py-1.5 font-medium tracking-wider uppercase">Item #</th>
                                    <th className="px-2 py-1.5 font-medium tracking-wider uppercase">Part Name / Desc</th>
                                    <th className="px-2 py-1.5 font-medium tracking-wider uppercase">Material</th>
                                    <th className="px-2 py-1.5 font-medium tracking-wider uppercase">Dimensions (mm)</th>
                                    <th className="px-2 py-1.5 font-medium tracking-wider uppercase">Qty</th>
                                    <th className="px-2 py-1.5 font-medium tracking-wider uppercase">Process</th>
                                    <th className="px-2 py-1.5 font-medium tracking-wider uppercase whitespace-nowrap">Machining Cost (₹)</th>
                                    <th className="px-2 py-1.5 font-medium tracking-wider uppercase whitespace-nowrap">Material Cost (₹)</th>
                                    <th className="px-2 py-1.5 font-medium tracking-wider uppercase whitespace-nowrap">Critical Considerations</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {multiQuote.parts.map((p, i) => (
                                    <tr key={i} className={`hover:bg-white/5 transition-colors ${p.isBuyout ? 'opacity-80 bg-black/20' : ''}`}>
                                        <td className="px-2 py-2 font-mono text-gray-400">{p.item_number}</td>
                                        <td className="px-2 py-2 text-cyan-100 max-w-[150px] truncate" title={p.name}>{p.name}</td>
                                        <td className="px-2 py-2 text-gray-300 max-w-[120px] truncate">{p.material}</td>
                                        <td className="px-2 py-2 text-gray-400 font-mono text-[9px]">{p.dimensions}</td>
                                        <td className="px-2 py-2 font-mono text-cyan-300">{p.qty}</td>
                                        <td className="px-2 py-2 text-gray-300">
                                            {p.isBuyout ? <span className="text-amber-400/80 text-[9px] uppercase tracking-wider bg-amber-400/10 px-1 py-0.5 rounded border border-amber-400/20">{p.process}</span> : p.process}
                                        </td>
                                        <td className="px-2 py-2 font-mono text-gray-300">{p.isBuyout ? '—' : `₹${fmt(p.machining_cost)}`}</td>
                                        <td className="px-2 py-2 font-mono text-gray-300">{p.isBuyout ? '—' : `₹${fmt(p.material_cost)}`}</td>
                                        <td className="px-2 py-2 text-gray-400 text-[9px] max-w-[200px] truncate" title={p.critical_considerations}>{p.critical_considerations}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Totals */}
                    <div className="border-t border-purple-500/20 pt-2 space-y-0.5 mt-2">
                        <LineItem 
                            label="Grand Total (Estimated, Excl. Buyouts)"
                            value={`₹${fmt(multiQuote.parts.reduce((sum, p) => sum + (p.total_price || 0), 0))}`}
                            highlight large
                        />
                        <p className="text-[9px] text-gray-500 text-right italic pt-1">All prices in ₹ INR. Buyout items quoted separately.</p>
                        
                        {/* Download BOM PDF */}
                        <button
                            onClick={downloadBomPdf}
                            disabled={pdfLoading}
                            className="w-full py-2.5 mt-2 rounded-xl text-[12px] font-bold tracking-wider
                                transition-all duration-300 flex items-center justify-center gap-2
                                border border-purple-500/30 bg-white/5 text-purple-300
                                hover:bg-purple-500/10 hover:border-purple-400 active:scale-[0.98]
                                disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {pdfLoading
                                ? <><RefreshCw size={14} className="animate-spin" /> Generating PDF…</>
                                : <><FileText size={14} /> Download BOM Quote (PDF)</>}
                        </button>
                    </div>
                </div>
            )}

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
                        {quote.include_setup_cost !== false ? (
                            <LineItem label="Setup (amort.)" value={`₹${fmt(quote.breakdown?.setup_cost)}`} />
                        ) : (
                            <LineItem label="Setup (excluded)" value="₹0" />
                        )}
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

                    {/* Part info + Material Estimate */}
                    <div className="border-t border-gray-700/40 pt-2 space-y-0.5">
                        <LineItem label="Part Mass" value={`${fmt(quote.mass_kg, 3)} kg`} />
                        {quote.material_estimate && (
                            <>
                                <LineItem label="Stock Size" value={quote.material_estimate.standard_stock_size || '—'} highlight />
                                <LineItem label="Gross Wt/Part" value={`${quote.material_estimate.gross_weight_per_part_kg?.toFixed(3)} kg`} />
                                <LineItem label="Batch Weight" value={`${quote.material_estimate.total_batch_weight_kg?.toFixed(3)} kg`} />
                                <LineItem label="Utilization" value={`${quote.material_estimate.material_utilization_pct}%`} />
                            </>
                        )}
                        <LineItem label="Machining Time" value={`${fmt(quote.machining_hours, 2)} hr`} />
                        <LineItem label="Complexity" value={quote.complexity || '—'} />
                        {(quote.holes_count > 0) &&
                            <LineItem label="Holes (used)" value={String(quote.holes_count)} />}
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
