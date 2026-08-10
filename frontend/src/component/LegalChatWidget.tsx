import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Bot, Send, X, Maximize2, Minimize2, Loader2, Award, Sparkles } from 'lucide-react';

const API_BASE_URL = 'https://tata-ai-backend-og7t.onrender.com';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
}

export function LegalChatWidget({ currentDocumentId }: { currentDocumentId?: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', text: '👋 Welcome! I am **Aadhya**, your Tata Legal & Governance AI Assistant. How may I assist your contract review today?' }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }, 100);
    }
  }, [messages, isOpen, isExpanded]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userText = input.trim();
    const newMessages: ChatMessage[] = [...messages, { role: 'user', text: userText }];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      const backendHistory = newMessages.slice(0, -1).map(msg => ({
        role: msg.role,
        text: msg.text
      }));

      const response = await axios.post(`${API_BASE_URL}/api/v1/chat/query`, {
        query: userText,
        user_id: "demo_user@tata.com",
        document_id: currentDocumentId || null,
        chat_history: backendHistory
      });

      setMessages(prev => [...prev, { role: 'assistant', text: response.data.answer }]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, { role: 'assistant', text: '⚠️ System Error: Unable to reach the Aadhya AI gateway. Please ensure the backend is running.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 h-14 w-14 bg-[#002B49] hover:bg-[#003B73] rounded-full flex items-center justify-center shadow-2xl transition-all z-50 group border border-[#00A3E0]/40"
        title="Open Aadhya AI Legal Assistant"
      >
        <Award className="w-6 h-6 text-[#00A3E0] group-hover:scale-110 transition-transform" />
        <span className="absolute -top-1 -right-1 flex h-4 w-4">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00A3E0] opacity-75"></span>
          <span className="relative inline-flex rounded-full h-4 w-4 bg-[#00A3E0] border-2 border-[#001021]"></span>
        </span>
      </button>
    );
  }

  return (
    <div className={`fixed bottom-6 right-6 bg-[#00182C] border border-[#002B49] rounded-2xl shadow-2xl flex flex-col z-50 transition-all duration-300 font-sans ${isExpanded ? 'w-[620px] h-[82vh]' : 'w-[400px] h-[520px]'}`}>
      
      {/* Tata Corporate Header */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-[#002B49] bg-[#001021] rounded-t-2xl">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-[#002B49] flex items-center justify-center border border-[#004B87] shadow-inner">
            <Award className="w-5 h-5 text-[#00A3E0]" />
          </div>
          <div>
            <h3 className="text-sm font-black tracking-tight text-white flex items-center gap-2">
              Aadhya <span className="px-1.5 py-0.5 rounded text-[9px] bg-[#00A3E0]/10 text-[#00A3E0] border border-[#00A3E0]/30 font-bold uppercase tracking-widest">TATA AI</span>
            </h3>
            <p className="text-[10px] text-emerald-400 flex items-center gap-1 font-semibold mt-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span> Grounded Policy Assistant
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setIsExpanded(!isExpanded)} className="p-1.5 text-slate-400 hover:text-white hover:bg-[#002B49] rounded-lg transition-colors cursor-pointer">
            {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button onClick={() => setIsOpen(false)} className="p-1.5 text-slate-400 hover:text-white hover:bg-[#002B49] rounded-lg transition-colors cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-[#001021]/80">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] text-xs leading-relaxed p-3.5 rounded-2xl shadow-md ${
              msg.role === 'user' 
                ? 'bg-[#002B49] text-white rounded-br-none border border-[#004B87]' 
                : 'bg-[#00182C] text-slate-200 rounded-bl-none border border-[#002B49]'
            }`}>
              <div dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-[#00182C] text-slate-400 text-xs p-3 rounded-2xl rounded-bl-none border border-[#002B49] flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#00A3E0]" /> Aadhya is searching policy database...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Section */}
      <div className="p-3 border-t border-[#002B49] bg-[#001021] rounded-b-2xl">
        <div className="relative flex items-center">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask Aadhya about contract clauses, risks, or Tata policies..."
            className="w-full bg-[#00182C] border border-[#002B49] text-xs text-white rounded-xl pl-3.5 pr-11 py-3 focus:outline-none focus:border-[#00A3E0] resize-none h-[46px] overflow-hidden placeholder:text-slate-500"
            rows={1}
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 p-1.5 bg-[#002B49] hover:bg-[#003B73] border border-[#004B87] text-[#00A3E0] rounded-lg disabled:opacity-50 transition-all cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

    </div>
  );
}