import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { History, FileText, CheckCircle, XCircle, RefreshCw } from 'lucide-react';


interface SidebarProps {
  userEmail?: string;       // <-- Optional add kiya
  refreshTrigger?: number;  // <-- Optional add kiya
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

// FIX: Deep Scan LocalStorage to automatically find the REAL logged-in user's email
const getSessionUser = () => {
  const emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/;
  
  // 1. First check common keys
  const keys = ['user_email', 'email', 'user', 'currentUser', 'session', 'auth'];
  for (const k of keys) {
    const val = localStorage.getItem(k) || sessionStorage.getItem(k);
    if (val) {
      const match = val.match(emailRegex);
      if (match) return match[1];
    }
  }

  // 2. If not found, deep scan all storage
  for (let i = 0; i < localStorage.length; i++) {
    const val = localStorage.getItem(localStorage.key(i) || '');
    if (val) {
      const match = val.match(emailRegex);
      if (match) return match[1];
    }
  }
  
  return "demo1@tata.com"; // Fallback if no user is logged in
};

export const DocumentHistorySidebar: React.FC<SidebarProps> = ({ onSelectDocument }) => {
  const [history, setHistory] = useState<AuditRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const currentUser = getSessionUser(); // REAL LOGGED-IN USER

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      // Clean request relying entirely on the JWT token in the Axios authorization header
      const response = await axios.get('http://localhost:8000/api/v1/review/history');
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
    <div className="w-72 bg-[#0F172A] border-r border-slate-700/60 h-screen flex flex-col">
      <div className="p-5 border-b border-slate-700/60 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h2 className="text-slate-200 font-bold text-sm flex items-center gap-2">
            <History className="w-4 h-4 text-indigo-400" /> Archive & History
          </h2>
          <button 
            onClick={fetchHistory} 
            className={`text-slate-400 hover:text-white transition-colors ${isLoading ? 'animate-spin' : ''}`}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        {/* VISUAL CHECK: Shows which user's isolated dashboard this is */}
        <div className="text-[10px] text-slate-500 font-mono truncate">
          User: {currentUser}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-3">
        {history.length === 0 ? (
          <div className="text-center p-6 border border-dashed border-slate-700 rounded-xl bg-slate-800/30">
            <p className="text-xs text-slate-500">No historical documents found. Upload and review a contract to begin.</p>
          </div>
        ) : (
          history.map((record) => (
            <div 
              key={record.id}
              onClick={() => onSelectDocument(record.document_id)} 
              className="bg-[#162032] border border-slate-700/50 rounded-xl p-3 shadow-md hover:bg-slate-800/80 transition-colors cursor-pointer"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2 overflow-hidden">
                  <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                  <span className="text-xs font-semibold text-slate-200 truncate">
                    {record.file_name}
                  </span>
                </div>
                {record.action === 'ACCEPT' ? (
                  <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                )}
              </div>
              
              <div className="flex items-center justify-between text-[10px]">
                <span className={`font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                  record.action === 'ACCEPT' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                }`}>
                  {record.action}
                </span>
                <span className="text-slate-500">{formatDate(record.timestamp)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};