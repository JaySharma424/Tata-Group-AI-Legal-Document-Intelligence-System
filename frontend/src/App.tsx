import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { DocumentHistorySidebar } from './component/DocumentHistorySidebar';
import { DocumentWorkspace } from './component/DocumentWorkspace';
import { AuthGate } from './component/AuthGate';
import { LegalChatWidget } from './component/LegalChatWidget';
import { User, Settings, LogOut, X, CheckCircle2 } from 'lucide-react';

// Global Axios Interceptor for JWT Authorization
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

function App() {
  const [user, setUser] = useState<any>(null);
  const [clickedJobId, setClickedJobId] = useState<string | null>(null);
  
  const [showProfile, setShowProfile] = useState(false);
  const [editName, setEditName] = useState('');
  const [editPassword, setEditPassword] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const token = localStorage.getItem('access_token');
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
    setClickedJobId(null);
  };

  // Flexible handler to catch either (token, userData) or just (userData) from AuthGate
  const handleLoginSuccess = (arg1: any, arg2?: any) => {
    let token = '';
    let userData = null;

    if (arg2) {
      token = arg1;
      userData = arg2;
    } else {
      token = arg1?.access_token || localStorage.getItem('access_token') || '';
      userData = arg1?.user || arg1;
    }

    if (token) {
      localStorage.setItem('access_token', token);
    }
    if (userData) {
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
    }
    setClickedJobId(null);
  };

  if (!user) {
    return <AuthGate onLoginSuccess={handleLoginSuccess} />;
  }

  const userEmail = user?.email || 'demo1@tata.com';
  // Safely extract name from whatever key the backend user object uses
  const userName = user?.full_name || user?.name || user?.username || (user?.email ? user.email.split('@')[0].toUpperCase() : 'Enterprise User');
  const userRole = user?.role || 'Compliance Officer';
  const userBU = user?.businessUnit || user?.business_unit || 'Enterprise Legal';

  const openProfileModal = () => {
    setEditName(userName);
    setEditPassword('');
    setShowProfile(true);
  };

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdating(true);
    try {
      const response = await axios.put('http://localhost:8000/api/v1/auth/profile', {
        email: userEmail,
        full_name: editName,
        new_password: editPassword
      });
      
      setUser(response.data.user);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      setShowProfile(false);
      alert('Success: Database credentials updated securely!');
    } catch (error) {
      console.error('Profile update failed:', error);
      alert('Failed to update database.');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#0B1120] text-slate-200 font-sans selection:bg-indigo-500/30 relative">
      <DocumentHistorySidebar onSelectDocument={(jobId) => setClickedJobId(jobId)} />

      <main className="flex-1 overflow-y-auto custom-scrollbar flex flex-col relative">
        <header className="flex justify-end items-center px-8 py-4 bg-[#0F172A]/95 backdrop-blur-md border-b border-slate-800/80 sticky top-0 z-20 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-bold text-slate-200">{userName}</p>
              <p className="text-[10px] font-bold tracking-widest uppercase text-indigo-400">{userRole} • {userBU}</p>
            </div>
            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-lg">
              {userName.charAt(0).toUpperCase()}
            </div>
            <div className="h-8 w-px bg-slate-700/50 mx-2"></div>
            <button onClick={openProfileModal} className="p-2 text-slate-400 hover:text-indigo-400 hover:bg-slate-800 rounded-lg transition-all" title="Profile Settings">
              <Settings className="w-4 h-4" />
            </button>
            <button onClick={handleLogout} className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-all" title="Sign Out">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </header>

        <div className="flex-1">
          <DocumentWorkspace selectedHistoryJobId={clickedJobId} />
        </div>
      </main>

      {showProfile && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-md shadow-2xl relative">
            <button onClick={() => setShowProfile(false)} className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
            <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2"><User className="w-5 h-5 text-indigo-400" /> Account Settings</h2>
            <p className="text-xs text-slate-400 mb-6">Updates will be saved directly to the enterprise database.</p>
            
            <form className="space-y-4" onSubmit={handleProfileUpdate}>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Full Name</label>
                <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)} required className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:border-indigo-500 outline-none" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Corporate Email (SSO Locked)</label>
                <input type="email" value={userEmail} disabled className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg p-2.5 text-sm text-slate-500 cursor-not-allowed" />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">New Password (Optional)</label>
                <input type="password" value={editPassword} onChange={(e) => setEditPassword(e.target.value)} placeholder="Leave blank to keep current" className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:border-indigo-500 outline-none" />
              </div>
              <button type="submit" disabled={isUpdating} className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-lg transition-colors mt-4 disabled:opacity-50 flex items-center justify-center gap-2">
                {isUpdating ? 'Saving to Database...' : <><CheckCircle2 className="w-4 h-4"/> Save Database Changes</>}
              </button>
            </form>
          </div>
        </div>
      )}

      <LegalChatWidget currentDocumentId={clickedJobId || undefined} />
    </div>
  );
}

export default App;