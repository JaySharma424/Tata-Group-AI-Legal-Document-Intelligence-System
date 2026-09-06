import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Scan, FileText, Database, Scale, FileCheck2, Loader2, CheckCircle2 } from 'lucide-react';

const pipelineStages = [
  { id: 1, label: "Running Multimodal OCR Scanning...", icon: Scan },
  { id: 2, label: "Deterministic Indian Legal Parsing & Cosine Chunking...", icon: FileText },
  { id: 3, label: "Querying Qdrant Vector DB & Redis Policy Cache...", icon: Database },
  { id: 4, label: "Batch Reasoning & Automated Policy Redlines (Gemini)...", icon: Scale },
  { id: 5, label: "Compiling Final Audit Report & Storing Knowledge...", icon: FileCheck2 },
];

interface PipelineVisualizerProps {
  isAnalyzing: boolean;
  activeStage?: number;
  statusMessage?: string;
}

export const PipelineVisualizer: React.FC<PipelineVisualizerProps> = ({ 
  isAnalyzing, 
  activeStage: propActiveStage = 1,
  statusMessage = "Processing legal document pipeline..."
}) => {
  const [currentStage, setCurrentStage] = useState<number>(propActiveStage);

  useEffect(() => {
    if (propActiveStage) {
      setCurrentStage(propActiveStage);
    }
  }, [propActiveStage]);

  if (!isAnalyzing) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="w-full bg-[#001021]/90 backdrop-blur-md border border-[#00A3E0]/40 rounded-2xl p-6 mt-6 shadow-[0_0_25px_rgba(0,163,224,0.15)]"
    >
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-[#00A3E0] text-xs font-black tracking-widest uppercase flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" /> Live V2 Async Streaming Execution
        </h3>
        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded">
          WebSocket Live
        </span>
      </div>

      <div className="space-y-3.5">
        {pipelineStages.map((stage) => {
          const Icon = stage.icon;
          const isActive = currentStage === stage.id;
          const isDone = currentStage > stage.id;
          
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
                {isActive && statusMessage && (
                  <p className="text-[10px] text-cyan-300 font-mono mt-0.5">
                    {statusMessage}
                  </p>
                )}
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