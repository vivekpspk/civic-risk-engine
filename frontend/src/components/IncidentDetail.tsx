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
  ArrowLeft,
  Camera,
  UserPlus,
  RotateCcw,
  CheckSquare,
  XCircle,
  FileCheck2,
  ExternalLink,
  MessageSquare
} from 'lucide-react';
import {
  applyManualOverride,
  fetchIncidentDetail,
  fetchEvidenceComparison,
  fetchMunicipalWorkers,
  assignWorker,
  verifyResolution,
  reopenComplaint
} from '../api/client';
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
  const [comparison, setComparison] = useState<any>(null);
  const [workers, setWorkers] = useState<any[]>([]);
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

  // Lifecycle Modals State
  const [showAssignModal, setShowAssignModal] = useState<boolean>(false);
  const [selectedWorker, setSelectedWorker] = useState<string>('WRK-101');
  const [assignInstructions, setAssignInstructions] = useState<string>('Dispatch team immediately and secure hazard.');

  const [showVerifyModal, setShowVerifyModal] = useState<boolean>(false);
  const [verifyNotes, setVerifyNotes] = useState<string>('Verified before-and-after photo evidence. Repair meets municipal quality standard.');

  const [showRejectModal, setShowRejectModal] = useState<boolean>(false);
  const [rejectNotes, setRejectNotes] = useState<string>('Water is still backing up. Requires deep pipe clearing.');

  const [showReopenModal, setShowReopenModal] = useState<boolean>(false);
  const [reopenReason, setReopenReason] = useState<string>('Recurrence reported by citizen post-storm; temporary patch failed.');

  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [incidentData, compData, workersList] = await Promise.all([
        fetchIncidentDetail(incidentId),
        fetchEvidenceComparison(incidentId).catch(() => null),
        fetchMunicipalWorkers().catch(() => [])
      ]);
      setDetail(incidentData);
      setComparison(compData);
      setWorkers(workersList);
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
      setActionNotice('Emergency override applied and recorded in audit ledger.');
      loadData();
      onRefresh();
    } catch (err: any) {
      setOverrideError(err.message || 'Failed to apply manual override.');
    } finally {
      setOverrideLoading(false);
    }
  };

  const handleAssignWorker = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      await assignWorker(incidentId, {
        worker_id: selectedWorker,
        admin_id: authorizedBy,
        instructions: assignInstructions,
      });
      setShowAssignModal(false);
      setActionNotice(`Successfully assigned to worker ${selectedWorker}.`);
      loadData();
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to assign worker');
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerifyResolution = async (decision: 'approve' | 'reject') => {
    setActionLoading(true);
    try {
      await verifyResolution(incidentId, {
        decision: decision,
        admin_id: authorizedBy,
        notes: decision === 'approve' ? verifyNotes : rejectNotes,
      });
      setShowVerifyModal(false);
      setShowRejectModal(false);
      setActionNotice(
        decision === 'approve'
          ? 'Resolution approved as COMPLETED. Citizen SMS notification dispatched.'
          : 'Resolution rejected and returned to worker for rework.'
      );
      loadData();
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to verify resolution');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReopen = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      await reopenComplaint(incidentId, {
        admin_id: authorizedBy,
        reason: reopenReason,
      });
      setShowReopenModal(false);
      setActionNotice('Complaint reopened and restored to actionable dispatch queue.');
      loadData();
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to reopen complaint');
    } finally {
      setActionLoading(false);
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
  const currentStatus = (detail as any).status ? (detail as any).status.toUpperCase() : 'SUBMITTED';

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
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${
                currentStatus === 'COMPLETED'
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : currentStatus === 'REOPENED'
                  ? 'bg-rose-100 text-rose-800 border border-rose-300'
                  : currentStatus === 'VERIFICATION_REQUIRED'
                  ? 'bg-purple-100 text-purple-800 border border-purple-300'
                  : 'bg-sky-100 text-sky-800 border border-sky-300'
              }`}>
                {currentStatus}
              </span>
              <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase bg-slate-100 text-slate-600">
                {detail.hazard_type.replace(/_/g, ' ')}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              {detail.ward} • Assigned Dept: <span className="font-semibold text-slate-700">{detail.assigned_department}</span>
            </p>
          </div>
        </div>

        {/* Action Buttons: Lifecycle Management */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Assign Worker Button */}
          <button
            onClick={() => setShowAssignModal(true)}
            className="px-3 py-1.5 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 text-xs font-bold flex items-center gap-1.5 transition shadow-sm"
          >
            <UserPlus className="h-3.5 w-3.5" />
            <span>Assign Worker</span>
          </button>

          {/* Verification Buttons */}
          {(currentStatus === 'VERIFICATION_REQUIRED' || currentStatus === 'RESOLUTION_SUBMITTED') && (
            <>
              <button
                onClick={() => setShowVerifyModal(true)}
                className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1.5 transition shadow-md shadow-emerald-600/20"
              >
                <CheckSquare className="h-3.5 w-3.5" />
                <span>Verify &amp; Approve</span>
              </button>
              <button
                onClick={() => setShowRejectModal(true)}
                className="px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 hover:bg-amber-100 text-xs font-bold flex items-center gap-1.5 transition"
              >
                <XCircle className="h-3.5 w-3.5" />
                <span>Reject Resolution</span>
              </button>
            </>
          )}

          {/* Reopen Button if Completed */}
          {currentStatus === 'COMPLETED' && (
            <button
              onClick={() => setShowReopenModal(true)}
              className="px-3 py-1.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 hover:bg-rose-100 text-xs font-bold flex items-center gap-1.5 transition"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reopen Complaint</span>
            </button>
          )}

          {/* Manual Emergency Override */}
          <button
            onClick={() => setShowOverrideModal(true)}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm active:scale-95 transition"
          >
            <Lock className="h-3 w-3" />
            <span>Emergency Override</span>
          </button>
        </div>
      </div>

      {actionNotice && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs font-semibold flex items-center justify-between">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-emerald-600 font-bold">&times;</button>
        </div>
      )}

      {/* BEFORE & AFTER PHOTOGRAPHIC EVIDENCE COMPARISON CARD */}
      <div className="glass-card p-6 rounded-2xl space-y-4 border border-white/60 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Camera className="h-4 w-4 text-sky-600" />
            <h3 className="text-sm font-black text-slate-900 uppercase tracking-tight">
              Before-and-After Photographic Proof &amp; Verification Dossier
            </h3>
          </div>
          <span className="text-xs text-slate-500 font-semibold">
            Status: <span className="font-bold text-slate-800 uppercase">{currentStatus}</span>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* BEFORE EVIDENCE PANEL */}
          <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase tracking-wider text-rose-700 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                Before Photo (Reported Hazard)
              </span>
              <span className="text-[10px] text-slate-400 font-mono">EXIF Scrubbed</span>
            </div>

            {comparison && comparison.before_evidence && comparison.before_evidence.length > 0 ? (
              <div className="space-y-2">
                {comparison.before_evidence.map((ev: any, idx: number) => (
                  <div key={idx} className="rounded-lg overflow-hidden border border-slate-200 bg-white">
                    <img
                      src={ev.view_url}
                      alt="Before Hazard"
                      className="w-full h-44 object-cover hover:scale-[1.02] transition duration-200"
                    />
                    <div className="p-2 text-[11px] text-slate-600 flex justify-between items-center">
                      <span>{ev.caption || 'Initial hazard photo submitted by citizen'}</span>
                      <span className="text-[10px] text-slate-400">{new Date(ev.uploaded_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-40 rounded-lg border-2 border-dashed border-slate-200 flex flex-col items-center justify-center text-slate-400 text-xs">
                <Camera className="h-8 w-8 text-slate-300 mb-1" />
                <span>No initial photographic upload on record</span>
              </div>
            )}
          </div>

          {/* AFTER EVIDENCE PANEL */}
          <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase tracking-wider text-emerald-700 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                After Photo (Field Resolution Proof)
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Verified by Worker</span>
            </div>

            {comparison && comparison.after_evidence && comparison.after_evidence.length > 0 ? (
              <div className="space-y-2">
                {comparison.after_evidence.map((ev: any, idx: number) => (
                  <div key={idx} className="rounded-lg overflow-hidden border border-slate-200 bg-white">
                    <img
                      src={ev.view_url}
                      alt="After Resolution"
                      className="w-full h-44 object-cover hover:scale-[1.02] transition duration-200"
                    />
                    <div className="p-2 text-[11px] text-slate-600 flex justify-between items-center">
                      <span>{ev.caption || 'Resolution photo submitted by field crew'}</span>
                      <span className="text-[10px] text-slate-400">{new Date(ev.uploaded_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-40 rounded-lg border-2 border-dashed border-slate-200 flex flex-col items-center justify-center text-slate-400 text-xs">
                <Camera className="h-8 w-8 text-slate-300 mb-1" />
                <span>Awaiting field worker repair and after-photo upload</span>
              </div>
            )}
          </div>
        </div>

        {/* Resolution Notes Banner */}
        {comparison && comparison.resolution_summary && (
          <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200 text-xs text-sky-900 space-y-1">
            <div className="flex items-center justify-between font-bold">
              <span>Field Worker Resolution Summary:</span>
              <span className="text-[11px] text-sky-700">Worker ID: {comparison.resolution_summary.worker_id}</span>
            </div>
            <p className="text-slate-800 font-medium">{comparison.resolution_summary.description}</p>
            <p className="text-[11px] text-slate-600">Action: {comparison.resolution_summary.action_taken}</p>
          </div>
        )}
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

      {/* Assign Field Worker Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="glass-card p-6 rounded-2xl max-w-md w-full shadow-2xl border border-white space-y-4 bg-white">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="font-bold text-slate-900 flex items-center gap-2 text-sm">
                <UserPlus className="h-4 w-4 text-indigo-600" />
                Dispatch &amp; Assign Municipal Worker
              </h3>
              <button onClick={() => setShowAssignModal(false)} className="text-slate-400 hover:text-slate-600 font-bold">&times;</button>
            </div>

            <form onSubmit={handleAssignWorker} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Select Field Worker</label>
                <select
                  value={selectedWorker}
                  onChange={(e) => setSelectedWorker(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl focus:outline-none bg-white font-medium"
                >
                  {workers.length > 0 ? (
                    workers.map((w: any) => (
                      <option key={w.worker_id} value={w.worker_id}>
                        {w.name} ({w.worker_id}) - {w.department} [{w.ward}]
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="WRK-101">Ramesh Kumar (WRK-101) - Stormwater Drainage</option>
                      <option value="WRK-102">Priya Sharma (WRK-102) - Roads &amp; Infrastructure</option>
                      <option value="WRK-103">Suresh Reddy (WRK-103) - Electrical &amp; Streetlights</option>
                      <option value="WRK-104">Ananya Das (WRK-104) - Water Supply</option>
                    </>
                  )}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Operational Instructions</label>
                <textarea
                  rows={3}
                  value={assignInstructions}
                  onChange={(e) => setAssignInstructions(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl focus:outline-none"
                  placeholder="Specific task instructions for field worker..."
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAssignModal(false)}
                  className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold shadow-md shadow-indigo-600/20"
                >
                  {actionLoading ? 'Assigning...' : 'Confirm Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Verify & Approve Modal */}
      {showVerifyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="glass-card p-6 rounded-2xl max-w-md w-full shadow-2xl border border-white space-y-4 bg-white">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="font-bold text-slate-900 flex items-center gap-2 text-sm">
                <CheckSquare className="h-4 w-4 text-emerald-600" />
                Administrator Resolution Verification
              </h3>
              <button onClick={() => setShowVerifyModal(false)} className="text-slate-400 hover:text-slate-600 font-bold">&times;</button>
            </div>

            <div className="space-y-3.5 text-xs">
              <p className="text-slate-600">
                Approving this resolution will mark the complaint as <span className="font-bold text-emerald-700">COMPLETED</span>, archive the verified before-and-after proof, and trigger an automated SMS completion notification to the citizen.
              </p>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Verification Inspection Notes</label>
                <textarea
                  rows={3}
                  value={verifyNotes}
                  onChange={(e) => setVerifyNotes(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowVerifyModal(false)}
                  className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleVerifyResolution('approve')}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold shadow-md shadow-emerald-600/20"
                >
                  {actionLoading ? 'Approving...' : 'Approve & Dispatch SMS'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reject Resolution Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="glass-card p-6 rounded-2xl max-w-md w-full shadow-2xl border border-white space-y-4 bg-white">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="font-bold text-slate-900 flex items-center gap-2 text-sm">
                <XCircle className="h-4 w-4 text-amber-600" />
                Reject Resolution Submission
              </h3>
              <button onClick={() => setShowRejectModal(false)} className="text-slate-400 hover:text-slate-600 font-bold">&times;</button>
            </div>

            <div className="space-y-3.5 text-xs">
              <p className="text-slate-600">
                Provide mandatory feedback. The task will return to <span className="font-bold text-amber-700">IN_PROGRESS</span> and alert the assigned field crew.
              </p>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Rejection Feedback (Required)</label>
                <textarea
                  rows={3}
                  required
                  value={rejectNotes}
                  onChange={(e) => setRejectNotes(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl focus:outline-none"
                  placeholder="Detail the deficiencies preventing resolution approval..."
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowRejectModal(false)}
                  className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={actionLoading || !rejectNotes.trim()}
                  onClick={() => handleVerifyResolution('reject')}
                  className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold"
                >
                  {actionLoading ? 'Rejecting...' : 'Reject & Return to Worker'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reopen Modal */}
      {showReopenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="glass-card p-6 rounded-2xl max-w-md w-full shadow-2xl border border-white space-y-4 bg-white">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="font-bold text-slate-900 flex items-center gap-2 text-sm">
                <RotateCcw className="h-4 w-4 text-rose-600" />
                Reopen Civic Complaint
              </h3>
              <button onClick={() => setShowReopenModal(false)} className="text-slate-400 hover:text-slate-600 font-bold">&times;</button>
            </div>

            <form onSubmit={handleReopen} className="space-y-3.5 text-xs">
              <p className="text-slate-600">
                Reopening restores the complaint to the administrator's actionable triage queue while preserving its complete historical audit trail.
              </p>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Mandatory Reopening Reason</label>
                <textarea
                  rows={3}
                  required
                  value={reopenReason}
                  onChange={(e) => setReopenReason(e.target.value)}
                  className="w-full glass-input px-3 py-2 rounded-xl focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowReopenModal(false)}
                  className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading || !reopenReason.trim()}
                  className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold"
                >
                  {actionLoading ? 'Reopening...' : 'Confirm Reopen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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
