import React, { useState, useEffect } from 'react';
import { Save, RefreshCw, CheckCircle, AlertCircle, Search, Sliders, Database, Upload, FileSpreadsheet } from 'lucide-react';

const API = '/api';

export default function AdminPanel() {
    const [materials, setMaterials] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [resetting, setResetting] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [editedPrices, setEditedPrices] = useState({});
    const [message, setMessage] = useState(null); 
    const [uploadResults, setUploadResults] = useState(null); 

    useEffect(() => {
        loadMaterials();
    }, []);

    const loadMaterials = async () => {
        setLoading(true);
        try {
            const resp = await fetch(`${API}/materials`);
            if (resp.ok) {
                const data = await resp.json();
                setMaterials(data);
                
                const initialPrices = {};
                Object.keys(data).forEach(mid => {
                    initialPrices[mid] = data[mid].price_inr_kg;
                });
                setEditedPrices(initialPrices);
            } else {
                showMsg('error', 'Failed to load materials catalog.');
            }
        } catch (err) {
            showMsg('error', 'Error connecting to server.');
        } finally {
            setLoading(false);
        }
    };

    const showMsg = (type, text) => {
        setMessage({ type, text });
        setTimeout(() => setMessage(null), 8000);
    };

    const handlePriceChange = (mid, val) => {
        const num = parseFloat(val);
        setEditedPrices(prev => ({
            ...prev,
            [mid]: isNaN(num) ? '' : num
        }));
    };

    const handleSave = async (e) => {
        e.preventDefault();
        setSaving(true);
        setUploadResults(null);
        try {
            const pricesToUpdate = {};
            Object.keys(editedPrices).forEach(mid => {
                const p = parseFloat(editedPrices[mid]);
                if (!isNaN(p) && p > 0) {
                    pricesToUpdate[mid] = p;
                }
            });

            const resp = await fetch(`${API}/materials/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prices: pricesToUpdate })
            });

            if (resp.ok) {
                showMsg('success', 'Material base prices updated successfully!');
                await loadMaterials();
            } else {
                const err = await resp.json().catch(() => ({}));
                showMsg('error', err.detail || 'Failed to update prices.');
            }
        } catch (err) {
            showMsg('error', 'Connection error while saving.');
        } finally {
            setSaving(false);
        }
    };

    const handleExcelUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        setUploadResults(null);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const resp = await fetch(`${API}/materials/upload-excel`, {
                method: 'POST',
                body: formData
            });

            if (resp.ok) {
                const result = await resp.json();
                setUploadResults(result);
                showMsg('success', `Excel imported successfully! Updated ${result.updated_count} materials.`);
                await loadMaterials();
            } else {
                const err = await resp.json().catch(() => ({ detail: 'Failed to process file' }));
                showMsg('error', err.detail || 'Excel processing failed.');
            }
        } catch (err) {
            showMsg('error', 'Connection error while uploading spreadsheet.');
        } finally {
            setUploading(false);
            e.target.value = '';
        }
    };

    const handleReset = async () => {
        if (!window.confirm("Are you sure you want to reset all material prices to default market standards? Any custom edits will be lost.")) {
            return;
        }
        setResetting(true);
        setUploadResults(null);
        try {
            const resp = await fetch(`${API}/materials/reset`, { method: 'POST' });
            if (resp.ok) {
                showMsg('success', 'Reset standard default prices.');
                await loadMaterials();
            } else {
                showMsg('error', 'Failed to reset database.');
            }
        } catch (err) {
            showMsg('error', 'Connection error while resetting.');
        } finally {
            setResetting(false);
        }
    };

    const filteredMaterials = Object.keys(materials).filter(mid => {
        const mat = materials[mid];
        const searchLower = searchTerm.toLowerCase();
        return (
            mat.name?.toLowerCase().includes(searchLower) ||
            mat.grade?.toLowerCase().includes(searchLower) ||
            mat.standard?.toLowerCase().includes(searchLower) ||
            mid.toLowerCase().includes(searchLower)
        );
    });

    if (loading) {
        return (
            <div className="py-12 flex flex-col items-center justify-center gap-2">
                <RefreshCw size={24} className="text-accu-600 animate-spin" />
                <p className="text-[10px] text-slate-500 font-mono font-semibold">Loading materials catalog…</p>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto w-full py-2 px-1 text-slate-800 font-sans">
            {/* Main Side-by-Side Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                
                {/* Left Side: Admin Tools & Controls (1/3 width on desktop) */}
                <div className="lg:col-span-1 space-y-5">
                    
                    {/* Secure Admin Overrides Info Card */}
                    <div className="p-4 rounded-2xl border border-slate-200 bg-white shadow-sm space-y-4">
                        <div className="space-y-2">
                            <div className="flex items-center gap-2">
                                <div className="p-1 rounded-lg bg-accu-50 text-accu-600 border border-accu-200">
                                    <Sliders size={14} />
                                </div>
                                <span className="text-[11px] font-extrabold text-slate-900 tracking-wider uppercase font-heading">
                                    Secure Rate Overrides
                                </span>
                            </div>
                            <p className="text-[10px] text-slate-600 leading-relaxed font-sans">
                                Fine-tune local raw material base rates (₹ INR/kg). Changes take effect instantly across all geometry calculations and quotation logs.
                            </p>
                        </div>

                        <div className="pt-3 border-t border-slate-100 space-y-2 font-mono text-[9px] text-slate-500">
                            <div className="flex justify-between">
                                <span>Status:</span>
                                <span className="text-emerald-600 font-bold flex items-center gap-1">
                                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" /> Live DB Connected
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span>Storage:</span>
                                <span className="text-slate-700 font-bold">Local JSON Encrypted</span>
                            </div>
                        </div>
                    </div>

                    {/* Spreadsheet Upload Dropzone */}
                    <div className="p-4 rounded-2xl border border-slate-200 bg-white shadow-sm space-y-3.5">
                        <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                            <div className="flex items-center gap-2">
                                <FileSpreadsheet size={15} className="text-emerald-600" />
                                <span className="text-[10px] font-bold text-slate-900 uppercase tracking-wider font-heading">Bulk Pricing Upload</span>
                            </div>
                            <span className="text-[8px] font-mono text-slate-400 font-bold">.xlsx, .xls, .csv</span>
                        </div>

                        <div className="space-y-3">
                            <label className="flex flex-col items-center justify-center border border-dashed border-slate-300 hover:border-accu-500 rounded-xl p-5 cursor-pointer hover:bg-slate-50 transition-all group text-center min-h-[100px]">
                                <input 
                                    type="file" 
                                    accept=".xlsx,.xls,.csv" 
                                    onChange={handleExcelUpload} 
                                    disabled={uploading}
                                    className="hidden" 
                                />
                                {uploading ? (
                                    <div className="flex flex-col items-center gap-2">
                                        <RefreshCw size={18} className="animate-spin text-accu-600" />
                                        <span className="text-[9px] font-mono text-slate-500 font-bold">Updating matrices...</span>
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center gap-1.5">
                                        <Upload size={18} className="text-slate-400 group-hover:text-accu-600 transition-colors" />
                                        <span className="text-[10px] font-bold text-slate-700">Choose Senior's Pricing File</span>
                                        <span className="text-[8px] text-slate-400 font-mono">Auto-matches common aliases</span>
                                    </div>
                                )}
                            </label>

                            {/* Upload Results pane */}
                            {uploadResults && (
                                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-[9px] flex flex-col justify-between">
                                    <div className="flex justify-between border-b border-slate-200 pb-1 font-mono">
                                        <span className="text-emerald-600 font-bold">✓ {uploadResults.updated_count} Synced</span>
                                        {uploadResults.unrecognized?.length > 0 && (
                                            <span className="text-amber-600 font-bold">⚠ {uploadResults.unrecognized.length} Skipped</span>
                                        )}
                                    </div>
                                    <div className="max-h-[80px] overflow-y-auto pr-1 space-y-1 font-mono text-slate-600 mt-1">
                                        {uploadResults.updated_materials?.map((m, idx) => (
                                            <div key={idx} className="flex justify-between">
                                                <span className="truncate max-w-[100px] font-semibold">{m.name}</span>
                                                <span className="text-emerald-600 font-bold">₹{m.new_price}/kg</span>
                                            </div>
                                        ))}
                                        {uploadResults.unrecognized?.length > 0 && (
                                            <div className="pt-1 mt-1 text-[8px] text-amber-600 font-semibold">
                                                Skipped: {uploadResults.unrecognized.join(', ')}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Reset Button under Left column */}
                    <button
                        type="button"
                        onClick={handleReset}
                        disabled={saving || resetting || uploading}
                        className="w-full py-2 px-3.5 rounded-xl border border-red-200 hover:border-red-300 hover:bg-red-50 
                            disabled:opacity-50 text-red-600 text-[10px] font-bold uppercase tracking-wider transition-all
                            flex items-center justify-center gap-1.5 shadow-xs cursor-pointer"
                    >
                        <Database size={11} />
                        Reset Database Defaults
                    </button>
                </div>

                {/* Right Side: Material Catalog & Search (2/3 width on desktop) */}
                <div className="lg:col-span-2 space-y-4">
                    
                    {/* Header with Search */}
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 border-b border-slate-200 pb-2">
                        <h4 className="text-[10px] font-mono uppercase tracking-widest text-slate-600 font-bold">
                            Manual Catalog Adjustments
                        </h4>
                        <div className="relative w-full md:w-64">
                            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                type="text"
                                value={searchTerm}
                                onChange={e => setSearchTerm(e.target.value)}
                                placeholder="Filter catalog..."
                                className="w-full bg-white border border-slate-300 text-slate-800
                                    text-[10px] rounded-xl pl-8 pr-2.5 py-1.5 focus:outline-none focus:border-accu-500 focus:ring-1 focus:ring-accu-500 font-mono shadow-xs placeholder-slate-400"
                            />
                        </div>
                    </div>

                    {/* Notifications */}
                    {message && (
                        <div className={`p-2.5 rounded-xl border flex items-center gap-2 text-[10px] font-mono animate-fade-in
                            ${message.type === 'success' 
                                ? 'bg-emerald-50 border-emerald-300 text-emerald-800' 
                                : 'bg-red-50 border-red-300 text-red-800'}`}>
                            {message.type === 'success' ? <CheckCircle size={12} className="shrink-0 text-emerald-600" /> : <AlertCircle size={12} className="shrink-0 text-red-600" />}
                            <span className="font-semibold">{message.text}</span>
                        </div>
                    )}

                    <form onSubmit={handleSave} className="space-y-4">
                        
                        {/* Materials Grid (2-column inside 2/3 container) */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[480px] overflow-y-auto pr-1.5 custom-scrollbar pb-1">
                            {filteredMaterials.length === 0 ? (
                                <p className="text-[10px] text-slate-400 italic text-center py-8 col-span-full">
                                    No matching materials registered in this database.
                                </p>
                            ) : (
                                filteredMaterials.map(mid => {
                                    const mat = materials[mid];
                                    return (
                                        <div key={mid} className="p-3.5 rounded-2xl border border-slate-200 bg-white hover:border-accu-400 hover:shadow-md transition-all duration-150 flex flex-col justify-between gap-3 shadow-xs">
                                            <div>
                                                <div className="text-[11px] font-extrabold text-slate-900 truncate font-heading">{mat.name}</div>
                                                <div className="text-[9px] text-slate-500 font-mono mt-0.5">
                                                    {mat.grade !== '-' && `Grade: ${mat.grade}`} 
                                                    {mat.standard !== '-' && ` · Std: ${mat.standard}`}
                                                </div>
                                            </div>
                                            <div className="flex justify-between items-center pt-2.5 border-t border-slate-100">
                                                <span className="text-[8.5px] text-slate-500 font-mono font-semibold">Density: {mat.density} g/cm³</span>
                                                <div className="relative w-28">
                                                    <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[10px] text-accu-600 font-mono font-bold">₹</span>
                                                    <input
                                                        type="number"
                                                        step="0.1"
                                                        min="1"
                                                        value={editedPrices[mid] ?? ''}
                                                        onChange={e => handlePriceChange(mid, e.target.value)}
                                                        className="w-full bg-slate-50 border border-slate-300 focus:border-accu-500 focus:ring-1 focus:ring-accu-500 rounded-lg py-1 pl-5 pr-2
                                                            text-[10px] text-right font-mono text-slate-900 font-bold focus:outline-none shadow-xs"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                        </div>

                        {/* Save Action Bar */}
                        <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
                            <button
                                type="submit"
                                disabled={saving || resetting || uploading}
                                className="py-2 px-5 rounded-xl bg-accu-600 hover:bg-accu-700 disabled:opacity-50
                                    text-white text-[10px] font-bold uppercase tracking-wider transition-colors shadow-md
                                    flex items-center justify-center gap-1.5 cursor-pointer"
                            >
                                {saving ? <RefreshCw size={11} className="animate-spin" /> : <Save size={11} />}
                                Save Manual Prices
                            </button>
                        </div>

                    </form>
                </div>

            </div>

            {/* TechNewity Labs Branding */}
            <div className="mt-8 text-center border-t border-slate-200 pt-4 pb-2">
                <p className="text-[9px] uppercase tracking-[0.2em] font-semibold text-slate-400 font-sans">
                    developed by{" "}
                    <span className="font-extrabold text-accu-600">
                        TechNewity Labs
                    </span>
                </p>
            </div>
        </div>
    );
}
