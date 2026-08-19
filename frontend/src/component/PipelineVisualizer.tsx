import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Scan, FileText, Database, Scale, FileCheck2, Loader2, CheckCircle2 } from 'lucide-react';

const pipelineStages = [
  { id: 1, label: "Running Multimodal OCR Scanning...", icon: Scan, time: 0 },
  { id: 2, label: "Parsing & Chunking Document Clauses...", icon: FileText, time: 2000 },
  { id: 3, label: "Querying Qdrant Vector DB for Policies...", icon: Database, time: 5000 },
  { id: 4, label: "Cross-Referencing Citations & Risk (Gemini)...", icon: Scale, time: 8500 },
  { id: 5, label: "Compiling Final Audit Report...", icon: FileCheck2, time: 13000 },
];

export const PipelineVisualizer = ({ isAnalyzing }: { isAnalyzing: boolean }) => {
  const [activeStage, setActiveStage] = useState(1);

  useEffect(() => {
    let timeouts: number[] = [];
    
    if (isAnalyzing) {
      setActiveStage(1);
      pipelineStages.forEach((stage) => {
        if (stage.time > 0) {
          const timeout = window.setTimeout(() => {
            setActiveStage(stage.id);
          }, stage.time);
          timeouts.push(timeout);
        }
      });
    }

    return () => {
      timeouts.forEach((t) => window.clearTimeout(t));
    };
  }, [isAnalyzing]);

  if (!isAnalyzing) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="w-full bg-[#001021]/90 backdrop-blur-md border border-[#00A3E0]/40 rounded-2xl p-6 mt-6 shadow-[0_0_25px_rgba(0,163,224,0.15)]"
    >
      <h3 className="text-[#00A3E0] text-xs font-black tracking-widest mb-5 uppercase flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin" /> Live LangGraph AI Pipeline Execution
      </h3>
      <div className="space-y-3.5">
        {pipelineStages.map((stage) => {
          const Icon = stage.icon;
          const isActive = activeStage === stage.id;
          const isDone = activeStage > stage.id;
          
          return (
            <motion.div 
              key={stage.id}
              initial={{ opacity: 0.3, x: -5 }}
              animate={{ opacity: isActive || isDone ? 1 : 0.3, x: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex items-center space-x-4 p-3 rounded-xl border transition-all ${
                isActive ? 'bg-[#002B49]/80 border-[#00A3E0] shadow-lg shadow-[#00A3E0]/10' : 
                isDone ? 'bg-emerald-950/20 border-emerald-500/30' : 
                'bg-[#001426]/50 border-[#002B49]'
              }`}
            >
              <div className={`p-2 rounded-lg border ${
                isActive ? 'bg-[#002B49] border-[#00A3E0] text-[#00A3E0]' : 
                isDone ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 
                'bg-[#001021] border-[#002B49] text-slate-600'
              }`}>
                <Icon className="w-4 h-4" />
              </div>
              
              <div className="flex-1">
                <span className={`text-xs ${
                  isActive ? 'text-white font-bold tracking-wide' : 
                  isDone ? 'text-emerald-400 font-medium' : 
                  'text-slate-500 font-medium'
                }`}>
                  {stage.label}
                </span>
              </div>
              
              {isActive && <Loader2 className="w-4 h-4 animate-spin text-[#00A3E0]" />}
              {isDone && (
                <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }}>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </motion.div>
              )}
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
};
