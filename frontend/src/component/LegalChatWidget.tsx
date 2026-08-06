import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Bot, Send, X, Maximize2, Minimize2, Loader2 } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
}

export function LegalChatWidget({ currentDocumentId }: { currentDocumentId?: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', text: '👋 Hello! I am **Aadhya**, your Tata Legal Assistant. How may I assist your review today?' }
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
      // Map history to match the backend Pydantic model exactly
      const backendHistory = newMessages.slice(0, -1).map(msg => ({
        role: msg.role,
        text: msg.text
      }));

      const response = await axios.post('http://localhost:8000/api/v1/chat/query', {
        query: userText,
        user_id: "demo_user@tata.com", // You can dynamically pass the logged-in user here later
        document_id: currentDocumentId || null,
        chat_history: backendHistory // <--- This unlocks the memory!
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
        className="fixed bottom-6 right-6 h-14 w-14 bg-indigo-600 hover:bg-indigo-500 rounded-full flex items-center justify-center shadow-2xl transition-all z-50 group border border-indigo-400/30"
      >
        <Bot className="w-6 h-6 text-white group-hover:scale-110 transition-transform" />
        <span className="absolute -top-2 -right-2 flex h-4 w-4">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-4 w-4 bg-emerald-500 border-2 border-[#0F172A]"></span>
        </span>
      </button>
    );
  }

  return (
    <div className={`fixed bottom-6 right-6 bg-[#162032] border border-slate-700/60 rounded-2xl shadow-2xl flex flex-col z-50 transition-all duration-300 ${isExpanded ? 'w-[600px] h-[80vh]' : 'w-[380px] h-[500px]'}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/60 bg-[#0F172A] rounded-t-2xl">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
            <Bot className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">Aadhya <span className="px-1.5 py-0.5 rounded text-[9px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/20">AI</span></h3>
            <p className="text-[10px] text-emerald-400 flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span> Active Session</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setIsExpanded(!isExpanded)} className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors">
            {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button onClick={() => setIsOpen(false)} className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-[#0B1120]/50">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] text-sm p-3 rounded-2xl ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-sm' : 'bg-slate-800 text-slate-300 rounded-bl-sm border border-slate-700/50'}`}>
              <div dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 text-slate-400 text-xs p-3 rounded-2xl rounded-bl-sm border border-slate-700/50 flex items-center gap-2">
              <Loader2 className="w-3 h-3 animate-spin" /> Aadhya is typing...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-3 border-t border-slate-700/60 bg-[#0F172A] rounded-b-2xl">
        <div className="relative flex items-center">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask Aadhya about clauses, risks, or policies..."
            className="w-full bg-[#162032] border border-slate-700 text-sm text-white rounded-xl pl-4 pr-12 py-3 focus:outline-none focus:border-indigo-500 resize-none h-[46px] overflow-hidden"
            rows={1}
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 p-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg disabled:opacity-50 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}