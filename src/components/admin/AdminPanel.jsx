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
                <RefreshCw size={24} className="text-cyan-400 animate-spin" />
                <p className="text-[10px] text-gray-500 font-mono">Loading materials catalog…</p>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto w-full py-2 px-1">
            {/* Main Side-by-Side Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                
                {/* Left Side: Admin Tools & Controls (1/3 width on desktop) */}
                <div className="lg:col-span-1 space-y-5">
                    
                    {/* Secure Admin Overrides Info Card */}
                    <div className="p-4 rounded-xl border border-emerald-500/10 bg-emerald-500/[0.01] backdrop-blur-sm space-y-4">
                        <div className="space-y-2">
                            <div className="flex items-center gap-2">
                                <div className="p-1 rounded bg-emerald-500/10 text-emerald-400">
                                    <Sliders size={14} />
                                </div>
                                <span className="text-[11px] font-extrabold text-white tracking-wider uppercase">
                                    Secure Rate Overrides
                                </span>
                            </div>
                            <p className="text-[10px] text-gray-400 leading-relaxed">
                                Fine-tune local raw material base rates (INR/kg). Changes take effect instantly across all geometry calculations and quotation logs.
                            </p>
                        </div>

                        <div className="pt-3 border-t border-white/[0.03] space-y-2 font-mono text-[9px] text-gray-500">
                            <div className="flex justify-between">
                                <span>Status:</span>
                                <span className="text-emerald-400 font-bold flex items-center gap-1">
                                    <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" /> Live DB Connected
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span>Storage:</span>
                                <span className="text-gray-300">Local JSON Encrypted</span>
                            </div>
                        </div>
                    </div>

                    {/* Spreadsheet Upload Dropzone */}
                    <div className="p-4 rounded-xl border border-gray-800 bg-gray-950/20 backdrop-blur-sm space-y-3.5">
                        <div className="flex justify-between items-center border-b border-white/[0.03] pb-2">
                            <div className="flex items-center gap-2">
                                <FileSpreadsheet size={15} className="text-emerald-400" />
                                <span className="text-[10px] font-bold text-gray-200 uppercase tracking-wider">Bulk Pricing Upload</span>
                            </div>
                            <span className="text-[8px] font-mono text-gray-500">.xlsx, .xls, .csv</span>
                        </div>

                        <div className="space-y-3">
                            <label className="flex flex-col items-center justify-center border border-dashed border-gray-700/60 hover:border-emerald-500/40 rounded-lg p-5 cursor-pointer hover:bg-white/[0.01] transition-all group text-center min-h-[100px]">
                                <input 
                                    type="file" 
                                    accept=".xlsx,.xls,.csv" 
                                    onChange={handleExcelUpload} 
                                    disabled={uploading}
                                    className="hidden" 
                                />
                                {uploading ? (
                                    <div className="flex flex-col items-center gap-2">
                                        <RefreshCw size={18} className="animate-spin text-emerald-400" />
                                        <span className="text-[9px] font-mono text-gray-400">Updating matrices...</span>
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center gap-1.5">
                                        <Upload size={18} className="text-gray-500 group-hover:text-emerald-400 transition-colors" />
                                        <span className="text-[10px] font-bold text-gray-300">Choose Senior's Pricing File</span>
                                        <span className="text-[8px] text-gray-600 font-mono">Auto-matches common aliases</span>
                                    </div>
                                )}
                            </label>

                            {/* Upload Results pane */}
                            {uploadResults && (
                                <div className="p-2.5 rounded-lg bg-gray-950/60 border border-gray-900 text-[9px] flex flex-col justify-between">
                                    <div className="flex justify-between border-b border-gray-900 pb-1 font-mono">
                                        <span className="text-emerald-400 font-bold">✓ {uploadResults.updated_count} Synced</span>
                                        {uploadResults.unrecognized?.length > 0 && (
                                            <span className="text-amber-400 font-bold">⚠ {uploadResults.unrecognized.length} Skipped</span>
                                        )}
                                    </div>
                                    <div className="max-h-[80px] overflow-y-auto pr-1 space-y-1 font-mono text-gray-400 mt-1">
                                        {uploadResults.updated_materials?.map((m, idx) => (
                                            <div key={idx} className="flex justify-between">
                                                <span className="truncate max-w-[100px]">{m.name}</span>
                                                <span className="text-emerald-400">₹{m.new_price}/kg</span>
                                            </div>
                                        ))}
                                        {uploadResults.unrecognized?.length > 0 && (
                                            <div className="pt-1 mt-1 text-[8px] text-amber-500">
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
                        className="w-full py-2 px-3.5 rounded border border-red-900/30 hover:border-red-700/40 hover:bg-red-950/10 
                            disabled:opacity-50 text-red-400 text-[10px] font-bold uppercase tracking-wider transition-all
                            flex items-center justify-center gap-1.5"
                    >
                        <Database size={11} />
                        Reset Database Defaults
                    </button>
                </div>

                {/* Right Side: Material Catalog & Search (2/3 width on desktop) */}
                <div className="lg:col-span-2 space-y-4">
                    
                    {/* Header with Search */}
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 border-b border-white/[0.04] pb-2">
                        <h4 className="text-[10px] font-mono uppercase tracking-widest text-gray-500">
                            Manual Catalog Adjustments
                        </h4>
                        <div className="relative w-full md:w-64">
                            <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-600" />
                            <input
                                type="text"
                                value={searchTerm}
                                onChange={e => setSearchTerm(e.target.value)}
                                placeholder="Filter catalog..."
                                className="w-full bg-gray-900/50 border border-gray-800 text-gray-300
                                    text-[10px] rounded-lg pl-7.5 pr-2.5 py-1.5 focus:outline-none focus:border-emerald-500/30 font-mono"
                            />
                        </div>
                    </div>

                    {/* Notifications */}
                    {message && (
                        <div className={`p-2.5 rounded-lg border flex items-center gap-2 text-[10px] font-mono animate-fade-in
                            ${message.type === 'success' 
                                ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300' 
                                : 'bg-red-950/20 border-red-500/30 text-red-300'}`}>
                            {message.type === 'success' ? <CheckCircle size={12} className="shrink-0" /> : <AlertCircle size={12} className="shrink-0" />}
                            <span>{message.text}</span>
                        </div>
                    )}

                    <form onSubmit={handleSave} className="space-y-4">
                        
                        {/* Materials Grid (2-column inside 2/3 container) */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[480px] overflow-y-auto pr-1.5 custom-scrollbar pb-1">
                            {filteredMaterials.length === 0 ? (
                                <p className="text-[10px] text-gray-600 italic text-center py-8 col-span-full">
                                    No matching materials registered in this database.
                                </p>
                            ) : (
                                filteredMaterials.map(mid => {
                                    const mat = materials[mid];
                                    return (
                                        <div key={mid} className="p-3 rounded-lg border border-white/[0.03] bg-white/[0.005] hover:bg-white/[0.015] transition-all duration-150 flex flex-col justify-between gap-3">
                                            <div>
                                                <div className="text-[11px] font-extrabold text-white truncate">{mat.name}</div>
                                                <div className="text-[9px] text-gray-500 font-mono mt-0.5">
                                                    {mat.grade !== '-' && `Grade: ${mat.grade}`} 
                                                    {mat.standard !== '-' && ` · Std: ${mat.standard}`}
                                                </div>
                                            </div>
                                            <div className="flex justify-between items-center pt-2.5 border-t border-white/[0.03]">
                                                <span className="text-[8px] text-gray-600 font-mono">Density: {mat.density} g/cm³</span>
                                                <div className="relative w-28">
                                                    <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[9px] text-cyan-400 font-mono">₹</span>
                                                    <input
                                                        type="number"
                                                        step="0.1"
                                                        min="1"
                                                        value={editedPrices[mid] ?? ''}
                                                        onChange={e => handlePriceChange(mid, e.target.value)}
                                                        className="w-full bg-gray-950/80 border border-gray-800 rounded py-1 pl-4.5 pr-2
                                                            text-[10px] text-right font-mono text-cyan-300 focus:outline-none focus:border-cyan-500/80"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                        </div>

                        {/* Save Action Bar */}
                        <div className="flex justify-end gap-3 pt-3 border-t border-white/[0.04]">
                            <button
                                type="submit"
                                disabled={saving || resetting || uploading}
                                className="py-1.5 px-5 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50
                                    text-white text-[10px] font-bold uppercase tracking-wider transition-colors
                                    flex items-center justify-center gap-1.5"
                            >
                                {saving ? <RefreshCw size={11} className="animate-spin" /> : <Save size={11} />}
                                Save Manual Prices
                            </button>
                        </div>

                    </form>
                </div>
                
            </div>
        </div>
    );
}
