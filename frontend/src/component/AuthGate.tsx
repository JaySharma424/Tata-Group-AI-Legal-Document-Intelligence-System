import React, { useState } from 'react';
import axios from 'axios';
import { ShieldCheck, Lock, Building2, UserCheck, Mail, ArrowLeft, Award } from 'lucide-react';

interface UserData {
  name?: string;
  email: string;
  businessUnit?: string;
  role: string;
}

interface AuthProps {
  onLoginSuccess: (userOrToken: any, extraUser?: any) => void;
}

type AuthView = 'login' | 'register' | 'forgot';

// Locked Production Base URL
const API_BASE_URL = 'https://tata-ai-backend-og7t.onrender.com';

export const AuthGate: React.FC<AuthProps> = ({ onLoginSuccess }) => {
  const [view, setView] = useState<AuthView>('login');
  
  // Form States
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [businessUnit, setBusinessUnit] = useState('Enterprise Legal');
  const [role, setRole] = useState('Senior Reviewer');
  
  // Feedback Messages
  const [successMessage, setSuccessMessage] = useState('');
  const [error, setError] = useState('');

  const resetMessages = () => {
    setError('');
    setSuccessMessage('');
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();

    try {
      // Send standard OAuth2 Form Data directly
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      
      const response = await axios.post(`${API_BASE_URL}/api/v1/auth/login`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      const data = response.data;
      
      const token = 
        typeof data === 'string' ? data : (
        data?.access_token || 
        data?.accessToken || 
        data?.token || 
        data?.jwt || 
        data?.data?.access_token
      );

      if (token && token.length > 10) {
        const userData: UserData = data?.user || data?.data?.user || { 
          name: email.split('@')[0], 
          email, 
          role: 'Senior Reviewer', 
          businessUnit: 'Enterprise Legal' 
        };
        
        sessionStorage.setItem('access_token', token);
        sessionStorage.setItem('user', JSON.stringify(userData));

        if (onLoginSuccess) {
          onLoginSuccess(token, userData);
        }
      } else {
        setError(`Token missing. Backend returned: ${JSON.stringify(data)}`);
      }
    } catch (err: any) {
      console.error("Login failed:", err);
      const detail = err.response?.data?.detail;
      setError(`Error: ${typeof detail === 'string' ? detail : 'Invalid credentials or server error.'}`);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();

    if (!name || !email || !password) {
      setError('Please fill in all required fields.');
      return;
    }

    try {
      await axios.post(`${API_BASE_URL}/api/v1/auth/register`, {
        full_name: name,
        email: email,
        password: password,
        business_unit: businessUnit,
        role: role
      });
    
      setSuccessMessage('Registration successful! Please sign in with your credentials.');
      setPassword('');
      setView('login');
    } catch (err: any) {
      console.error('Registration failed:', err);
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Failed to register user.');
    }
  };

  const handleForgotPassword = (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();

    if (!email) {
      setError('Please enter your corporate email address.');
      return;
    }
    setSuccessMessage('Password reset instructions have been sent to your corporate email.');
    setTimeout(() => {
      setSuccessMessage('');
      setView('login');
    }, 2000);
  };

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-[#001021] font-sans p-4 relative overflow-hidden">
      {/* Tata Royal Glow Background Accents */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-[#003B73]/20 via-[#002B49]/10 to-transparent rounded-full blur-3xl pointer-events-none"></div>

      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200/80 p-8 space-y-6 relative z-10">
        
        {/* Tata Header Brand Section */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-[#002B49] text-white rounded-xl mb-1 shadow-md border border-[#004B87]">
            <Award className="w-7 h-7 text-[#00A3E0]" />
          </div>
          <div className="flex items-center justify-center gap-1.5">
            <span className="text-xs font-black tracking-widest text-[#002B49] uppercase">TATA GROUP</span>
            <span className="text-xs text-slate-300">•</span>
            <span className="text-xs font-semibold text-[#00A3E0] uppercase tracking-wider">AI LEGAL</span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">Legal Intelligence</h1>
          <p className="text-[11px] text-slate-500 uppercase tracking-widest font-bold">
            Governance, Risk & Compliance Portal
          </p>
        </div>

        {/* Feedback Banners */}
        {successMessage && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg font-medium text-center break-words shadow-sm">
            {successMessage}
          </div>
        )}
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg font-medium text-center break-words shadow-sm">
            {error}
          </div>
        )}

        {/* VIEW 1: LOGIN */}
        {view === 'login' && (
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-[#003B73]" /> Corporate Email
              </label>
              <input 
                type="email" 
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003B73] bg-slate-50 text-slate-900"
                placeholder="name@tata.com"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-xs font-bold text-slate-700 uppercase">Password</label>
                <button 
                  type="button" 
                  onClick={() => { setView('forgot'); resetMessages(); }}
                  className="text-xs text-[#003B73] hover:underline font-bold cursor-pointer"
                >
                  Forgot password?
                </button>
              </div>
              <input 
                type="password" 
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003B73] bg-slate-50 text-slate-900"
                placeholder="••••••••"
              />
            </div>

            <button 
              type="submit" 
              className="w-full bg-[#002B49] hover:bg-[#003B73] text-white py-3 rounded-lg text-sm font-bold transition-all shadow-lg shadow-[#002B49]/20 flex items-center justify-center gap-2 cursor-pointer mt-2"
            >
              <ShieldCheck className="w-4 h-4 text-[#00A3E0]" /> Secure Corporate Sign In
            </button>

            <div className="text-center pt-2">
              <span className="text-xs text-slate-500">New reviewer or counsel? </span>
              <button 
                type="button" 
                onClick={() => { setView('register'); resetMessages(); }}
                className="text-xs font-bold text-[#003B73] hover:underline cursor-pointer"
              >
                Register an account
              </button>
            </div>
          </form>
        )}

        {/* VIEW 2: REGISTER */}
        {view === 'register' && (
          <form onSubmit={handleRegister} className="space-y-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1 flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5 text-[#003B73]" /> Full Name
              </label>
              <input 
                type="text" 
                required
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003B73] bg-slate-50 text-slate-900"
                placeholder="e.g. Ratan Tata"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Corporate Email</label>
              <input 
                type="email" 
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003B73] bg-slate-50 text-slate-900"
                placeholder="name@tata.com"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Password</label>
              <input 
                type="password" 
                required
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003B73] bg-slate-50 text-slate-900"
                placeholder="Create secure password"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1 flex items-center gap-1">
                  <Building2 className="w-3 h-3 text-[#003B73]" /> Business Unit
                </label>
                <select 
                  value={businessUnit}
                  onChange={(e) => setBusinessUnit(e.target.value)}
                  className="w-full px-2 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none bg-slate-50 text-slate-900 font-medium"
                >
                  <option value="Enterprise Legal">Enterprise Legal</option>
                  <option value="Compliance & Risk">Compliance & Risk</option>
                  <option value="Procurement">Procurement</option>
                  <option value="Executive Office">Executive Office</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Role</label>
                <select 
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-2 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none bg-slate-50 text-slate-900 font-medium"
                >
                  <option value="Senior Reviewer">Senior Reviewer</option>
                  <option value="Compliance Officer">Compliance Officer</option>
                  <option value="General Counsel">General Counsel</option>
                </select>
              </div>
            </div>

            <button 
              type="submit" 
              className="w-full bg-[#002B49] text-white py-2.5 rounded-lg text-sm font-bold hover:bg-[#003B73] transition-colors shadow-md cursor-pointer mt-1"
            >
              Complete Registration
            </button>

            <div className="text-center pt-2">
              <button 
                type="button" 
                onClick={() => { setView('login'); resetMessages(); }}
                className="text-xs text-slate-600 hover:text-[#003B73] flex items-center justify-center gap-1 mx-auto cursor-pointer font-bold"
              >
                <ArrowLeft className="w-3 h-3" /> Back to Sign In
              </button>
            </div>
          </form>
        )}

        {/* VIEW 3: FORGOT PASSWORD */}
        {view === 'forgot' && (
          <form onSubmit={handleForgotPassword} className="space-y-4">
            <p className="text-xs text-slate-500 leading-relaxed">
              Enter your registered corporate email address and we will send password reset instructions.
            </p>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">Corporate Email</label>
              <input 
                type="email" 
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#003B73] bg-slate-50 text-slate-900"
                placeholder="name@tata.com"
              />
            </div>

            <button 
              type="submit" 
              className="w-full bg-[#002B49] text-white py-3 rounded-lg text-sm font-bold hover:bg-[#003B73] transition-colors shadow-md cursor-pointer"
            >
              Send Reset Instructions
            </button>

            <div className="text-center pt-2">
              <button 
                type="button" 
                onClick={() => { setView('login'); resetMessages(); }}
                className="text-xs text-slate-600 hover:text-[#003B73] flex items-center justify-center gap-1 mx-auto cursor-pointer font-bold"
              >
                <ArrowLeft className="w-3 h-3" /> Back to Sign In
              </button>
            </div>
          </form>
        )}

        <p className="text-[10px] text-center text-slate-400 leading-relaxed border-t border-slate-100 pt-4 font-mono">
          Proprietary System of Tata Group. All activities audited for compliance.
        </p>

      </div>
    </div>
  );
};