import React, { useState } from 'react';
import {
  AlertTriangle,
  Clock,
  Layers,
  ArrowUpDown,
  Search,
  ChevronRight,
  Filter,
  CheckCircle,
  ExternalLink,
  Play,
  RotateCcw,
  Sparkles,
  ShieldAlert,
  XCircle
} from 'lucide-react';
import { PriorityQueueItem } from '../types';
import { runSimulation, createIncident } from '../api/client';

interface PriorityQueueProps {
  queue: PriorityQueueItem[];
  loading: boolean;
  onSelectIncident: (incidentId: string) => void;
  onRefresh: () => void;
}

export const PriorityQueue: React.FC<PriorityQueueProps> = ({
  queue,
  loading,
  onSelectIncident,
  onRefresh,
}) => {
  const [filterBand, setFilterBand] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedItem, setSelectedItem] = useState<PriorityQueueItem | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const criticalCount = queue.filter((i) => i.effective_priority_band === 'Critical').length;
  const highCount = queue.filter((i) => i.effective_priority_band === 'High').length;
  const overrideCount = queue.filter((i) => i.safety_override_active).length;
  const slaBreachCount = queue.filter((i) => i.is_sla_breached).length;

  const filtered = queue.filter((item) => {
    const matchesBand =
      filterBand === 'ALL' || item.effective_priority_band.toUpperCase() === filterBand.toUpperCase();
    const matchesSearch =
      item.incident_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.hazard_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.assigned_department.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesBand && matchesSearch;
  });

  const handleRunSimulation = async () => {
    setSimulating(true);
    setActionError(null);
    try {
      await runSimulation();
      onRefresh();
    } catch (err: any) {
      setActionError(err.message || 'Failed to execute 140-report simulation.');
    } finally {
      setSimulating(false);
    }
  };

  const handleLoadSample = async () => {
    setSimulating(true);
    setActionError(null);
    try {
      await createIncident({
        incident_id: 'INC-001',
        hazard_type: 'open_manhole',
        ward: 'Ward 07',
        evidence_status: 'corroborated',
        factors: {
          hazard_severity: 1.0,
          sensitive_site_proximity: 0.9,
          population_exposed: 0.7,
          weather_risk: 0.8,
          time_outstanding: 0.2,
          recurrence: 0.3,
        },
        sla_deadline: new Date(Date.now() + 2 * 3600 * 1000).toISOString(),
      });
      onRefresh();
    } catch (err: any) {
      // If already created, refresh is fine
      onRefresh();
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* KPI Metric Summary Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
        <div className="glass-card p-3.5 rounded-xl border border-white/60">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Total In Queue</span>
          <div className="flex items-baseline gap-1.5 mt-0.5">
            <span className="text-2xl font-black font-mono text-slate-900">{queue.length}</span>
            <span className="text-xs text-slate-500 font-medium">tickets</span>
          </div>
        </div>

        <div className="glass-card p-3.5 rounded-xl border border-white/60">
          <span className="text-[10px] font-bold text-rose-500 uppercase tracking-wider block">Critical Urgency</span>
          <div className="flex items-baseline gap-1.5 mt-0.5">
            <span className="text-2xl font-black font-mono text-rose-600">{criticalCount}</span>
            <span className="text-xs text-rose-400 font-medium">immediate</span>
          </div>
        </div>

        <div className="glass-card p-3.5 rounded-xl border border-white/60">
          <span className="text-[10px] font-bold text-amber-500 uppercase tracking-wider block">High Priority</span>
          <div className="flex items-baseline gap-1.5 mt-0.5">
            <span className="text-2xl font-black font-mono text-amber-700">{highCount}</span>
            <span className="text-xs text-amber-400 font-medium">2hr SLA</span>
          </div>
        </div>

        <div className="glass-card p-3.5 rounded-xl border border-white/60">
          <span className="text-[10px] font-bold text-rose-600 uppercase tracking-wider block">Safety Overrides</span>
          <div className="flex items-baseline gap-1.5 mt-0.5">
            <span className="text-2xl font-black font-mono text-rose-700">{overrideCount}</span>
            <span className="text-xs text-rose-400 font-medium">bypassed</span>
          </div>
        </div>

        <div className="glass-card p-3.5 rounded-xl border border-white/60 col-span-2 sm:col-span-1">
          <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider block">SLA Breaches</span>
          <div className="flex items-baseline gap-1.5 mt-0.5">
            <span className="text-2xl font-black font-mono text-amber-700">{slaBreachCount}</span>
            <span className="text-xs text-amber-500 font-medium">escalated</span>
          </div>
        </div>
      </div>

      {actionError && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold">
          {actionError}
        </div>
      )}

      {/* Header and Controls */}
      <div className="glass-card p-5 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Layers className="h-5 w-5 text-indigo-500" />
            Dynamic Municipal Priority Queue
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Ranked deterministically: Safety Overrides First &rarr; Risk Score &rarr; SLA Urgency &rarr; Age Tie-Breaker.
          </p>
        </div>

        {/* Filter Pills and Search */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="h-3.5 w-3.5 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Search ID, hazard..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="glass-input pl-9 pr-3 py-1.5 text-xs rounded-xl focus:outline-none w-44"
            />
          </div>

          <div className="flex items-center gap-1 bg-slate-200/50 p-1 rounded-xl text-xs font-semibold">
            {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'ROUTINE'].map((b) => (
              <button
                key={b}
                onClick={() => setFilterBand(b)}
                className={`px-2.5 py-1 rounded-lg transition ${
                  filterBand === b
                    ? 'bg-white text-slate-900 shadow-sm font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {b}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Layout: Queue Table + Selected Item Explanation Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Left Table (8 cols) */}
        <div className="lg:col-span-8 glass-card rounded-2xl overflow-hidden border border-white/60">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 border-b border-slate-200/80 text-slate-500 uppercase tracking-wider font-bold">
                <tr>
                  <th className="py-3 px-4 w-12 text-center">Rank</th>
                  <th className="py-3 px-4">Incident ID</th>
                  <th className="py-3 px-4">Hazard Category</th>
                  <th className="py-3 px-4 text-center">Score</th>
                  <th className="py-3 px-4 text-center">Priority</th>
                  <th className="py-3 px-4 text-center">SLA Status</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading || simulating ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-slate-400 font-semibold">
                      <div className="flex items-center justify-center gap-2">
                        <RotateCcw className="h-4 w-4 animate-spin text-sky-600" />
                        <span>{simulating ? 'Ingesting and ranking reports via backend engine...' : 'Loading ranked municipal queue...'}</span>
                      </div>
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-10 px-4 text-center">
                      {queue.length === 0 ? (
                        /* Empty Database Prompt */
                        <div className="max-w-md mx-auto space-y-3 py-4">
                          <div className="h-12 w-12 rounded-2xl bg-indigo-100 text-indigo-600 flex items-center justify-center mx-auto shadow-sm">
                            <Layers className="h-6 w-6" />
                          </div>
                          <div>
                            <h4 className="text-sm font-bold text-slate-800">Municipal Database Initial State</h4>
                            <p className="text-xs text-slate-500 mt-1">
                              No active incidents currently logged. Ingest and score the Challenge 10 storm scenario or load the Section 8 benchmark incident directly through the backend.
                            </p>
                          </div>
                          <div className="flex flex-col sm:flex-row items-center justify-center gap-2 pt-2">
                            <button
                              onClick={handleRunSimulation}
                              disabled={simulating}
                              className="w-full sm:w-auto px-4 py-2.5 rounded-xl font-bold text-white bg-gradient-to-r from-rose-500 to-indigo-600 hover:opacity-95 shadow-md shadow-rose-500/20 text-xs flex items-center justify-center gap-2 transition"
                            >
                              <Play className="h-3.5 w-3.5 fill-white" />
                              <span>Run 140-Report Simulation</span>
                            </button>
                            <button
                              onClick={handleLoadSample}
                              disabled={simulating}
                              className="w-full sm:w-auto px-4 py-2.5 rounded-xl font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 text-xs shadow-sm transition"
                            >
                              Load INC-001 Benchmark
                            </button>
                          </div>
                        </div>
                      ) : (
                        /* Filtered Empty State */
                        <div className="space-y-2 py-4">
                          <p className="text-slate-500 font-semibold">No incidents match current filter criteria.</p>
                          <button
                            onClick={() => { setFilterBand('ALL'); setSearchQuery(''); }}
                            className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs"
                          >
                            Reset All Filters
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ) : (
                  filtered.map((item) => {
                    const isSelected = selectedItem?.incident_id === item.incident_id;
                    return (
                      <tr
                        key={item.incident_id}
                        onClick={() => setSelectedItem(item)}
                        className={`hover:bg-sky-50/50 cursor-pointer transition ${
                          isSelected ? 'bg-sky-50/80 font-medium' : ''
                        }`}
                      >
                        <td className="py-3 px-4 text-center font-bold text-slate-700 font-mono">
                          #{item.queue_rank}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-slate-900">
                          {item.incident_id}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-semibold text-slate-800 capitalize block">
                            {item.hazard_type.replace(/_/g, ' ')}
                          </span>
                          {item.safety_override_active && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-100 px-1.5 py-0.2 rounded mt-0.5">
                              <AlertTriangle className="h-2.5 w-2.5" />
                              OVERRIDE
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center font-mono font-black text-slate-800">
                          {item.risk_score.toFixed(1)}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${
                              item.effective_priority_band === 'Critical'
                                ? 'bg-rose-100 text-rose-700 border border-rose-300'
                                : item.effective_priority_band === 'High'
                                ? 'bg-amber-100 text-amber-800 border border-amber-300'
                                : item.effective_priority_band === 'Medium'
                                ? 'bg-sky-100 text-sky-800 border border-sky-300'
                                : 'bg-slate-100 text-slate-700 border border-slate-300'
                            }`}
                          >
                            {item.effective_priority_band}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              item.is_sla_breached
                                ? 'bg-rose-100 text-rose-700 font-black animate-pulse'
                                : item.sla_status === 'imminent_breach'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-emerald-100 text-emerald-800'
                            }`}
                          >
                            {item.sla_status.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-600 truncate max-w-[140px]" title={item.assigned_department}>
                          {item.assigned_department}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectIncident(item.incident_id);
                            }}
                            className="p-1 rounded bg-slate-100 hover:bg-sky-100 text-slate-600 hover:text-sky-700 transition"
                            title="Open Incident Audit"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Detail Explanation Panel (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          {selectedItem ? (
            <div className="glass-card p-5 rounded-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Queue Inspector</span>
                  <h3 className="text-base font-bold text-slate-800 font-mono">
                    {selectedItem.incident_id}
                  </h3>
                </div>
                <button
                  onClick={() => onSelectIncident(selectedItem.incident_id)}
                  className="px-2.5 py-1 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 flex items-center gap-1 shadow-sm transition"
                >
                  <span>Full Dossier</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>

              {/* Ranking Explanation */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase block">Deterministic Ranking Rationale</span>
                <p className="text-xs text-slate-800 font-medium">{selectedItem.ranking_explanation}</p>
              </div>

              {/* Safety Override Status */}
              {selectedItem.safety_override_active && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-300 space-y-1">
                  <span className="text-[10px] font-bold text-rose-800 uppercase flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3 text-rose-600" />
                    Safety Override Active
                  </span>
                  <p className="text-xs text-rose-900">{selectedItem.safety_override_reason}</p>
                </div>
              )}

              {/* Recommended Action */}
              <div className="space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase block">Recommended Next Action</span>
                <div className="p-2.5 rounded-lg bg-sky-50 border border-sky-200 text-xs font-semibold text-sky-900">
                  {selectedItem.recommended_action}
                </div>
              </div>

              {/* Factor Contribution Pills */}
              <div className="space-y-1.5 pt-2 border-t border-slate-100">
                <span className="text-[10px] font-bold text-slate-500 uppercase block">Factor Point Breakdown</span>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  {Object.entries(selectedItem.factor_contributions).map(([f, pts]) => (
                    <div key={f} className="p-2 rounded bg-slate-100/70 flex justify-between">
                      <span className="capitalize text-slate-600">{f.split('_')[0]}</span>
                      <span className="font-mono font-bold text-slate-800">+{pts.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-card p-6 rounded-2xl text-center text-slate-400 space-y-2 flex flex-col items-center justify-center h-64">
              <ArrowUpDown className="h-8 w-8 text-slate-300" />
              <p className="text-xs font-semibold text-slate-500">
                {queue.length > 0
                  ? 'Select any incident from the priority queue to inspect its explainable ranking rationale and factor contributions.'
                  : 'Queue is currently empty. Run the 140-report simulation to populate live municipal incidents.'}
              </p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
