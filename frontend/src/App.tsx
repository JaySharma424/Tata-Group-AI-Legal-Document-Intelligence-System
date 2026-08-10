import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { DocumentHistorySidebar } from './component/DocumentHistorySidebar';
import { DocumentWorkspace } from './component/DocumentWorkspace';
import { AdminPortal } from './component/AdminPortal';
import { AuthGate } from './component/AuthGate';
import { LegalChatWidget } from './component/LegalChatWidget';
import { User, Settings, LogOut, X, CheckCircle2, Award, ShieldAlert, FileText, Lock } from 'lucide-react';

// Global Axios Interceptors
axios.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

function App() {
  const [user, setUser] = useState<any>(null);
  const [clickedJobId, setClickedJobId] = useState<string | null>(null);
  
  // Navigation State: 'workspace' or 'admin'
  const [activeView, setActiveView] = useState<'workspace' | 'admin'>('workspace');
  const [showProfile, setShowProfile] = useState(false);

  useEffect(() => {
    const storedUser = sessionStorage.getItem('user');
    const token = sessionStorage.getItem('access_token');
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const handleLogout = () => {
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('user');
    setUser(null);
    setClickedJobId(null);
  };

  const handleLoginSuccess = (arg1: any, arg2?: any) => {
    let token = arg2 ? arg1 : (arg1?.access_token || sessionStorage.getItem('access_token') || '');
    let userData = arg2 ? arg2 : (arg1?.user || arg1);

    if (token) sessionStorage.setItem('access_token', token);
    if (userData) {
      sessionStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
    }
    setClickedJobId(null);
  };

  if (!user) {
    return <AuthGate onLoginSuccess={handleLoginSuccess} />;
  }

  const userEmail = (user?.email || 'user@tata.com').toLowerCase();
  const userName = user?.full_name || user?.name || user?.username || 'Enterprise User';
  const userRole = user?.role || 'Compliance Officer';
  const userBU = user?.businessUnit || user?.business_unit || 'Enterprise Legal';

  // Strict Role Guard: Only Admin, General Counsel, Senior Reviewer, or Admin email gets access
  const isAdminUser = ['Admin', 'General Counsel', 'Senior Reviewer'].includes(userRole) || userEmail.includes('admin');

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#000D1A] text-slate-200 font-sans relative">
      <DocumentHistorySidebar onSelectDocument={(jobId) => {
        setClickedJobId(jobId);
        setActiveView('workspace');
      }} />

      <main className="flex-1 overflow-y-auto custom-scrollbar flex flex-col relative">
        
        {/* Navigation Header */}
        <header className="flex justify-between items-center px-8 py-3.5 bg-[#001021]/95 backdrop-blur-md border-b border-[#002B49] sticky top-0 z-20 shadow-md">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-[#002B49] rounded-lg border border-[#004B87]">
                <Award className="w-5 h-5 text-[#00A3E0]" />
              </div>
              <div>
                <span className="text-[10px] font-black uppercase tracking-widest text-[#00A3E0]">TATA GROUP</span>
                <h2 className="text-xs font-bold text-white tracking-tight">AI Legal Intelligence Portal</h2>
              </div>
            </div>

            {/* Navigation View Switcher - Strictly Visible ONLY to Admin / Senior Roles */}
            {isAdminUser && (
              <div className="flex bg-[#001021] border border-[#002B49] rounded-xl p-1 gap-1">
                <button 
                  onClick={() => setActiveView('workspace')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-1.5 ${
                    activeView === 'workspace' 
                      ? 'bg-[#002B49] text-[#00A3E0] border border-[#004B87]' 
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" /> Workspace
                </button>

                <button 
                  onClick={() => setActiveView('admin')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer flex items-center gap-1.5 ${
                    activeView === 'admin' 
                      ? 'bg-[#002B49] text-[#00A3E0] border border-[#004B87]' 
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <ShieldAlert className="w-3.5 h-3.5" /> Admin Control Portal
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-xs font-bold text-white tracking-wide">{userName}</p>
              <p className="text-[10px] font-bold tracking-widest uppercase text-[#00A3E0]">
                {userRole} • {userBU}
              </p>
            </div>
            <div className="h-9 w-9 rounded-xl bg-[#002B49] border border-[#004B87] flex items-center justify-center text-[#00A3E0] font-black text-sm">
              {userName.charAt(0).toUpperCase()}
            </div>
            <div className="h-6 w-px bg-[#002B49] mx-1"></div>
            <button onClick={handleLogout} className="p-2 text-slate-400 hover:text-rose-400 hover:bg-[#002B49] rounded-lg transition-all cursor-pointer" title="Sign Out">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* View Switch Logic with Security Check */}
        <div className="flex-1">
          {activeView === 'admin' && isAdminUser ? (
            <AdminPortal />
          ) : (
            <DocumentWorkspace selectedHistoryJobId={clickedJobId} />
          )}
        </div>
      </main>

      <LegalChatWidget currentDocumentId={clickedJobId || undefined} />
    </div>
  );
}

export default App;