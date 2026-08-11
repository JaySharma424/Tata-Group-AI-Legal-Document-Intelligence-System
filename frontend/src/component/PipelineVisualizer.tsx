import React, { useState, useEffect } from 'react';
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
    <div className="w-full bg-[#001021]/80 backdrop-blur-md border border-[#00A3E0]/30 rounded-xl p-6 mt-6 shadow-[0_0_20px_rgba(0,163,224,0.1)]">
      <h3 className="text-[#00A3E0] text-xs font-black tracking-widest mb-5 uppercase flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin" /> Live Analysis Pipeline
      </h3>
      <div className="space-y-4">
        {pipelineStages.map((stage) => {
          const Icon = stage.icon;
          const isActive = activeStage === stage.id;
          const isDone = activeStage > stage.id;
          
          return (
            <div 
              key={stage.id} 
              className={`flex items-center space-x-4 transition-all duration-500 ${
                isActive || isDone ? 'opacity-100' : 'opacity-20'
              }`}
            >
              <div className={`p-2 rounded-lg border ${
                isActive ? 'bg-[#002B49] border-[#00A3E0] text-[#00A3E0]' : 
                isDone ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-400' : 
                'bg-slate-800/50 border-slate-700 text-slate-500'
              }`}>
                <Icon className="w-4 h-4" />
              </div>
              
              <div className="flex-1">
                <span className={`text-sm ${
                  isActive ? 'text-white font-bold' : 
                  isDone ? 'text-emerald-400/80 font-medium' : 
                  'text-slate-500 font-medium'
                }`}>
                  {stage.label}
                </span>
              </div>
              
              {isActive && <Loader2 className="w-4 h-4 animate-spin text-[#00A3E0]" />}
              {isDone && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
            </div>
          );
        })}
      </div>
    </div>
  );
};