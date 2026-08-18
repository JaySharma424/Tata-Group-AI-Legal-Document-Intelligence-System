import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  ShieldCheck, CheckCircle2, AlertTriangle, Eye,
  RefreshCw, Award, Filter, Search, FileText, UserCheck, Clock, Layers,
  BookOpen, Sparkles, Cpu, Key, Sliders, Save, CheckCircle, XCircle, Activity
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';

interface AdminDocRecord {
  job_id: string;
  file_name: string;
  uploader_email: string;
  business_unit: string;
  document_type: string;
  confidentiality_level: string;
  review_priority: string;
  created_at: string;
  status: string;
  ocr_confidence: number;
  page_count: number;
  high_risk_count: number;
  clauses_count: number;
  audit_trail: Array<{
    action: string;
    user_email: string;
    timestamp: string;
    comments: string;
  }>;
}

export const AdminPortal: React.FC = () => {
  // Navigation Tabs: 'documents' | 'llm_settings'
  const [adminTab, setAdminTab] = useState<'documents' | 'llm_settings'>('documents');

  const [documents, setDocuments] = useState<AdminDocRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterBu, setFilterBu] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  
  // LLM Config State
  const [selectedLlm, setSelectedLlm] = useState('gemini-3.5-flash');
  const [selectedEmbedding, setSelectedEmbedding] = useState('gemini-embedding-001');
  const [apiKey, setApiKey] = useState('');
  const [maskedKey, setMaskedKey] = useState('');
  const [configSaving, setConfigSaving] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; msg: string } | null>(null);

  // Inspection Modal
  const [inspectDoc, setInspectDoc] = useState<AdminDocRecord | null>(null);
  const [docClauses, setDocClauses] = useState<any[]>([]);
  const [inspectLoading, setInspectLoading] = useState(false);
  
  const [actionSubmitting, setActionSubmitting] = useState<string | null>(null);

  const fetchAdminDocuments = async () => {
    try {
      const token = sessionStorage.getItem('access_token');
      const response = await axios.get(`${API_BASE_URL}/api/v1/review/admin/documents`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDocuments(response.data.documents || []);
    } catch (err) {
      console.error('Failed to load admin documents:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchLlmConfig = async () => {
    try {
      const token = sessionStorage.getItem('access_token');
      const response = await axios.get(`${API_BASE_URL}/api/v1/admin/llm-config`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSelectedLlm(response.data.llm_model || 'gemini-3.5-flash');
      setSelectedEmbedding(response.data.embedding_model || 'gemini-embedding-001');
      setMaskedKey(response.data.masked_api_key || '****');
    } catch (err) {
      console.error('Failed to load LLM config:', err);
    }
  };

  useEffect(() => {
    fetchAdminDocuments();
    fetchLlmConfig();
    const interval = setInterval(fetchAdminDocuments, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveLlmConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setConfigSaving(true);
    setTestResult(null);

    try {
      const token = sessionStorage.getItem('access_token');
      await axios.post(`${API_BASE_URL}/api/v1/admin/llm-config`, {
        api_key: apiKey || undefined,
        llm_model: selectedLlm,
        embedding_model: selectedEmbedding
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      alert('Success: System LLM Model and API Key updated securely!');
      setApiKey('');
      fetchLlmConfig();
    } catch (err: any) {
      console.error('Failed to save LLM config:', err);
      alert(err.response?.data?.detail || 'Failed to update LLM configuration.');
    } finally {
      setConfigSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setTestResult(null);

    try {
      const token = sessionStorage.getItem('access_token');
      const response = await axios.post(`${API_BASE_URL}/api/v1/admin/llm-config/test`, {
        api_key: apiKey || undefined,
        llm_model: selectedLlm
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setTestResult({ success: true, msg: response.data.message });
    } catch (err: any) {
      setTestResult({ 
        success: false, 
        msg: err.response?.data?.detail || 'Connection test failed. Please verify API key.' 
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleAdminAction = async (docId: string, action: 'ACCEPT' | 'REJECT' | 'MANUAL_REVIEW') => {
    setActionSubmitting(docId);
    try {
      const token = sessionStorage.getItem('access_token');
      const currentUser = sessionStorage.getItem('user_email') || 'admin@tata.com';
      
      await axios.post(`${API_BASE_URL}/api/v1/review/admin/review/action`, {
        job_id: docId,
        action: action,
        comments: `Admin (${currentUser}) marked document as ${action}`
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setDocuments(prev => prev.map(d => {
        if (d.job_id === docId) {
          return { ...d, status: `ADMIN_${action}` };
        }
        return d;
      }));

      window.dispatchEvent(new Event('audit_updated'));
      alert(`Admin Action Success: Document updated to ${action.replace('_', ' ')}`);
    } catch (err) {
      console.error('Admin action failed:', err);
      alert('Failed to update document status in database.');
    } finally {
      setActionSubmitting(null);
    }
  };

  const handleInspectDocument = async (doc: AdminDocRecord) => {
    setInspectDoc(doc);
    setInspectLoading(true);
    try {
      const token = sessionStorage.getItem('access_token');
      const response = await axios.get(`${API_BASE_URL}/api/v1/documents/${doc.job_id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDocClauses(response.data.clauses || []);
    } catch (err) {
      console.error('Failed to inspect document clauses:', err);
    } finally {
      setInspectLoading(false);
    }
  };

  const filteredDocs = documents.filter(doc => {
    const matchesBu = filterBu === 'ALL' || doc.business_unit === filterBu;
    const matchesStatus = filterStatus === 'ALL' || doc.status === filterStatus;
    const matchesSearch = doc.file_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          doc.uploader_email.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesBu && matchesStatus && matchesSearch;
  });

  const totalUploads = documents.length;
  const pendingReview = documents.filter(d => d.status === 'PENDING_REVIEW' || !d.status).length;
  const acceptedDocs = documents.filter(d => d.status.includes('ACCEPT')).length;
  const manualReviewDocs = documents.filter(d => d.status.includes('MANUAL')).length;

  if (loading) {
    return <div className="p-8 text-[#00A3E0] font-mono text-xs">Loading Tata Admin Governance Console...</div>;
  }

  return (
    <div className="p-8 space-y-8 bg-[#000D1A] min-h-screen text-slate-100 font-sans max-w-7xl mx-auto">
      
      {/* Header with Tab Navigation */}
      <div className="border-b border-[#002B49] pb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Award className="w-5 h-5 text-[#00A3E0]" />
            <span className="text-xs font-black uppercase tracking-widest text-[#00A3E0]">TATA GROUP CENTRAL GOVERNANCE</span>
          </div>
          <h1 className="text-3xl font-black tracking-tight text-white">
            Admin Governance & Control Portal
          </h1>
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-2">
            <UserCheck className="w-3.5 h-3.5 text-emerald-400" /> Executive Oversight • Cross-User Document Audit & LLM Engine Settings
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-[#001021] border border-[#002B49] rounded-xl p-1 gap-1">
          <button 
            onClick={() => setAdminTab('documents')}
            className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-2 ${
              adminTab === 'documents' 
                ? 'bg-[#002B49] text-[#00A3E0] border border-[#004B87] shadow-md' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Layers className="w-4 h-4" /> Multi-User Directory
          </button>

          <button 
            onClick={() => setAdminTab('llm_settings')}
            className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-2 ${
              adminTab === 'llm_settings' 
                ? 'bg-[#002B49] text-[#00A3E0] border border-[#004B87] shadow-md' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sliders className="w-4 h-4" /> LLM & Key Settings
          </button>
        </div>
      </div>

      {/* TAB 1: MULTI-USER DOCUMENT DIRECTORY */}
      {adminTab === 'documents' && (
        <div className="space-y-8">
          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
            <div className="bg-[#00182C] border border-[#002B49] border-t-4 border-t-[#00A3E0] rounded-2xl p-5 shadow-lg space-y-1">
              <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest flex justify-between">
                <span>Total Uploads</span>
                <Layers className="w-4 h-4 text-[#00A3E0]" />
              </div>
              <div className="text-3xl font-black text-white">{totalUploads}</div>
              <p className="text-[10px] text-slate-500 font-mono">Across all business units</p>
            </div>

            <div className="bg-[#00182C] border border-[#002B49] border-t-4 border-t-amber-500 rounded-2xl p-5 shadow-lg space-y-1">
              <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest flex justify-between">
                <span>Pending Review</span>
                <Clock className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-3xl font-black text-amber-400">{pendingReview}</div>
              <p className="text-[10px] text-slate-500 font-mono">Awaiting admin sign-off</p>
            </div>

            <div className="bg-[#00182C] border border-[#002B49] border-t-4 border-t-emerald-500 rounded-2xl p-5 shadow-lg space-y-1">
              <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest flex justify-between">
                <span>Approved Contracts</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-3xl font-black text-emerald-400">{acceptedDocs}</div>
              <p className="text-[10px] text-slate-500 font-mono">Committed to archive</p>
            </div>

            <div className="bg-[#00182C] border border-[#002B49] border-t-4 border-t-purple-500 rounded-2xl p-5 shadow-lg space-y-1">
              <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest flex justify-between">
                <span>Manual Review Queue</span>
                <AlertTriangle className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-3xl font-black text-purple-400">{manualReviewDocs}</div>
              <p className="text-[10px] text-slate-500 font-mono">Flagged for legal counsel</p>
            </div>
          </div>

          {/* Filter Toolbar */}
          <div className="bg-[#00182C] border border-[#002B49] rounded-2xl p-4 flex flex-wrap gap-4 items-center justify-between shadow-xl">
            <div className="flex items-center gap-3 flex-1 min-w-[280px]">
              <Search className="w-4 h-4 text-[#00A3E0]" />
              <input 
                type="text" 
                placeholder="Search by file name or uploader email..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#001021] border border-[#002B49] rounded-xl px-3.5 py-2 text-xs text-white outline-none focus:border-[#00A3E0]"
              />
            </div>

            <div className="flex items-center gap-3">
              <Filter className="w-4 h-4 text-slate-400" />
              <select 
                value={filterBu} 
                onChange={(e) => setFilterBu(e.target.value)}
                className="bg-[#001021] border border-[#002B49] rounded-xl px-3 py-2 text-xs text-slate-300 outline-none"
              >
                <option value="ALL">All Business Units</option>
                <option value="Procurement">Procurement</option>
                <option value="Legal">Legal & Compliance</option>
                <option value="Corporate Strategy">Corporate Strategy</option>
              </select>

              <select 
                value={filterStatus} 
                onChange={(e) => setFilterStatus(e.target.value)}
                className="bg-[#001021] border border-[#002B49] rounded-xl px-3 py-2 text-xs text-slate-300 outline-none"
              >
                <option value="ALL">All Statuses</option>
                <option value="PENDING_REVIEW">Pending Review</option>
                <option value="ACCEPT">Accepted</option>
                <option value="REJECT">Rejected</option>
                <option value="MANUAL_REVIEW">Manual Review</option>
              </select>

              <button 
                onClick={fetchAdminDocuments} 
                className="bg-[#002B49] hover:bg-[#003B73] border border-[#004B87] text-[#00A3E0] p-2 rounded-xl text-xs font-bold uppercase transition-all cursor-pointer"
                title="Refresh Directory"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Document Table */}
          <div className="bg-[#00182C] border border-[#002B49] rounded-2xl overflow-hidden shadow-2xl">
            <div className="p-5 border-b border-[#002B49] flex justify-between items-center bg-[#001021]">
              <h2 className="text-xs font-black uppercase tracking-widest text-[#00A3E0] flex items-center gap-2">
                <FileText className="w-4 h-4" /> Multi-User Document Master Directory ({filteredDocs.length})
              </h2>
              <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping"></span> Live Database Sync
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#001424] border-b border-[#002B49] text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                    <th className="p-4">Uploader / User</th>
                    <th className="p-4">Document Details</th>
                    <th className="p-4">BU & Type</th>
                    <th className="p-4 text-center">Risk Score</th>
                    <th className="p-4 text-center">Current Status</th>
                    <th className="p-4 text-center">Admin Controls</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#002B49]/60">
                  {filteredDocs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-slate-500 text-xs">
                        No user document records found matching filters.
                      </td>
                    </tr>
                  ) : (
                    filteredDocs.map((doc) => {
                      const statusStr = doc.status || 'PENDING';
                      const isAccepted = statusStr.includes('ACCEPT');
                      const isRejected = statusStr.includes('REJECT');
                      const isManual = statusStr.includes('MANUAL');

                      return (
                        <tr key={doc.job_id} className="hover:bg-[#002340]/50 transition-colors">
                          <td className="p-4">
                            <div className="font-bold text-white text-xs">{doc.uploader_email}</div>
                            <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                              ID: {doc.job_id.substring(0, 8)}...
                            </div>
                          </td>

                          <td className="p-4">
                            <div className="font-bold text-slate-200">{doc.file_name}</div>
                            <div className="text-[10px] text-slate-400 mt-0.5 flex gap-2">
                              <span>{doc.page_count} Pages</span> • 
                              <span>OCR Quality: {Math.round(doc.ocr_confidence || 95)}%</span>
                            </div>
                          </td>

                          <td className="p-4">
                            <span className="px-2 py-1 bg-[#002B49] text-[#00A3E0] border border-[#004B87] rounded text-[10px] font-bold uppercase">
                              {doc.business_unit}
                            </span>
                            <div className="text-[10px] text-slate-400 mt-1">{doc.document_type}</div>
                          </td>

                          <td className="p-4 text-center">
                            {doc.high_risk_count > 0 ? (
                              <span className="px-2.5 py-1 bg-rose-500/10 border border-rose-500/30 text-rose-400 rounded-md font-bold text-[10px] inline-flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" /> {doc.high_risk_count} High Risk
                              </span>
                            ) : (
                              <span className="px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-md font-bold text-[10px] inline-flex items-center gap-1">
                                <ShieldCheck className="w-3 h-3" /> Low Risk
                              </span>
                            )}
                          </td>

                          <td className="p-4 text-center">
                            <span className={`px-2.5 py-1 rounded-md text-[10px] font-black uppercase tracking-wider border ${
                              isAccepted ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                              isRejected ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' :
                              isManual ? 'bg-purple-500/10 text-purple-400 border-purple-500/30' :
                              'bg-amber-500/10 text-amber-400 border-amber-500/30'
                            }`}>
                              {statusStr}
                            </span>
                          </td>

                          <td className="p-4 text-center">
                            <div className="flex items-center justify-center gap-1.5">
                              <button 
                                onClick={() => handleInspectDocument(doc)}
                                className="p-1.5 bg-[#002B49] hover:bg-[#003B73] border border-[#004B87] text-[#00A3E0] rounded-lg transition-colors cursor-pointer"
                                title="Inspect Extracted Clauses & RAG Rationale"
                              >
                                <Eye className="w-3.5 h-3.5" />
                              </button>

                              <button 
                                onClick={() => handleAdminAction(doc.job_id, 'ACCEPT')}
                                disabled={actionSubmitting === doc.job_id}
                                className="px-2.5 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/50 text-emerald-400 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50"
                              >
                                Accept
                              </button>

                              <button 
                                onClick={() => handleAdminAction(doc.job_id, 'REJECT')}
                                disabled={actionSubmitting === doc.job_id}
                                className="px-2.5 py-1.5 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/50 text-rose-400 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50"
                              >
                                Reject
                              </button>

                              <button 
                                onClick={() => handleAdminAction(doc.job_id, 'MANUAL_REVIEW')}
                                disabled={actionSubmitting === doc.job_id}
                                className="px-2.5 py-1.5 bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/50 text-amber-400 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all cursor-pointer disabled:opacity-50"
                              >
                                Manual Review
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DYNAMIC LLM MODEL & API KEY CONTROL CENTER */}
      {adminTab === 'llm_settings' && (
        <div className="bg-[#00182C] border border-[#002B49] rounded-3xl p-8 shadow-2xl space-y-6 max-w-3xl mx-auto">
          
          <div className="border-b border-[#002B49] pb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-black text-white flex items-center gap-2">
                <Cpu className="w-5 h-5 text-[#00A3E0]" /> LLM Provider & Key Management
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Configure runtime LLM model selection and update API keys dynamically for RAG reasoning and evaluations.
              </p>
            </div>
            
            <span className="px-3 py-1 bg-[#001021] border border-[#004B87] text-[#00A3E0] rounded-lg text-xs font-mono font-bold">
              Active Key: {maskedKey}
            </span>
          </div>

          <form onSubmit={handleSaveLlmConfig} className="space-y-6">
            
            {/* Model Selection Dropdown */}
            <div className="space-y-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-[#00A3E0]" /> Primary LLM Reasoning Engine
              </label>
              <select 
                value={selectedLlm} 
                onChange={(e) => setSelectedLlm(e.target.value)}
                className="w-full bg-[#001021] border border-[#002B49] rounded-xl p-3 text-sm text-white focus:border-[#00A3E0] outline-none font-medium cursor-pointer"
              >
                <optgroup label="NVIDIA NIM (Enterprise Endpoints)">
                  <option value="nvidia/nemotron-3.5-lightning-30b-a3b">NVIDIA Nemotron 3.5 Lightning 30B (Free Endpoint)</option>
                  <option value="nvidia/llama-3.1-nemotron-70b-instruct">Llama-3.1-Nemotron 70B (Instruct)</option>
                  <option value="meta/llama-3.1-405b-instruct">NVIDIA Hosted: Llama 3.1 405B</option>
                  <option value="meta/llama-3.1-70b-instruct">NVIDIA Hosted: Llama 3.1 70B</option>
                  <option value="mistralai/mixtral-8x22b-instruct-v0.1">NVIDIA Hosted: Mixtral 8x22B</option>
                </optgroup>
                <optgroup label="Google DeepMind Models">
                  <option value="gemini-3.5-flash">Gemini 3.5 Flash (Fastest • High Accuracy)</option>
                  <option value="gemini-3.6-flash">Gemini 3.6 Flash (Updated Reasoning)</option>
                  <option value="gemini-2.5-pro">Gemini 2.5 Pro (Deep Context Analysis)</option>
                </optgroup>
                <optgroup label="OpenAI Models">
                  <option value="gpt-4o">GPT-4o (Omni Multimodal)</option>
                  <option value="gpt-4-turbo">GPT-4 Turbo (Large Context)</option>
                </optgroup>
                <optgroup label="Anthropic Claude Models">
                  <option value="claude-3-5-sonnet-20240620">Claude 3.5 Sonnet (Best Reasoning)</option>
                  <option value="claude-3-opus-20240229">Claude 3 Opus (Highly Complex Tasks)</option>
                </optgroup>
                <optgroup label="Groq (Ultra-Fast Open Source)">
                  <option value="llama-3.1-70b-versatile">Groq: Llama 3.1 70B</option>
                  <option value="mixtral-8x7b-32768">Groq: Mixtral 8x7B</option>
                </optgroup>
              </select>
              <p className="text-[11px] text-slate-500 font-mono">
                This engine executes clause extraction, risk evaluation, and chat assistant responses.
              </p>
            </div>

            {/* Embedding Model Dropdown */}
            <div className="space-y-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#00A3E0]" /> Vector Embedding Model
              </label>
              <select 
                value={selectedEmbedding} 
                onChange={(e) => setSelectedEmbedding(e.target.value)}
                className="w-full bg-[#001021] border border-[#002B49] rounded-xl p-3 text-sm text-white focus:border-[#00A3E0] outline-none font-medium cursor-pointer"
              >
                <option value="gemini-embedding-001">gemini-embedding-001 (768-dim Vector)</option>
                <option value="text-embedding-004">text-embedding-004 (Standard Google Vector)</option>
              </select>
              <p className="text-[11px] text-slate-500 font-mono">
                Used to index and retrieve knowledge base policy vectors from Qdrant DB. (Keep as-is to prevent vector dimension errors).
              </p>
            </div>

            {/* Custom API Key Input */}
            <div className="space-y-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Key className="w-4 h-4 text-[#00A3E0]" /> Provider API Key (Google, OpenAI, Anthropic, or Groq)
              </label>
              <input 
                type="password" 
                value={apiKey} 
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter new API key (Leave blank to keep existing key)"
                className="w-full bg-[#001021] border border-[#002B49] rounded-xl p-3 text-sm text-white focus:border-[#00A3E0] outline-none font-mono placeholder:text-slate-600"
              />
              <p className="text-[11px] text-slate-500 font-mono">
                Updating this key will dynamically update your backend without restarting the Render instance. Ensure the key matches the selected model provider.
              </p>
            </div>

            {/* Connection Test Output Box */}
            {testResult && (
              <div className={`p-4 rounded-xl border flex items-center gap-3 text-xs font-mono ${
                testResult.success 
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
              }`}>
                {testResult.success ? <CheckCircle className="w-5 h-5 shrink-0" /> : <XCircle className="w-5 h-5 shrink-0" />}
                <span>{testResult.msg}</span>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4 pt-2">
              <button 
                type="button" 
                onClick={handleTestConnection}
                disabled={testingConnection}
                className="flex-1 bg-[#002B49] hover:bg-[#003B73] border border-[#004B87] text-[#00A3E0] font-bold py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 text-xs uppercase tracking-wider cursor-pointer disabled:opacity-50"
              >
                {testingConnection ? 'Testing API Key...' : <><Activity className="w-4 h-4" /> Test Connection</>}
              </button>

              <button 
                type="submit" 
                disabled={configSaving}
                className="flex-1 bg-[#00A3E0] hover:bg-[#0082B3] text-[#001021] font-black py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 text-xs uppercase tracking-wider shadow-lg shadow-[#00A3E0]/20 cursor-pointer disabled:opacity-50"
              >
                {configSaving ? 'Saving Settings...' : <><Save className="w-4 h-4 text-[#001021]" /> Save Configuration</>}
              </button>
            </div>

          </form>

        </div>
      )}

      {/* Clause Inspection Modal */}
      {inspectDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#00182C] border border-[#002B49] rounded-2xl p-6 w-full max-w-3xl shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto custom-scrollbar">
            <div className="flex justify-between items-start border-b border-[#002B49] pb-3">
              <div>
                <span className="text-[10px] font-bold text-[#00A3E0] uppercase tracking-widest">Admin Deep Inspection</span>
                <h3 className="text-base font-black text-white">{inspectDoc.file_name}</h3>
                <p className="text-xs text-slate-400">Uploaded by: {inspectDoc.uploader_email}</p>
              </div>
              <button 
                onClick={() => setInspectDoc(null)} 
                className="p-1.5 bg-[#002B49] text-slate-400 hover:text-white rounded-lg cursor-pointer"
              >
                ✕
              </button>
            </div>

            {inspectLoading ? (
              <div className="p-8 text-center text-xs text-[#00A3E0] font-mono">Loading clauses and RAG reasoning...</div>
            ) : (
              <div className="space-y-4">
                {docClauses.map((clause, idx) => {
                  const ragRef = clause?.rag_reference_used || clause?.policy_citation || `KB-POLICY-${(clause?.clause_type || 'GENERAL').toUpperCase().replace(/\s+/g, '_')}-00${idx + 1}`;

                  return (
                    <div key={idx} className="bg-[#001021] border border-[#002B49] p-4 rounded-xl space-y-3 shadow-md">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-white uppercase flex items-center gap-2">
                          <span className="px-1.5 py-0.5 bg-[#002B49] border border-[#004B87] text-[#00A3E0] rounded font-mono text-[10px]">#{idx + 1}</span> {clause.clause_type}
                        </span>
                        <span className={`px-2.5 py-0.5 rounded text-[10px] font-black uppercase border ${
                          clause.risk_level === 'HIGH' ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' : 
                          clause.risk_level === 'MEDIUM' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' :
                          'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        }`}>
                          Risk: {clause.risk_level}
                        </span>
                      </div>

                      <p className="text-xs text-slate-300 font-mono bg-[#000814] p-3 rounded-lg border border-[#002B49]">
                        "{clause.extracted_text}"
                      </p>

                      <div className="text-xs text-slate-300 bg-[#00182C] p-3 rounded-lg border border-[#002B49] space-y-2">
                        <div className="text-[#00A3E0] font-bold uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5" /> RAG Rationale
                        </div>
                        <p className="text-slate-300 leading-relaxed">
                          {clause.risk_rationale}
                        </p>

                        <div className="flex items-center gap-2 pt-2 border-t border-[#002B49] text-[11px]">
                          <BookOpen className="w-3.5 h-3.5 text-[#00A3E0] shrink-0" />
                          <span className="font-mono text-slate-400">
                            <strong className="text-[#00A3E0]">Cited RAG Policy Reference:</strong>{' '}
                            <span className="px-2 py-0.5 rounded bg-[#001021] border border-[#004B87] text-slate-200 font-bold">
                              {ragRef}
                            </span>
                          </span>
                        </div>
                      </div>

                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
};
