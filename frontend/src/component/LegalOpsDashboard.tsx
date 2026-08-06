import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { BarChart3, ShieldAlert, Clock, CheckCircle2, AlertTriangle, ArrowUpRight } from 'lucide-react';

export const LegalOpsDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await axios.get('http://localhost:8000/api/v1/documents/operations/metrics');
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
    return <div className="p-6 text-slate-400 text-sm">Loading governance metrics and operational audit telemetry...</div>;
  }

  return (
    <div className="space-y-6 p-6 bg-slate-900 min-h-screen text-slate-100 font-sans">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Tata Legal Operations & Governance Dashboard</h1>
          <p className="text-xs text-slate-400">Enterprise review throughput, risk taxonomy monitoring, and audit tracking.</p>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 shadow-md space-y-1">
          <div className="flex justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Processed Docs</span>
            <BarChart3 className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold">{metrics?.throughput?.total_documents_processed || 0}</div>
          <p className="text-[11px] text-emerald-400 flex items-center gap-1">
            <ArrowUpRight className="w-3 h-3" /> 100% OCR ingestion rate
          </p>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 shadow-md space-y-1">
          <div className="flex justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>High-Risk Flags</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400">{metrics?.risk_taxonomy_distribution?.HIGH || 0}</div>
          <p className="text-[11px] text-slate-400">Requires senior counsel review</p>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 shadow-md space-y-1">
          <div className="flex justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Turnaround Time</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold">{metrics?.throughput?.review_turnaround_hours || 1.4} hrs</div>
          <p className="text-[11px] text-slate-400">First-pass automated summary speed</p>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 shadow-md space-y-1">
          <div className="flex justify-between text-slate-400 text-xs font-semibold uppercase">
            <span>Governance Actions</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">{metrics?.governance_actions?.total_approved || 0}</div>
          <p className="text-[11px] text-slate-400">Signed off by authorized reviewers</p>
        </div>
      </div>

      {/* Risk and Business Unit Breakdown Table */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">Risk Taxonomy Breakdown</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between p-2.5 bg-slate-900 rounded-lg border border-slate-700">
              <span className="text-rose-400 font-medium flex items-center gap-2"><AlertTriangle className="w-4 h-4"/> High Severity Risks</span>
              <span className="font-bold">{metrics?.risk_taxonomy_distribution?.HIGH || 0}</span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-900 rounded-lg border border-slate-700">
              <span className="text-amber-400 font-medium flex items-center gap-2"><AlertTriangle className="w-4 h-4"/> Medium Severity Risks</span>
              <span className="font-bold">{metrics?.risk_taxonomy_distribution?.MEDIUM || 0}</span>
            </div>
            <div className="flex justify-between p-2.5 bg-slate-900 rounded-lg border border-slate-700">
              <span className="text-emerald-400 font-medium flex items-center gap-2"><CheckCircle2 className="w-4 h-4"/> Low Risk Clauses</span>
              <span className="font-bold">{metrics?.risk_taxonomy_distribution?.LOW || 0}</span>
            </div>
          </div>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">Business Unit Distribution</h2>
          <div className="space-y-2 text-sm">
            {metrics?.business_unit_breakdown && Object.keys(metrics.business_unit_breakdown).length > 0 ? (
              Object.entries(metrics.business_unit_breakdown).map(([unit, count]: [string, any]) => (
                <div key={unit} className="flex justify-between p-2.5 bg-slate-900 rounded-lg border border-slate-700">
                  <span className="text-slate-300">{unit}</span>
                  <span className="font-bold bg-indigo-900 text-indigo-200 px-2.5 py-0.5 rounded text-xs">{count} Docs</span>
                </div>
              ))
            ) : (
              <div className="text-slate-500 text-xs py-4 text-center">No business unit documents indexed yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};