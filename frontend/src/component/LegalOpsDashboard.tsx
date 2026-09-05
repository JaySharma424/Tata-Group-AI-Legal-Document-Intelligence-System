import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { BarChart3, ShieldAlert, Clock, CheckCircle2, AlertTriangle, ArrowUpRight, Award, Zap } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

export const LegalOpsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/monitoring/telemetry`);
        setMetrics(response.data);
      } catch (err) {
        console.error('Failed to load legal operations metrics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (loading) {
    return <div className="p-8 text-slate-400 text-xs font-mono">Loading Tata Governance Telemetry & Audit Operations...</div>;
  }

  return (
    <div className="space-y-6 p-8 bg-[#001021] min-h-screen text-slate-100 font-sans max-w-7xl mx-auto">
      
      {/* Tata Corporate Header */}
      <div className="flex justify-between items-center border-b border-[#002B49] pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Award className="w-4 h-4 text-[#00A3E0]" />
            <span className="text-xs font-black uppercase tracking-widest text-[#00A3E0]">TATA GROUP TELEMETRY</span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-white">
            Legal Operations & Governance Dashboard
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Enterprise review throughput, risk taxonomy monitoring, and multi-tenant audit metrics.
          </p>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        
        <div className="bg-[#00182C] border border-[#002B49] border-t-4 border-t-[#00A3E0] rounded-2xl p-5 shadow-lg space-y-2">
          <div className="flex justify-between text-slate-400 text-[10px] font-black uppercase tracking-widest">
            <span>Processed Docs</span>
            <BarChart3 className="w-4 h-4 text-[#00A3E0]" />
          </div>
          <div className="text-3xl font-black text-white">{metrics?.throughput?.total_documents_processed || 0}</div>
          <p className="text-[11px] text-emerald-400 font-semibold flex items-center gap-1">
            <ArrowUpRight className="w-3 h-3" /> 100% Ingestion Rate
          </p>
        </div>

        <div className="bg-[#00182C] border border-[#002B49] border-t-4 border-t-rose-500 rounded-2xl p-5 shadow-lg space-y-2">
          <div className="flex justify-between text-slate-400 text-[10px] font-black uppercase tracking-widest">
            <span>High-Risk Flags</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-3xl font-black text-rose-400">{metrics?.risk_taxonomy_distribution?.HIGH || 0}</div>
          <p className="text-[11px] text-slate-400 font-medium">Requires senior counsel review</p>
        </div>

        <div className="bg-[#00182C] border border-[#002B49] border-t-4 border-t-amber-500 rounded-2xl p-5 shadow-lg space-y-2">
          <div className="flex justify-between text-slate-400 text-[10px] font-black uppercase tracking-widest">
            <span>Turnaround Time</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-black text-white">{metrics?.throughput?.review_turnaround_hours || 1.4} hrs</div>
          <p className="text-[11px] text-slate-400 font-medium">First-pass automated review speed</p>
        </div>

        <div className="bg-[#00182C] border border-[#002B49] border-t-4 border-t-emerald-500 rounded-2xl p-5 shadow-lg space-y-2">
          <div className="flex justify-between text-slate-400 text-[10px] font-black uppercase tracking-widest">
            <span>Governance Actions</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-black text-emerald-400">{metrics?.governance_actions?.total_approved || 0}</div>
          <p className="text-[11px] text-slate-400 font-medium">Approved by counsel</p>
        </div>

      </div>

      {/* Breakdown Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Risk Breakdown */}
        <div className="bg-[#00182C] border border-[#002B49] rounded-2xl p-6 space-y-4 shadow-xl">
          <h2 className="text-xs font-black uppercase tracking-widest text-[#00A3E0] flex items-center gap-2">
            <Zap className="w-4 h-4" /> Risk Taxonomy Distribution
          </h2>
          <div className="space-y-3 text-xs font-medium">
            <div className="flex justify-between items-center p-3 bg-[#001021] rounded-xl border border-[#002B49]">
              <span className="text-rose-400 font-bold flex items-center gap-2">
                <AlertTriangle className="w-4 h-4"/> High Severity Risks
              </span>
              <span className="font-black text-sm px-2.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">
                {metrics?.risk_taxonomy_distribution?.HIGH || 0}
              </span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-[#001021] rounded-xl border border-[#002B49]">
              <span className="text-amber-400 font-bold flex items-center gap-2">
                <AlertTriangle className="w-4 h-4"/> Medium Severity Risks
              </span>
              <span className="font-black text-sm px-2.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                {metrics?.risk_taxonomy_distribution?.MEDIUM || 0}
              </span>
            </div>

            <div className="flex justify-between items-center p-3 bg-[#001021] rounded-xl border border-[#002B49]">
              <span className="text-emerald-400 font-bold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4"/> Low Risk Clauses
              </span>
              <span className="font-black text-sm px-2.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {metrics?.risk_taxonomy_distribution?.LOW || 0}
              </span>
            </div>
          </div>
        </div>

        {/* Business Unit Breakdown */}
        <div className="bg-[#00182C] border border-[#002B49] rounded-2xl p-6 space-y-4 shadow-xl">
          <h2 className="text-xs font-black uppercase tracking-widest text-[#00A3E0] flex items-center gap-2">
            <Award className="w-4 h-4" /> Business Unit Volume
          </h2>
          <div className="space-y-3 text-xs font-medium">
            {metrics?.business_unit_breakdown && Object.keys(metrics.business_unit_breakdown).length > 0 ? (
              Object.entries(metrics.business_unit_breakdown).map(([unit, count]: [string, any]) => (
                <div key={unit} className="flex justify-between items-center p-3 bg-[#001021] rounded-xl border border-[#002B49]">
                  <span className="text-slate-200 font-semibold">{unit}</span>
                  <span className="font-bold bg-[#002B49] text-[#00A3E0] px-3 py-1 rounded-lg text-xs border border-[#004B87]">
                    {count} Docs
                  </span>
                </div>
              ))
            ) : (
              <div className="text-slate-500 text-xs py-8 text-center bg-[#001021] rounded-xl border border-dashed border-[#002B49]">
                No business unit documents indexed yet.
              </div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
};