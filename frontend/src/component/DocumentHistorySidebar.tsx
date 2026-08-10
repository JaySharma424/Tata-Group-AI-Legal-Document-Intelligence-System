import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { History, FileText, CheckCircle, XCircle, RefreshCw, AlertCircle } from 'lucide-react';

interface HistoryItem {
  id: string;
  document_id: string;
  file_name: string;
  action: string;
  timestamp: string;
  reviewer_email?: string;
}

interface SidebarProps {
  onSelectDocument?: (jobId: string) => void;
}

const API_BASE_URL = 'https://tata-ai-backend-og7t.onrender.com';

export const DocumentHistorySidebar: React.FC<SidebarProps> = ({ onSelectDocument }) => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    try {
      const token = sessionStorage.getItem('access_token');
      const response = await axios.get(`${API_BASE_URL}/api/v1/review/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(response.data?.history || []);
    } catch (error) {
      console.error('Failed to load document history:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();

    // 1. Listen for instant updates when Accept/Reject/Upload happens
    const handleAuditUpdate = () => fetchHistory();
    window.addEventListener('audit_updated', handleAuditUpdate);

    // 2. Poll every 5 seconds for live database sync
    const interval = setInterval(fetchHistory, 5000);

    return () => {
      window.removeEventListener('audit_updated', handleAuditUpdate);
      clearInterval(interval);
    };
  }, []);

  // Helper to format ISO timestamps cleanly (e.g., Aug 11, 03:15 AM)
  const formatTimestamp = (rawTs: string) => {
    if (!rawTs) return 'Just now';
    try {
      const date = new Date(rawTs);
      if (isNaN(date.getTime())) return rawTs;
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      }) + ', ' + date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return rawTs;
    }
  };

  return (
    <aside className="w-72 bg-[#001021] border-r border-[#002B49] flex flex-col h-full text-slate-300 font-sans select-none shrink-0">
      
      {/* Sidebar Header */}
      <div className="p-4 border-b border-[#002B49] flex items-center justify-between bg-[#001426]">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-[#002B49] rounded-lg border border-[#004B87]">
            <History className="w-4 h-4 text-[#00A3E0]" />
          </div>
          <div>
            <h2 className="text-xs font-black text-white tracking-wider uppercase">TATA GROUP</h2>
            <p className="text-[10px] font-bold text-[#00A3E0] uppercase tracking-widest">Audit & History Archive</p>
          </div>
        </div>
        <button 
          onClick={fetchHistory} 
          className="p-1.5 hover:bg-[#002B49] text-slate-400 hover:text-[#00A3E0] rounded-lg transition-colors cursor-pointer"
          title="Refresh History"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-[#00A3E0]' : ''}`} />
        </button>
      </div>

      {/* History Items Container */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 custom-scrollbar">
        {history.length === 0 ? (
          <div className="text-center py-10 px-4 space-y-2">
            <FileText className="w-8 h-8 text-slate-600 mx-auto opacity-50" />
            <p className="text-xs text-slate-400 font-bold">No Audit History</p>
            <p className="text-[10px] text-slate-500">Processed contracts will log here automatically.</p>
          </div>
        ) : (
          history.map((item) => {
            const actionUpper = item.action.toUpperCase();
            const isAccept = actionUpper.includes('ACCEPT');
            const isReject = actionUpper.includes('REJECT');
            const isManual = actionUpper.includes('MANUAL') || actionUpper.includes('ESCALATE');

            return (
              <div 
                key={item.id}
                onClick={() => onSelectDocument && onSelectDocument(item.document_id)}
                className="bg-[#00182C] hover:bg-[#002340] border border-[#002B49] hover:border-[#004B87] p-3 rounded-xl transition-all cursor-pointer shadow-md space-y-2 group"
              >
                <div className="flex items-start gap-2">
                  <FileText className="w-4 h-4 text-[#00A3E0] shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-white truncate group-hover:text-[#00A3E0] transition-colors">
                      {item.file_name}
                    </p>
                    <p className="text-[9px] font-mono text-slate-500 truncate mt-0.5">
                      ID: {item.document_id}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1 border-t border-[#002B49]/60">
                  <span className={`px-2 py-0.5 rounded text-[9px] font-black tracking-widest uppercase border flex items-center gap-1 ${
                    isAccept ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                    isReject ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' :
                    isManual ? 'bg-purple-500/10 text-purple-400 border-purple-500/30' :
                    'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  }`}>
                    {isAccept ? <CheckCircle className="w-2.5 h-2.5" /> : isReject ? <XCircle className="w-2.5 h-2.5" /> : <AlertCircle className="w-2.5 h-2.5" />}
                    {actionUpper}
                  </span>

                  <span className="text-[10px] text-slate-400 font-mono">
                    {formatTimestamp(item.timestamp)}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="p-3 border-t border-[#002B49] bg-[#001426] text-[10px] text-slate-500 font-mono text-center">
        🔒 ENTERPRISE AUDIT TRAIL LOG
      </div>
    </aside>
  );
};