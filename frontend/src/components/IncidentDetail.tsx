import React, { useEffect, useState } from 'react';
import {
  ShieldAlert,
  Clock,
  History,
  AlertTriangle,
  UserCheck,
  CheckCircle2,
  Lock,
  Layers,
  ChevronRight,
  ArrowLeft
} from 'lucide-react';
import { applyManualOverride, fetchIncidentDetail } from '../api/client';
import { IncidentDetailResponse } from '../types';

interface IncidentDetailProps {
  incidentId: string;
  onBack: () => void;
  onRefresh: () => void;
}

export const IncidentDetail: React.FC<IncidentDetailProps> = ({
  incidentId,
  onBack,
  onRefresh,
}) => {
  const [detail, setDetail] = useState<IncidentDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Manual override modal state
  const [showOverrideModal, setShowOverrideModal] = useState<boolean>(false);
  const [authorizedBy, setAuthorizedBy] = useState<string>('Duty Officer S. Murthy');
  const [role, setRole] = useState<string>('duty_officer');
  const [reason, setReason] = useState<string>('Impending school dismissal with open sewer pit adjacent to bus gate.');
  const [targetSeverity, setTargetSeverity] = useState<string>('Critical');
  const [overrideLoading, setOverrideLoading] = useState<boolean>(false);
  const [overrideError, setOverrideError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchIncidentDetail(incidentId);
      setDetail(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load incident detail.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (incidentId) {
      loadData();
    }
  }, [incidentId]);

  const handleApplyOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    setOverrideLoading(true);
    setOverrideError(null);
    try {
      await applyManualOverride(incidentId, {
        authorized_by: authorizedBy,
        role: role,
        reason: reason,
        target_severity: targetSeverity,
      });
      setShowOverrideModal(false);
      loadData();
      onRefresh();
    } catch (err: any) {
      setOverrideError(err.message || 'Failed to apply manual override.');
    } finally {
      setOverrideLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="glass-card p-12 rounded-2xl text-center text-slate-400 font-semibold">
        Loading incident dossier and audit ledger for {incidentId}...
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="glass-card p-8 rounded-2xl text-center space-y-4">
        <p className="text-sm text-rose-600 font-bold">{error || 'Incident not found'}</p>
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-xl bg-slate-200 text-slate-800 text-xs font-bold"
        >
          &larr; Back to Priority Queue
        </button>
      </div>
    );
  }

  const latest = detail.latest_assessment;

  return (
    <div className="space-y-6">
      
      {/* Top Navigation & Action Header */}
      <div className="glass-card p-5 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 rounded-xl bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 transition shadow-sm"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-black font-mono text-slate-900">{detail.incident_id}</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase bg-slate-100 text-slate-700 border border-slate-200">
                {detail.hazard_type.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              {detail.ward} • Evidence: <span className="font-semibold text-slate-700 uppercase">{detail.evidence_status}</span>
            </p>
          </div>
        </div>

        {/* Action Button: Manual Emergency Override */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowOverrideModal(true)}
            className="px-4 py-2 rounded-xl bg-rose-500 hover:bg-rose-600 text-white text-xs font-bold flex items-center gap-1.5 shadow-md shadow-rose-500/20 active:scale-95 transition"
          >
            <Lock className="h-3.5 w-3.5" />
            <span>Apply Authorized Override</span>
          </button>
        </div>
      </div>

      {/* Grid: Left Assessment Summary & Factors (7 cols) + Right History & Audit (5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Left Column (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          
          {/* Latest Assessment Summary */}
          {latest && (
            <div className="glass-card p-6 rounded-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Active Physical Assessment
                </span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-black uppercase ${
                  latest.priority_band === 'Critical'
                    ? 'bg-rose-100 text-rose-700'
                    : latest.priority_band === 'High'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-sky-100 text-sky-800'
                }`}>
                  {latest.priority_band} BAND
                </span>
              </div>

              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-black font-mono text-slate-900">
                  {latest.risk_score.toFixed(1)}
                </span>
                <span className="text-slate-400 font-semibold">/ 100</span>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 space-y-1">
                <span className="font-bold text-slate-900 block">Assigned Response:</span>
                <p>{latest.recommended_action}</p>
              </div>

              {/* Active Override Banner if present */}
              {latest.safety_override.active && (
                <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-300 text-xs text-rose-900 space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <AlertTriangle className="h-4 w-4 text-rose-600" />
                    Safety Override Active ({latest.safety_override.effective_severity})
                  </div>
                  <p className="text-[11px] text-rose-800">{latest.safety_override.summary}</p>
                </div>
              )}
            </div>
          )}

          {/* Factor Points Breakdown Table */}
          {latest && (
            <div className="glass-card p-5 rounded-2xl space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Factor Normalization &amp; Contribution Breakdown
              </h3>
              <div className="space-y-2.5">
                {Object.entries(latest.factor_contributions).map(([f, pts]) => (
                  <div key={f} className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/60 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-bold capitalize text-slate-800">{f.replace(/_/g, ' ')}</span>
                      <span className="text-[10px] text-slate-400 block">Deterministic weighted contribution</span>
                    </div>
                    <span className="font-mono font-bold text-slate-900 text-sm">+{pts.toFixed(1)} pts</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Missing Data Warnings */}
          {latest && latest.uncertainty_flags.length > 0 && (
            <div className="glass-card p-5 rounded-2xl space-y-2 bg-amber-50/50 border border-amber-200">
              <h3 className="text-xs font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4 text-amber-700" />
                Uncertainty &amp; Missing Data Flags
              </h3>
              <ul className="text-xs text-amber-800 space-y-1 list-disc pl-4">
                {latest.uncertainty_flags.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

        </div>

        {/* Right Column: Assessment History & Tamper-Evident Audit (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          
          {/* Assessment History Timeline */}
          <div className="glass-card p-5 rounded-2xl space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <History className="h-4 w-4 text-indigo-500" />
              Immutable Assessment History ({detail.assessment_history.length})
            </h3>

            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {detail.assessment_history.map((hist, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1">
                  <div className="flex justify-between items-center font-bold">
                    <span className="font-mono text-slate-800">Score: {hist.risk_score.toFixed(1)} ({hist.priority_band})</span>
                    <span className="text-[10px] text-slate-400">{new Date(hist.assessed_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-[11px] text-slate-600 truncate">{hist.recommended_action}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Audit Event Ledger */}
          <div className="glass-card p-5 rounded-2xl space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <UserCheck className="h-4 w-4 text-emerald-500" />
              Tamper-Evident Audit Ledger
            </h3>

            <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
              {detail.audit_logs.map((log) => (
                <div key={log.id} className="p-2.5 rounded-lg bg-slate-50/70 border border-slate-200/60 text-xs space-y-0.5">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="font-bold text-slate-800 font-mono">{log.action_type}</span>
                    <span className="text-slate-400 text-[10px]">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div className="text-[10px] text-slate-500">Actor: <span className="font-semibold text-slate-700">{log.actor}</span></div>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>

      {/* Manual Override Modal */}
      {showOverrideModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="glass-card p-6 rounded-2xl max-w-md w-full shadow-2xl border border-white space-y-4 bg-white">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="font-bold text-slate-900 flex items-center gap-2 text-sm">
                <Lock className="h-4 w-4 text-rose-600" />
                Authorized Emergency Override
              </h3>
              <button
                onClick={() => setShowOverrideModal(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleApplyOverride} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Authorizing Official Name</label>
                <input
                  type="text"
                  required
                  value={authorizedBy}
                  onChange={(e) => setAuthorizedBy(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Role / Authorization Level</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl focus:outline-none bg-white font-medium"
                >
                  <option value="duty_officer">Municipal Duty Officer</option>
                  <option value="supervisor">Ward Supervisor</option>
                  <option value="admin">System Administrator</option>
                  <option value="municipal_commissioner">Municipal Commissioner</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Target Priority Severity</label>
                <select
                  value={targetSeverity}
                  onChange={(e) => setTargetSeverity(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl focus:outline-none bg-white font-medium"
                >
                  <option value="Critical">Critical (Immediate Dispatch)</option>
                  <option value="High">High (Within 2 Hours)</option>
                  <option value="Medium">Medium</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Documented Justification (Audit Record)</label>
                <textarea
                  required
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl focus:outline-none"
                  placeholder="Explain why this incident warrants an emergency safety override..."
                />
              </div>

              {overrideError && (
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">
                  {overrideError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowOverrideModal(false)}
                  className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={overrideLoading}
                  className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold shadow-md shadow-rose-600/20"
                >
                  {overrideLoading ? 'Applying...' : 'Sign & Apply Override'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
