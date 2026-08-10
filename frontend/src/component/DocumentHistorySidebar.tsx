import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { FileText, CheckCircle, XCircle, RefreshCw, Award, ShieldCheck, Clock } from 'lucide-react';

interface SidebarProps {
  userEmail?: string;
  refreshTrigger?: number;
  onSelectDocument: (jobId: string) => void;
}

interface AuditRecord {
  id: string;
  document_id: string;
  file_name: string;
  action: 'ACCEPT' | 'REJECT' | 'ESCALATE';
  timestamp: string;
  reviewer_email: string;
}

const getSessionUser = () => {
  const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/;
  const keys = ['user_email', 'email', 'user', 'currentUser', 'session', 'auth'];
  for (const k of keys) {
    const val = sessionStorage.getItem(k) || sessionStorage.getItem(k);
    if (val) {
      const match = val.match(emailRegex);
      if (match) return match[1];
    }
  }
  for (let i = 0; i < sessionStorage.length; i++) {
    const val = sessionStorage.getItem(sessionStorage.key(i) || '');
    if (val) {
      const match = val.match(emailRegex);
      if (match) return match[1];
    }
  }
  return "demo1@tata.com";
};

export const DocumentHistorySidebar: React.FC<SidebarProps> = ({ onSelectDocument }) => {
  const [history, setHistory] = useState<AuditRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const currentUser = getSessionUser();

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const API_BASE_URL = 'https://tata-ai-backend-og7t.onrender.com';
      const response = await axios.get(`${API_BASE_URL}/api/v1/review/history`);
      setHistory(response.data.history || []);
    } catch (error) {
      console.error("Failed to fetch document history:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 5000); 
    return () => clearInterval(interval);
  }, [currentUser]); 

  const formatDate = (isoString: string) => {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat('en-US', { 
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
    }).format(date);
  };

  return (
    <div className="w-80 bg-[#001021] border-r border-[#002B49] h-screen flex flex-col font-sans select-none shadow-2xl z-10">
      
      {/* Tata Corporate Sidebar Header */}
      <div className="p-5 border-b border-[#002B49] bg-[#00182C] space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-[#002B49] rounded-lg border border-[#004B87]">
              <Award className="w-4 h-4 text-[#00A3E0]" />
            </div>
            <div>
              <span className="text-[9px] font-black uppercase tracking-widest text-[#00A3E0] block leading-none">
                TATA GROUP
              </span>
              <h2 className="text-xs font-bold text-white tracking-tight mt-0.5">
                Audit & History Archive
              </h2>
            </div>
          </div>

          <button 
            onClick={fetchHistory} 
            title="Refresh History"
            className={`p-1.5 bg-[#002B49] border border-[#004B87] text-slate-300 hover:text-white rounded-lg transition-all cursor-pointer ${isLoading ? 'animate-spin' : ''}`}
          >
            <RefreshCw className="w-3.5 h-3.5 text-[#00A3E0]" />
          </button>
        </div>

        <div className="bg-[#001021] p-2.5 rounded-xl border border-[#002B49] flex items-center justify-between">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <ShieldCheck className="w-3 h-3 text-[#00A3E0]" /> Reviewer Scoped
          </span>
          <span className="text-[10px] font-mono text-[#00A3E0] truncate max-w-[120px]" title={currentUser}>
            {currentUser}
          </span>
        </div>
      </div>

      {/* History Cards Container */}
      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-3">
        {history.length === 0 ? (
          <div className="text-center p-8 border border-dashed border-[#002B49] rounded-2xl bg-[#00182C]">
            <Clock className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400 font-bold">No Audit History</p>
            <p className="text-[10px] text-slate-500 mt-1">Processed contracts will log here automatically.</p>
          </div>
        ) : (
          history.map((record) => {
            const isApproved = record.action === 'ACCEPT';
            
            return (
              <div 
                key={record.id}
                onClick={() => onSelectDocument(record.document_id)} 
                className="bg-[#00182C] border border-[#002B49] hover:border-[#00A3E0]/50 rounded-xl p-3.5 shadow-lg hover:bg-[#002340] transition-all duration-200 cursor-pointer group relative overflow-hidden"
              >
                {/* Active Hover Glow */}
                <div className="absolute top-0 left-0 bottom-0 w-1 bg-[#00A3E0] opacity-0 group-hover:opacity-100 transition-opacity"></div>

                <div className="flex items-start justify-between gap-2 mb-2.5">
                  <div className="flex items-start gap-2 overflow-hidden">
                    <div className="p-1 bg-[#001021] rounded border border-[#002B49] mt-0.5 shrink-0">
                      <FileText className="w-3.5 h-3.5 text-[#00A3E0]" />
                    </div>
                    <span className="text-xs font-bold text-slate-200 group-hover:text-white line-clamp-2 leading-tight">
                      {record.file_name}
                    </span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between pt-2 border-t border-[#002B49]/60 text-[10px]">
                  <span className={`font-black px-2 py-0.5 rounded-md uppercase tracking-wider flex items-center gap-1 border ${
                    isApproved 
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  }`}>
                    {isApproved ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                    {record.action}
                  </span>
                  <span className="text-slate-400 font-mono font-medium">
                    {formatDate(record.timestamp)}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer System Badge */}
      <div className="p-3 bg-[#00182C] border-t border-[#002B49] text-center">
        <p className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">
          Tata Corporate Security • Encrypted
        </p>
      </div>

    </div>
  );
};