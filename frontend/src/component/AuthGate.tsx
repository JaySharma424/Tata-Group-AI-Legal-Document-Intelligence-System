import React, { useState } from 'react';
import axios from 'axios';
import { ShieldCheck, Lock, Building2, UserCheck, Mail, ArrowLeft } from 'lucide-react';

interface AuthProps {
  onLoginSuccess: (user: { name: string; email: string; businessUnit: string; role: string }) => void;
}

type AuthView = 'login' | 'register' | 'forgot';

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

  const handleLoginSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  try {
    const response = await axios.post('http://localhost:8000/api/v1/auth/login', {
      email,
      password
    });

    // Capture token and user data dynamically from the backend response
    const token = response.data.access_token || response.data.token;
    const userData = response.data.user || { email, role: 'Compliance Officer' };

    if (token) {
      // Store securely so Axios interceptor can read it
      localStorage.setItem('access_token', token);
      localStorage.setItem('user', JSON.stringify(userData));

      // Propagate success up to App.tsx
      if (onLoginSuccess) {
        onLoginSuccess(token);
      }
    }
  } catch (error) {
    console.error("Login failed:", error);
    alert("Invalid credentials or server error.");
  }
};

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!name || !email || !password) {
      setError('Please fill in all required fields.');
      return;
    }

    try {
      const response = await axios.post('http://localhost:8000/api/v1/auth/register', {
        full_name: name, // Fixed from fullName to name
        email: email,
        password: password,
        business_unit: businessUnit,
        role: role
      });
    
      // Pass user data up on success
      setSuccessMessage('Registration successful! Please sign in with your credentials.');
      setPassword('');
    //   onLoginSuccess(response.data.user);
      setView('login');
    } catch (err: any) {
      console.error('Registration failed:', err);
      setError(err.response?.data?.detail || 'Failed to register user. Check if backend is running.');
    }
  };

  const handleForgotPassword = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email) {
      setError('Please enter your corporate email address.');
      return;
    }
    setSuccessMessage('Password reset instructions have been sent to your email.');
    setTimeout(() => {
      setSuccessMessage('');
      setView('login');
    }, 2000);
  };

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-slate-900 font-sans p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-800 p-8 space-y-6">
        
        {/* Header Section */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-indigo-50 text-indigo-600 rounded-xl mb-2 shadow-inner">
            <Lock className="w-7 h-7" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Tata AI Legal Intelligence</h1>
          <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">
            Enterprise Governance & Security Portal
          </p>
        </div>

        {/* Success or Error Banners */}
        {successMessage && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg font-medium text-center">
            {successMessage}
          </div>
        )}
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg font-medium text-center">
            {error}
          </div>
        )}

        {/* ================= VIEW 1: LOGIN ================= */}
        {view === 'login' && (
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-indigo-600" /> Corporate Email
              </label>
              <input 
                type="email" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-slate-50"
                placeholder="name@tata.com"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-xs font-bold text-slate-600 uppercase">Password</label>
                <button 
                  type="button" 
                  onClick={() => { setView('forgot'); setError(''); }}
                  className="text-xs text-indigo-600 hover:underline font-medium cursor-pointer"
                >
                  Forgot password?
                </button>
              </div>
              <input 
                type="password" 
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-slate-50"
                placeholder="••••••••"
              />
            </div>

            <button 
              type="submit" 
              className="w-full bg-indigo-600 text-white py-3 rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-md flex items-center justify-center gap-2 cursor-pointer mt-2"
            >
              <ShieldCheck className="w-4 h-4" /> Secure Sign In
            </button>

            <div className="text-center pt-2">
              <span className="text-xs text-slate-500">New reviewer or counsel? </span>
              <button 
                type="button" 
                onClick={() => { setView('register'); setError(''); }}
                className="text-xs font-bold text-indigo-600 hover:underline cursor-pointer"
              >
                Register an account
              </button>
            </div>
          </form>
        )}

        {/* ================= VIEW 2: REGISTER ================= */}
        {view === 'register' && (
          <form onSubmit={handleRegister} className="space-y-3">
            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1 flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5 text-indigo-600" /> Full Name
              </label>
              <input 
                type="text" 
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-slate-50"
                placeholder="e.g. Jane Doe"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Corporate Email</label>
              <input 
                type="email" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-slate-50"
                placeholder="name@tata.com"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Password</label>
              <input 
                type="password" 
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-slate-50"
                placeholder="Create secure password"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1 flex items-center gap-1">
                  <Building2 className="w-3 h-3 text-indigo-600" /> Unit
                </label>
                <select 
                  value={businessUnit}
                  onChange={(e) => setBusinessUnit(e.target.value)}
                  className="w-full px-2 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none bg-slate-50"
                >
                  <option value="Enterprise Legal">Enterprise Legal</option>
                  <option value="Compliance & Risk">Compliance & Risk</option>
                  <option value="Procurement">Procurement</option>
                  <option value="Executive Office">Executive Office</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Role</label>
                <select 
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full px-2 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none bg-slate-50"
                >
                  <option value="Senior Reviewer">Senior Reviewer</option>
                  <option value="Compliance Officer">Compliance Officer</option>
                  <option value="General Counsel">General Counsel</option>
                </select>
              </div>
            </div>

            <button 
              type="submit" 
              className="w-full bg-slate-900 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-slate-800 transition-colors shadow-md cursor-pointer mt-1"
            >
              Complete Registration
            </button>

            <div className="text-center pt-2">
              <button 
                type="button" 
                onClick={() => { setView('login'); setError(''); }}
                className="text-xs text-slate-600 hover:text-indigo-600 flex items-center justify-center gap-1 mx-auto cursor-pointer font-medium"
              >
                <ArrowLeft className="w-3 h-3" /> Back to Sign In
              </button>
            </div>
          </form>
        )}

        {/* ================= VIEW 3: FORGOT PASSWORD ================= */}
        {view === 'forgot' && (
          <form onSubmit={handleForgotPassword} className="space-y-4">
            <p className="text-xs text-slate-500 leading-relaxed">
              Enter your registered corporate email address and we will send password reset instructions to restore access.
            </p>

            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Corporate Email</label>
              <input 
                type="email" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-slate-50"
                placeholder="name@tata.com"
              />
            </div>

            <button 
              type="submit" 
              className="w-full bg-indigo-600 text-white py-3 rounded-lg text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-md cursor-pointer"
            >
              Send Reset Instructions
            </button>

            <div className="text-center pt-2">
              <button 
                type="button" 
                onClick={() => { setView('login'); setError(''); }}
                className="text-xs text-slate-600 hover:text-indigo-600 flex items-center justify-center gap-1 mx-auto cursor-pointer font-medium"
              >
                <ArrowLeft className="w-3 h-3" /> Back to Sign In
              </button>
            </div>
          </form>
        )}

        <p className="text-[11px] text-center text-slate-400 leading-relaxed border-t border-slate-100 pt-4">
          Authorized access only. All actions and document queries are audited for enterprise compliance.
        </p>

      </div>
    </div>
  );
};