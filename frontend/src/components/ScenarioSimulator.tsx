import React, { useEffect, useState } from 'react';
import {
  Play,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  Clock,
  Layers,
  Sparkles,
  ShieldCheck,
  Building,
  Flame,
  Radio,
  ExternalLink
} from 'lucide-react';
import { fetchSimulationStatus, runSimulation } from '../api/client';
import { SimulationResult } from '../types';

interface ScenarioSimulatorProps {
  onSelectIncident: (incidentId: string) => void;
  onRefreshQueue: () => void;
}

export const ScenarioSimulator: React.FC<ScenarioSimulatorProps> = ({
  onSelectIncident,
  onRefreshQueue,
}) => {
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = async () => {
    try {
      const data = await fetchSimulationStatus();
      setResult(data);
    } catch (err: any) {
      // If none run yet, that's okay
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleRunSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runSimulation();
      setResult(data);
      onRefreshQueue();
    } catch (err: any) {
      setError(err.message || 'Simulation execution failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header and Simulation Trigger */}
      <div className="glass-card p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-5 border border-white/60">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              <Radio className="h-5 w-5 text-rose-500 animate-pulse" />
              140-Report / 3-Hour Cloudburst Stress Test
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
              SYNTHETIC SCENARIO
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Simulates a sudden municipal storm event generating 140 incoming reports across 180 minutes. Tests evidence clustering, risk scoring, boundary disputes, abuse defense, and genuine emergency preservation.
          </p>
        </div>

        <button
          onClick={handleRunSimulation}
          disabled={loading}
          className="px-6 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-rose-500 via-indigo-600 to-sky-500 hover:opacity-95 shadow-lg shadow-rose-500/25 active:scale-95 transition flex items-center gap-2 text-sm shrink-0"
        >
          {loading ? (
            <>
              <RotateCcw className="h-4 w-4 animate-spin" />
              <span>Simulating Ingestion &amp; Triage...</span>
            </>
          ) : (
            <>
              <Play className="h-4 w-4 fill-white" />
              <span>Execute 140-Report Stress Test</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold">
          {error}
        </div>
      )}

      {/* 4 Scenario Category Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Category A */}
        <div className="glass-card p-4 rounded-xl space-y-1.5 border-l-4 border-l-rose-500">
          <span className="text-[10px] font-black uppercase tracking-wider text-rose-600 block">
            Category A (28 Reports)
          </span>
          <h4 className="text-xs font-bold text-slate-800">School Open Manhole</h4>
          <p className="text-[11px] text-slate-500">
            28 varied reports merged into unified incident cluster. Triggers Critical Safety Override (<span className="font-semibold text-rose-600">Score 91.2</span>).
          </p>
        </div>

        {/* Category B */}
        <div className="glass-card p-4 rounded-xl space-y-1.5 border-l-4 border-l-amber-500">
          <span className="text-[10px] font-black uppercase tracking-wider text-amber-600 block">
            Category B (36 Reports)
          </span>
          <h4 className="text-xs font-bold text-slate-800">Ward Boundary Waterlog</h4>
          <p className="text-[11px] text-slate-500">
            Roads vs Drain Dept deadlock. Clock never resets; auto-escalated to Duty Officer on SLA breach alert.
          </p>
        </div>

        {/* Category C */}
        <div className="glass-card p-4 rounded-xl space-y-1.5 border-l-4 border-l-indigo-500">
          <span className="text-[10px] font-black uppercase tracking-wider text-indigo-600 block">
            Category C (32 Reports)
          </span>
          <h4 className="text-xs font-bold text-slate-800">Coordinated Bot Burst</h4>
          <p className="text-[11px] text-slate-500">
            31 bot reports quarantined for review. <span className="font-bold text-emerald-700">1 genuine emergency preserved</span> &amp; dispatched.
          </p>
        </div>

        {/* Category D */}
        <div className="glass-card p-4 rounded-xl space-y-1.5 border-l-4 border-l-sky-500">
          <span className="text-[10px] font-black uppercase tracking-wider text-sky-600 block">
            Category D (44 Reports)
          </span>
          <h4 className="text-xs font-bold text-slate-800">Routine Civic Influx</h4>
          <p className="text-[11px] text-slate-500">
            Potholes, streetlights, curbs. Clustered into maintenance batches without disrupting emergency queues.
          </p>
        </div>

      </div>

      {result && (
        <div className="space-y-6">

          {/* KPI Stat Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            
            <div className="glass-card p-4 rounded-xl text-center">
              <span className="text-[10px] font-bold text-slate-400 uppercase block">Reports Ingested</span>
              <span className="text-2xl font-black font-mono text-slate-800">{result.total_reports_ingested}</span>
              <span className="text-[10px] text-emerald-600 font-semibold block mt-0.5">100% Verified</span>
            </div>

            <div className="glass-card p-4 rounded-xl text-center">
              <span className="text-[10px] font-bold text-slate-400 uppercase block">Proposed Clusters</span>
              <span className="text-2xl font-black font-mono text-indigo-600">{result.proposed_clusters_count}</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Evidence Graph</span>
            </div>

            <div className="glass-card p-4 rounded-xl text-center">
              <span className="text-[10px] font-bold text-slate-400 uppercase block">Triaged Incidents</span>
              <span className="text-2xl font-black font-mono text-sky-600">{result.incidents_triaged_count}</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Active Tickets</span>
            </div>

            <div className="glass-card p-4 rounded-xl text-center">
              <span className="text-[10px] font-bold text-slate-400 uppercase block">Safety Overrides</span>
              <span className="text-2xl font-black font-mono text-rose-600">{result.safety_overrides_triggered}</span>
              <span className="text-[10px] text-rose-500 font-semibold block mt-0.5">Immediate Review</span>
            </div>

            <div className="glass-card p-4 rounded-xl text-center">
              <span className="text-[10px] font-bold text-slate-400 uppercase block">SLA Breaches</span>
              <span className="text-2xl font-black font-mono text-amber-600">{result.sla_breaches_detected}</span>
              <span className="text-[10px] text-amber-700 font-semibold block mt-0.5">Escalated</span>
            </div>

            <div className="glass-card p-4 rounded-xl text-center">
              <span className="text-[10px] font-bold text-slate-400 uppercase block">Genuine Preserved</span>
              <span className="text-base font-black text-emerald-600 block mt-1">
                {result.genuine_hazard_preserved_under_attack ? '✓ 100% SECURE' : 'COMPROMISED'}
              </span>
              <span className="text-[9px] text-slate-400 block">Abuse Resilience</span>
            </div>

          </div>

          {/* Resulting Top Ranked Incidents Table */}
          <div className="glass-card p-6 rounded-2xl space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center justify-between">
              <span>Simulation Priority Triage Output (Top Incidents)</span>
              <span className="text-xs text-sky-600 font-mono">Calculated Live from Database</span>
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-bold">
                  <tr>
                    <th className="py-2.5 px-3 w-12 text-center">Rank</th>
                    <th className="py-2.5 px-3">Incident ID</th>
                    <th className="py-2.5 px-3">Hazard Type</th>
                    <th className="py-2.5 px-3 text-center">Score</th>
                    <th className="py-2.5 px-3 text-center">Band</th>
                    <th className="py-2.5 px-3 text-center">Override</th>
                    <th className="py-2.5 px-3">Recommended Action</th>
                    <th className="py-2.5 px-3 text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.highest_priority_incidents.map((inc) => (
                    <tr key={inc.incident_id} className="hover:bg-slate-50">
                      <td className="py-3 px-3 text-center font-bold font-mono">#{inc.queue_rank}</td>
                      <td className="py-3 px-3 font-mono font-bold text-slate-900">{inc.incident_id}</td>
                      <td className="py-3 px-3 capitalize font-semibold text-slate-800">{inc.hazard_type.replace(/_/g, ' ')}</td>
                      <td className="py-3 px-3 text-center font-mono font-black">{inc.risk_score.toFixed(1)}</td>
                      <td className="py-3 px-3 text-center">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          inc.effective_priority_band === 'Critical' ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {inc.effective_priority_band}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-center">
                        {inc.safety_override_active ? (
                          <span className="px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 text-[10px] font-bold">
                            ACTIVE
                          </span>
                        ) : (
                          <span className="text-slate-400 text-[10px]">None</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-slate-600 truncate max-w-xs">{inc.recommended_action}</td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => onSelectIncident(inc.incident_id)}
                          className="px-2 py-1 rounded bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold text-[11px]"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Department Allocations Grid */}
          <div className="glass-card p-5 rounded-2xl space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Department Workload Allocations
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(result.department_assignments).map(([dept, count]) => (
                <div key={dept} className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                  <div className="text-slate-500 truncate" title={dept}>{dept}</div>
                  <div className="text-lg font-bold text-slate-800 font-mono mt-1">{count} Active Tickets</div>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

    </div>
  );
};
