import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, CheckCircle2, ShieldAlert, Download, ArrowRight, Zap, AlertTriangle, ArchiveX, CheckCircle, XCircle } from 'lucide-react';
const API_BASE_URL = 'https://tata-ai-backend-og7t.onrender.com';

interface DocumentWorkspaceProps {
  selectedHistoryJobId?: string | null;
  _onActiveJobChange?: (jobId: string) => void; 
}

// FIX: Deep Scan LocalStorage to automatically find the REAL logged-in user's email
const getSessionUser = () => {
  const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/;
  const keys = ['user_email', 'email', 'user', 'currentUser', 'session', 'auth'];
  for (const k of keys) {
    const val = localStorage.getItem(k) || sessionStorage.getItem(k);
    if (val) {
      const match = val.match(emailRegex);
      if (match) return match[1];
    }
  }
  for (let i = 0; i < localStorage.length; i++) {
    const val = localStorage.getItem(localStorage.key(i) || '');
    if (val) {
      const match = val.match(emailRegex);
      if (match) return match[1];
    }
  }
  return "demo1@tata.com";
};

export const DocumentWorkspace: React.FC<DocumentWorkspaceProps> = ({ selectedHistoryJobId, _onActiveJobChange }) => {
  const [file, setFile] = useState<File | null>(null);
  const [businessUnit, setBusinessUnit] = useState('Procurement');
  const [category, setCategory] = useState('Vendor Agreement');
  
  const [documentType, setDocumentType] = useState('Master Services Agreement');
  const [counterparty, setCounterparty] = useState('');
  const [jurisdiction, setJurisdiction] = useState('Global');
  
  const [confidentiality, setConfidentiality] = useState('Confidential');
  const [priority, setPriority] = useState('High');
  const [loading, setLoading] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [clauses, setClauses] = useState<any[]>([]);

  const [reviewStatus, setReviewStatus] = useState<string | null>(null);
  const [reviewComments, setReviewComments] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const currentUser = getSessionUser(); // REAL LOGGED-IN USER

  useEffect(() => {
    if (selectedHistoryJobId) {
      loadDocumentFromHistory(selectedHistoryJobId);
    }
  }, [selectedHistoryJobId]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      alert('Please select a document file first.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('business_unit', businessUnit);
    formData.append('document_category', category);
    formData.append('document_type', documentType);
    formData.append('counterparty', counterparty || 'Unknown');
    formData.append('jurisdiction', jurisdiction || 'Global');
    formData.append('confidentiality_level', confidentiality);
    formData.append('review_priority', priority);
    
    // Pass the real authenticated user to backend database
    formData.append('user_email', currentUser);
    formData.append('user_role', 'Compliance Officer');

    setLoading(true);
    setReviewStatus(null); 
    setReviewComments('');
    
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/documents/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const rawClauses = response.data?.clauses;
      const safeClauses = Array.isArray(rawClauses) 
        ? rawClauses.filter((c: any) => c !== null && typeof c === 'object') 
        : [];
      
      const safeMetrics = response.data?.metrics || {};

      setActiveJobId(response.data?.job_id || null);
      setAnalysisResult({ ...response.data, metrics: safeMetrics });
      setClauses(safeClauses);

    } catch (error) {
      console.error('Upload error:', error);
      alert('Failed to process document through backend pipeline.');
    } finally {
      setLoading(false);
    }
  };

  const loadDocumentFromHistory = async (jobId: string) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/documents/${jobId}`);
      
      const safeClauses = Array.isArray(response.data?.clauses) 
        ? response.data.clauses.filter((c: any) => c !== null && typeof c === 'object') 
        : [];

      setActiveJobId(response.data?.job_id || null);
      setAnalysisResult({ metrics: response.data?.metrics || {} });
      setClauses(safeClauses);
      
      setReviewStatus(null);
      setReviewComments('');
    } catch (error) {
      console.error('Failed to load document details:', error);
    }
  };

  const handleDownloadPdf = async () => {
    // Determine target job ID from props or internal state
    const targetId = selectedHistoryJobId || (typeof activeJobId !== 'undefined' ? activeJobId : null);
    
    if (!targetId) {
      alert("Please select or analyze a document first.");
      return;
    }

    const token = localStorage.getItem('access_token');
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/v1/documents/${targetId}/export-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Audit_Report_${targetId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("PDF download failed:", error);
      alert("Failed to download audit package.");
    }
  };

  const handleReviewAction = async (action: 'ACCEPT' | 'REJECT') => {
    if (!activeJobId) {
      alert("No active document to review.");
      return;
    }

    setIsSubmitting(true);
    try {
      await axios.post(`${API_BASE_URL}/api/v1/review/actions`, {
        document_id: activeJobId,
        user_email: currentUser, // Ensure review matches dynamic user
        action: action,
        file_name: file?.name || "Analyzed Document",
        comments: reviewComments
      });

      setReviewStatus(action);
      alert(`Success: Document ${action.toLowerCase()}ed and securely archived to history!`);
    } catch (error) {
      console.error("Audit logging failed:", error);
      alert("Failed to record review action. Please check the backend connection.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-8 space-y-8 min-h-screen text-slate-300 font-sans max-w-7xl mx-auto">
      
      <div className="border-b border-slate-800/80 pb-6">
        <h1 className="text-3xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400">
          Tata AI Legal Intelligence
        </h1>
        <p className="text-sm text-slate-400 mt-2 flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" /> Enterprise Document Parsing, RAG Grounding & Risk Governance Portal
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <div className="bg-slate-800/40 backdrop-blur-md border border-slate-700/60 rounded-2xl p-6 shadow-xl relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-40 h-40 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
          
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 mb-6 flex items-center gap-2">
            <Upload className="w-4 h-4 text-indigo-400" /> Upload Legal Document
          </h2>
          
          <form onSubmit={handleUpload} className="space-y-4 text-sm relative z-10">
            <div className="space-y-1.5">
              <label className="block text-slate-400 text-xs font-semibold uppercase tracking-wider">Select File</label>
              <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} className="w-full text-slate-300 bg-slate-900/50 p-2.5 rounded-xl border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-500/10 file:text-indigo-400 hover:file:bg-indigo-500/20 cursor-pointer" />
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="block text-slate-400 text-xs font-semibold uppercase tracking-wider">Business Unit</label>
                <select value={businessUnit} onChange={(e) => setBusinessUnit(e.target.value)} className="w-full bg-slate-900/50 p-3 rounded-xl border border-slate-700 text-slate-200 focus:border-indigo-500 outline-none text-xs">
                  <option value="Procurement">Procurement</option>
                  <option value="Legal">Legal & Compliance</option>
                  <option value="Corporate Strategy">Corporate Strategy</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="block text-slate-400 text-xs font-semibold uppercase tracking-wider">Category</label>
                <input type="text" value={category} onChange={(e) => setCategory(e.target.value)} className="w-full bg-slate-900/50 p-3 rounded-xl border border-slate-700 text-slate-200 focus:border-indigo-500 outline-none text-xs" />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <label className="block text-slate-400 text-[10px] font-semibold uppercase tracking-wider">Doc Type</label>
                <input type="text" value={documentType} onChange={(e) => setDocumentType(e.target.value)} placeholder="e.g. MSA" className="w-full bg-slate-900/50 p-2.5 rounded-xl border border-slate-700 text-slate-200 text-xs outline-none" />
              </div>

              <div className="space-y-1.5">
                <label className="block text-slate-400 text-[10px] font-semibold uppercase tracking-wider">Counterparty</label>
                <input type="text" value={counterparty} onChange={(e) => setCounterparty(e.target.value)} placeholder="e.g. Acme Inc" className="w-full bg-slate-900/50 p-2.5 rounded-xl border border-slate-700 text-slate-200 text-xs outline-none" />
              </div>

              <div className="space-y-1.5">
                <label className="block text-slate-400 text-[10px] font-semibold uppercase tracking-wider">Jurisdiction</label>
                <input type="text" value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} placeholder="e.g. Global" className="w-full bg-slate-900/50 p-2.5 rounded-xl border border-slate-700 text-slate-200 text-xs outline-none" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="block text-slate-400 text-xs font-semibold uppercase tracking-wider">Confidentiality</label>
                <select value={confidentiality} onChange={(e) => setConfidentiality(e.target.value)} className="w-full bg-slate-900/50 p-3 rounded-xl border border-slate-700 text-slate-200 text-xs outline-none">
                  <option value="Confidential">Confidential</option>
                  <option value="Restricted">Restricted</option>
                  <option value="Standard">Standard</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="block text-slate-400 text-xs font-semibold uppercase tracking-wider">Review Priority</label>
                <select value={priority} onChange={(e) => setPriority(e.target.value)} className="w-full bg-slate-900/50 p-3 rounded-xl border border-slate-700 text-slate-200 text-xs outline-none">
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Normal">Normal</option>
                </select>
              </div>
            </div>
            
            <button type="submit" disabled={loading} className="w-full mt-4 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold py-3.5 rounded-xl transition-all duration-300 flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 hover:shadow-indigo-600/40 hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? (
                <><CheckCircle2 className="w-5 h-5 animate-spin" /> Processing AI Pipeline...</>
              ) : (
                <>Analyze Document <ArrowRight className="w-5 h-5" /></>
              )}
            </button>
          </form>
        </div>

        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="grid grid-cols-3 gap-5">
            <div className="bg-slate-800/40 backdrop-blur-md border border-slate-700/60 border-t-emerald-500 rounded-2xl p-5 shadow-lg flex flex-col justify-between relative overflow-hidden group">
              <div className="text-slate-400 text-[10px] font-bold uppercase tracking-widest relative z-10">OCR Confidence</div>
              <div className="text-3xl font-black text-emerald-400 relative z-10 mt-2">
                {analysisResult?.metrics?.ocr_confidence ? `${Math.round(analysisResult.metrics.ocr_confidence)}%` : '—'}
              </div>
            </div>
            
            <div className="bg-slate-800/40 backdrop-blur-md border border-slate-700/60 border-t-indigo-500 rounded-2xl p-5 shadow-lg flex flex-col justify-between relative overflow-hidden group">
              <div className="text-slate-400 text-[10px] font-bold uppercase tracking-widest relative z-10">Pages Processed</div>
              <div className="text-3xl font-black text-white relative z-10 mt-2">
                {analysisResult?.metrics?.pages || '—'}
              </div>
            </div>
            
            <div className="bg-slate-800/40 backdrop-blur-md border border-slate-700/60 border-t-cyan-500 rounded-2xl p-5 shadow-lg flex flex-col justify-between relative overflow-hidden group">
              <div className="text-slate-400 text-[10px] font-bold uppercase tracking-widest relative z-10">Entities Detected</div>
              <div className="text-3xl font-black text-cyan-400 relative z-10 mt-2">
                {analysisResult?.metrics?.entities_detected || '—'}
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-r from-slate-800 to-slate-800/40 border border-slate-700/60 rounded-2xl p-6 shadow-lg flex justify-between items-center mt-auto">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" /> Executive Audit Package
              </h3>
              <p className="text-xs text-slate-400 mt-1">Download certified PDF report with AI RAG risk matrix & sign-offs.</p>
            </div>
            <button 
              onClick={handleDownloadPdf} 
              disabled={!activeJobId && !selectedHistoryJobId}
              className="bg-slate-700 hover:bg-slate-600 border border-slate-600 hover:border-slate-500 text-white px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" /> Download PDF
            </button>
          </div>
        </div>
      </div>

      <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/60 rounded-3xl p-8 shadow-2xl space-y-6">
        <div className="flex items-center gap-3 pb-2 border-b border-slate-700/50">
          <ShieldAlert className="w-6 h-6 text-indigo-400" /> 
          <h2 className="text-sm font-black uppercase tracking-widest text-slate-200">
            Extracted Legal Clauses & RAG Risk Matrix
          </h2>
        </div>
        
        <div className="space-y-5">
          {clauses.length > 0 ? (
            clauses.map((clause, idx) => {
              if (!clause) return null;
              
              const riskLevel = clause?.risk_level || 'LOW';
              const isHigh = riskLevel === 'HIGH';
              const isMed = riskLevel === 'MEDIUM';
              
              const borderLeft = isHigh ? 'border-l-rose-500' : isMed ? 'border-l-amber-500' : 'border-l-emerald-500';
              const badgeBg = isHigh ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' : isMed ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
              const icon = isHigh ? <AlertTriangle className="w-3.5 h-3.5" /> : isMed ? <ShieldAlert className="w-3.5 h-3.5" /> : <CheckCircle2 className="w-3.5 h-3.5" />;

              return (
                <div key={idx} className={`bg-slate-900/60 border border-slate-700/50 ${borderLeft} border-l-4 rounded-xl p-5 shadow-md hover:shadow-lg hover:bg-slate-900/80 transition-all space-y-4`}>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-bold tracking-wide text-white uppercase flex items-center gap-2">
                      <span className="p-1 bg-slate-800 rounded text-indigo-400">#{idx + 1}</span> {clause?.clause_type || 'General Provision'}
                    </span>
                    <span className={`px-3 py-1 rounded-md text-[10px] font-black tracking-widest border uppercase flex items-center gap-1.5 shadow-sm ${badgeBg}`}>
                      {icon} Risk: {riskLevel} ({Math.round((clause?.confidence_score || 0.9) * 100)}% Match)
                    </span>
                  </div>
                  
                  <div className="text-[13px] text-slate-300 font-mono bg-[#0B1120] p-4 rounded-lg border border-slate-800 leading-relaxed shadow-inner">
                    <span className="text-slate-500 select-none mr-2">{"// Document Extract:"}</span><br/>
                    "{clause?.extracted_text || 'No text extracted.'}"
                  </div>
                  
                  <div className="text-[13px] text-slate-300 bg-slate-800/50 p-4 rounded-lg border border-slate-700/50 space-y-3">
                    <div className="whitespace-pre-wrap leading-relaxed">
                      <strong className="text-indigo-300 text-xs uppercase tracking-widest flex items-center gap-2 mb-2">
                        <Zap className="w-3.5 h-3.5" /> AI RAG Rationale
                      </strong>
                      {clause?.risk_rationale || 'Awaiting reasoning...'}
                    </div>
                    
                    <div className="flex flex-wrap gap-4 text-xs border-t border-slate-700/50 pt-3 mt-3">
                      <span className="flex items-center gap-1.5">
                        <strong className="text-slate-400 font-medium">Involved Party:</strong> 
                        <span className="text-slate-200">{clause?.involved_party || 'N/A'}</span>
                      </span>
                      <span className="text-slate-600">|</span>
                      <span className="flex items-center gap-1.5">
                        <strong className="text-slate-400 font-medium">RAG Reference:</strong> 
                        <span className="text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">{clause?.rag_reference_used || 'Standard Policy'}</span>
                      </span>
                    </div>
                  </div>
                  
                </div>
              );
            })
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-center bg-slate-900/40 rounded-2xl border border-dashed border-slate-700">
              <ShieldAlert className="w-12 h-12 text-slate-600 mb-4" />
              <h3 className="text-slate-300 font-bold mb-1">No clauses extracted yet</h3>
              <p className="text-slate-500 text-sm max-w-sm">Upload and analyze a document above to generate the RAG risk matrix and compliance overview.</p>
            </div>
          )}
        </div>
      </div>

      {activeJobId && clauses.length > 0 && (
        <div className="bg-[#0F172A] border border-slate-700/60 rounded-3xl p-8 shadow-2xl mt-8">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <ArchiveX className="w-5 h-5 text-indigo-400" />
            Final Review & Audit Sign-Off
          </h3>
          
          {reviewStatus ? (
            <div className={`p-5 rounded-xl flex items-center gap-4 ${reviewStatus === 'ACCEPT' ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border border-rose-500/30 text-rose-400'}`}>
              {reviewStatus === 'ACCEPT' ? <CheckCircle className="w-8 h-8" /> : <XCircle className="w-8 h-8" />}
              <div>
                <p className="font-bold text-sm tracking-wide">Document {reviewStatus}ED</p>
                <p className="text-xs opacity-80 mt-1">This decision and rationale have been permanently recorded in the audit archive.</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <textarea
                placeholder="Enter rationale or comments for the audit log..."
                value={reviewComments}
                onChange={(e) => setReviewComments(e.target.value)}
                className="w-full bg-[#162032] border border-slate-700 rounded-xl p-4 text-sm text-white focus:border-indigo-500 outline-none min-h-[100px] resize-none"
              />
              <div className="flex gap-4">
                <button 
                  onClick={() => handleReviewAction('ACCEPT')}
                  disabled={isSubmitting}
                  className="flex-1 bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/50 text-emerald-400 font-bold py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <CheckCircle className="w-5 h-5" /> Accept Document
                </button>
                <button 
                  onClick={() => handleReviewAction('REJECT')}
                  disabled={isSubmitting}
                  className="flex-1 bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/50 text-rose-400 font-bold py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <XCircle className="w-5 h-5" /> Reject Document
                </button>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
};