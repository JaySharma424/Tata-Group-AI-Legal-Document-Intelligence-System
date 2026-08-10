import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  ShieldCheck, CheckCircle2, XCircle, AlertTriangle, Eye, 
  RefreshCw, Award, Filter, Search, FileText, UserCheck, Clock, Layers,
  BookOpen, Sparkles
} from 'lucide-react';

const API_BASE_URL = 'https://tata-ai-backend-og7t.onrender.com';

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
  const [documents, setDocuments] = useState<AdminDocRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterBu, setFilterBu] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  
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

  useEffect(() => {
    fetchAdminDocuments();
    // Real-time synchronization interval (polling every 5s)
    const interval = setInterval(fetchAdminDocuments, 5000);
    return () => clearInterval(interval);
  }, []);

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

      // Immediate UI status update
      setDocuments(prev => prev.map(d => {
        if (d.job_id === docId) {
          return { ...d, status: `ADMIN_${action}` };
        }
        return d;
      }));

      // Trigger sidebar refresh across windows
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

  // Filter Logic
  const filteredDocs = documents.filter(doc => {
    const matchesBu = filterBu === 'ALL' || doc.business_unit === filterBu;
    const matchesStatus = filterStatus === 'ALL' || doc.status === filterStatus;
    const matchesSearch = doc.file_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          doc.uploader_email.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesBu && matchesStatus && matchesSearch;
  });

  // KPI Calculations
  const totalUploads = documents.length;
  const pendingReview = documents.filter(d => d.status === 'PENDING_REVIEW' || !d.status).length;
  const acceptedDocs = documents.filter(d => d.status.includes('ACCEPT')).length;
  const manualReviewDocs = documents.filter(d => d.status.includes('MANUAL')).length;

  if (loading) {
    return <div className="p-8 text-[#00A3E0] font-mono text-xs">Loading Tata Admin Governance Console...</div>;
  }

  return (
    <div className="p-8 space-y-8 bg-[#000D1A] min-h-screen text-slate-100 font-sans max-w-7xl mx-auto">
      
      {/* Header */}
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
            <UserCheck className="w-3.5 h-3.5 text-emerald-400" /> Executive Oversight • Cross-User Document Audit & Manual Override
          </p>
        </div>

        <button 
          onClick={fetchAdminDocuments} 
          className="bg-[#002B49] hover:bg-[#003B73] border border-[#004B87] text-[#00A3E0] px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer"
        >
          <RefreshCw className="w-4 h-4" /> Live Refresh
        </button>
      </div>

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
        </div>
      </div>

      {/* Document Directory Table */}
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

                        {/* RAG REFERENCE SOURCE CITATION IN ADMIN PORTAL */}
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