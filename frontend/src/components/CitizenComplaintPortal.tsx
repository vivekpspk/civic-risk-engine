import React, { useState } from 'react';
import {
  Send,
  MapPin,
  Camera,
  Shield,
  CheckCircle2,
  AlertTriangle,
  Clock,
  HelpCircle,
  Copy,
  Lock,
  Compass,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  User,
  Phone,
  Layers,
  Sparkles,
} from 'lucide-react';
import { submitCitizenComplaint } from '../api/client';
import { CitizenComplaintResponse } from '../types';

interface CitizenComplaintPortalProps {
  onComplaintSubmitted?: (complaintId: string) => void;
  onViewInQueue?: (complaintId: string) => void;
}

export const CitizenComplaintPortal: React.FC<CitizenComplaintPortalProps> = ({
  onComplaintSubmitted,
  onViewInQueue,
}) => {
  // 1. Citizen & Location details (Starting itself)
  const [reporterName, setReporterName] = useState<string>('');
  const [reporterPhone, setReporterPhone] = useState<string>('');
  const [address, setAddress] = useState<string>('');
  const [gpsCoords, setGpsCoords] = useState<{ lat: number; lon: number; acc: number } | null>(null);
  const [gpsLoading, setGpsLoading] = useState<boolean>(false);
  const [gpsError, setGpsError] = useState<string | null>(null);

  // 2. Complaint details
  const [description, setDescription] = useState<string>('');
  const [categoryHint, setCategoryHint] = useState<string>('');
  const [photoUploaded, setPhotoUploaded] = useState<boolean>(false);
  const [consentGiven, setConsentGiven] = useState<boolean>(true);

  // 3. Submission state & 3-line receipt
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<CitizenComplaintResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [showFullDetails, setShowFullDetails] = useState<boolean>(false);

  const requestGps = () => {
    setGpsLoading(true);
    setGpsError(null);
    if (!navigator.geolocation) {
      setGpsError('Geolocation is not supported by your browser. Please enter street name.');
      setGpsLoading(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsCoords({
          lat: parseFloat(pos.coords.latitude.toFixed(5)),
          lon: parseFloat(pos.coords.longitude.toFixed(5)),
          acc: Math.round(pos.coords.accuracy),
        });
        setGpsLoading(false);
      },
      () => {
        setGpsError('GPS permission declined or unavailable. You can enter the street or landmark below.');
        setGpsLoading(false);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  const usePresetLocation = (lat: number, lon: number, name: string) => {
    setGpsCoords({ lat, lon, acc: 8 });
    setAddress(name);
    setGpsError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim() || description.length < 5) {
      setError('Please provide a brief description of the civic issue.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        description: description.trim(),
        latitude: gpsCoords ? gpsCoords.lat : null,
        longitude: gpsCoords ? gpsCoords.lon : null,
        location_address: address.trim() || undefined,
        hazard_category_hint: categoryHint || undefined,
        evidence_photos: photoUploaded ? ['evidence_photo_clean_exif_stripped.jpg'] : [],
        reporter_name: reporterName.trim() || 'Citizen Reporter',
        reporter_phone: reporterPhone.trim() || undefined,
        consent_given: consentGiven,
      };

      const ack = await submitCitizenComplaint(payload);
      setResult(ack);
      setShowFullDetails(false);
      if (onComplaintSubmitted) {
        onComplaintSubmitted(ack.complaint_id);
      }
    } catch (err: any) {
      setError(err.message || 'Submission failed. Please check network connectivity.');
    } finally {
      setLoading(false);
    }
  };

  const copyId = () => {
    if (result) {
      navigator.clipboard.writeText(result.complaint_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const resetForm = () => {
    setDescription('');
    setCategoryHint('');
    setAddress('');
    setGpsCoords(null);
    setPhotoUploaded(false);
    setResult(null);
    setError(null);
    setShowFullDetails(false);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header Banner */}
      <div className="glass-card p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 border border-white/60 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-sky-100 text-sky-800 border border-sky-300">
              Civic Intake Portal
            </span>
            <span className="text-xs text-slate-400 font-semibold">• Automated Priority Triage</span>
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight mt-1">
            Report a Civic Hazard or Storm Issue
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Provide your location and report. The automated municipal engine assesses physical severity, checks sensitive site proximity, and dispatches the complaint directly into the priority response queue.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 bg-white/80 p-3 rounded-xl border border-slate-200 shrink-0">
          <Shield className="h-4 w-4 text-emerald-600 shrink-0" />
          <span>Confidential &amp; EXIF-Scrubbed</span>
        </div>
      </div>

      {result ? (
        /* ========================================================================= */
        /* COMPACT 3-LINE RECEIPT CARD (CLICK TO EXPAND ALL DETAILED PARAMETERS)      */
        /* ========================================================================= */
        <div className="glass-card p-6 sm:p-7 rounded-2xl border border-emerald-300/80 shadow-xl space-y-4">
          
          {/* Header pill */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
              <span className="text-xs font-bold text-emerald-800 uppercase tracking-wide">
                Complaint Received &amp; Assessed
              </span>
            </div>
            <span className="text-[11px] font-mono font-semibold text-slate-400">
              {new Date(result.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>

          {/* 3-LINE COMPACT SUMMARY */}
          <div className="p-4 rounded-xl bg-white/90 border border-slate-200/90 shadow-sm space-y-2.5">
            {/* LINE 1: ID, Priority, Status */}
            <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-500">Ticket ID:</span>
                <span className="text-base font-black font-mono text-slate-900">{result.complaint_id}</span>
                <button
                  onClick={copyId}
                  className="p-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 transition"
                  title="Copy Ticket ID"
                >
                  <Copy className="h-3.5 w-3.5" />
                </button>
                {copied && <span className="text-[11px] font-bold text-emerald-600">Copied!</span>}
              </div>

              <div className="flex items-center gap-2">
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${
                  result.priority_band === 'Critical'
                    ? 'bg-rose-100 text-rose-700 border border-rose-300'
                    : result.priority_band === 'High'
                    ? 'bg-amber-100 text-amber-800 border border-amber-300'
                    : 'bg-sky-100 text-sky-800 border border-sky-300'
                }`}>
                  {result.priority_band} PRIORITY
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  Dispatched to Queue
                </span>
              </div>
            </div>

            {/* LINE 2: Department, Response SLA, Ward */}
            <div className="text-xs font-medium text-slate-700 flex flex-wrap items-center gap-x-4 gap-y-1">
              <span><strong>Department:</strong> {result.assigned_department}</span>
              <span className="text-slate-300">•</span>
              <span><strong>Response SLA:</strong> <span className="font-mono font-bold text-indigo-700">{result.estimated_response_window}</span></span>
              <span className="text-slate-300">•</span>
              <span><strong>Ward:</strong> {result.assigned_ward}</span>
            </div>

            {/* LINE 3: Executive Assessment Summary */}
            <div className="text-xs text-slate-800 leading-relaxed font-semibold bg-slate-50 p-2.5 rounded-lg border border-slate-200/60">
              {result.ai_reasoning_summary || result.plain_language_explanation.split(' • ')[0]}
            </div>
          </div>

          {/* CLICK-TO-VIEW-ALL ACCORDION TOGGLE */}
          <button
            type="button"
            onClick={() => setShowFullDetails(!showFullDetails)}
            className="w-full py-2.5 px-4 rounded-xl bg-slate-100/90 hover:bg-slate-200/80 text-slate-700 font-bold text-xs flex items-center justify-between transition"
          >
            <span>{showFullDetails ? 'Hide Detailed Parameters & Breakdown' : 'Click to View Full Parameters & Technical Breakdown'}</span>
            {showFullDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {/* EXPANDABLE FULL PARAMETERS BREAKDOWN */}
          {showFullDetails && (
            <div className="p-4 rounded-xl bg-slate-50/90 border border-slate-200 space-y-4 animate-in fade-in duration-200">
              
              {result.safety_override_active && (
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-300 text-xs text-rose-800 font-medium flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
                  <span><strong>Safety Override Active:</strong> Life-safety criteria met; forced Critical triage review.</span>
                </div>
              )}

              {/* Grid of All Computed Risk Parameters */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Hazard Category</span>
                  <span className="font-bold text-slate-900 capitalize mt-0.5 block">{result.hazard_display_name}</span>
                </div>

                <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Calculated Risk</span>
                  <span className="font-bold font-mono text-slate-900 mt-0.5 block">{result.risk_score.toFixed(1)} / 100</span>
                </div>

                <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Evidence Tier</span>
                  <span className="font-bold text-slate-900 capitalize mt-0.5 block">{result.evidence_status}</span>
                </div>

                <div className="p-2.5 rounded-lg bg-white border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-400 uppercase block">Ward Dispute</span>
                  <span className="font-bold text-slate-900 mt-0.5 block">
                    {result.is_boundary_dispute ? 'Boundary Overlap (50m)' : 'Single Ward Clear'}
                  </span>
                </div>
              </div>

              {/* Full Multi-factor Explanation Log */}
              <div className="p-3 rounded-lg bg-white border border-slate-200 text-xs space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Complete Assessment Narrative &amp; Telemetry
                </span>
                <p className="text-slate-700 leading-relaxed font-medium">
                  {result.plain_language_explanation}
                </p>
              </div>

              {/* Action Ordered */}
              <div className="p-3 rounded-lg bg-sky-50 border border-sky-200 text-xs text-sky-950 font-medium space-y-0.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-sky-700 block">
                  Mandatory Field Action Ordered
                </span>
                <p className="font-semibold text-slate-900">{result.recommended_action}</p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-100">
            <button
              onClick={resetForm}
              className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs transition"
            >
              Report Another Issue
            </button>

            {onViewInQueue && (
              <button
                onClick={() => onViewInQueue(result.complaint_id)}
                className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-md shadow-indigo-500/20 transition"
              >
                <span>View in Priority Queue</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </div>

        </div>
      ) : (
        /* ========================================================================= */
        /* CITIZEN INTAKE FORM: ASKS NAME & LOCATION ACCESS RIGHT AT THE START        */
        /* ========================================================================= */
        <form onSubmit={handleSubmit} className="glass-card p-6 sm:p-7 rounded-2xl space-y-6 border border-white/60 shadow-lg">
          
          {/* STEP 1: UPFRONT CITIZEN & LOCATION ACCESS */}
          <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-sky-50/80 to-indigo-50/80 border border-sky-200/80 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase tracking-wider text-sky-900 flex items-center gap-1.5">
                <MapPin className="h-4 w-4 text-sky-600" />
                1. Your Information &amp; Location Access
              </span>
              <span className="text-[11px] text-slate-500 font-medium">Enables automated spatial assessment</span>
            </div>

            {/* Name Input */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1 flex items-center gap-1">
                  <User className="h-3.5 w-3.5 text-slate-500" />
                  Your Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={reporterName}
                  onChange={(e) => setReporterName(e.target.value)}
                  placeholder="Enter your name"
                  className="w-full glass-input px-3.5 py-2.5 text-xs rounded-xl focus:outline-none bg-white font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1 flex items-center gap-1">
                  <Phone className="h-3.5 w-3.5 text-slate-500" />
                  Phone Number (Confidential)
                </label>
                <input
                  type="text"
                  value={reporterPhone}
                  onChange={(e) => setReporterPhone(e.target.value)}
                  placeholder="e.g. +91-9876543210 (Optional)"
                  className="w-full glass-input px-3.5 py-2.5 text-xs rounded-xl focus:outline-none bg-white font-medium"
                />
              </div>
            </div>

            {/* Location Access Button & Presets */}
            <div className="pt-2 border-t border-sky-100 space-y-2.5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <label className="text-xs font-bold text-slate-700">
                  Location Access (GPS or Street Landmark) <span className="text-rose-500">*</span>
                </label>
                <button
                  type="button"
                  onClick={requestGps}
                  disabled={gpsLoading}
                  className="px-3.5 py-2 rounded-xl bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold shadow-md shadow-sky-500/20 flex items-center justify-center gap-2 transition"
                >
                  <Compass className={`h-4 w-4 ${gpsLoading ? 'animate-spin' : ''}`} />
                  <span>{gpsLoading ? 'Acquiring GPS...' : '📍 Share Current Location (GPS)'}</span>
                </button>
              </div>

              {/* GPS Confirmation Pill */}
              {gpsCoords && (
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-300 text-xs text-emerald-900 flex items-center justify-between font-medium">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                    <span>Location Acquired: <strong>{gpsCoords.lat}° N, {gpsCoords.lon}° E</strong> (±{gpsCoords.acc}m accuracy)</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setGpsCoords(null)}
                    className="text-emerald-700 font-bold hover:underline text-[11px]"
                  >
                    Change
                  </button>
                </div>
              )}

              {gpsError && (
                <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800">
                  {gpsError}
                </div>
              )}

              {/* Street Address / Landmark input */}
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Or type street name, colony, or landmark (e.g. Near St. Mary's School gate, Ward 07)"
                className="w-full glass-input px-3.5 py-2 text-xs rounded-xl focus:outline-none bg-white font-medium"
              />

              {/* Quick Preset Location Pills */}
              <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                <span className="text-slate-400 font-medium">Quick location presets:</span>
                <button
                  type="button"
                  onClick={() => usePresetLocation(16.5063, 80.6481, "St. Mary's Primary School, Ward 07")}
                  className="px-2 py-0.5 rounded-md bg-white hover:bg-sky-50 text-sky-800 border border-sky-200 font-medium"
                >
                  School Zone (Ward 07)
                </button>
                <button
                  type="button"
                  onClick={() => usePresetLocation(16.5050, 80.6450, "General Hospital Gate 2, Ward 08")}
                  className="px-2 py-0.5 rounded-md bg-white hover:bg-sky-50 text-sky-800 border border-sky-200 font-medium"
                >
                  Hospital Area (Ward 08)
                </button>
                <button
                  type="button"
                  onClick={() => usePresetLocation(16.5085, 80.6485, "Sector 4 / Sector 5 Border Road")}
                  className="px-2 py-0.5 rounded-md bg-white hover:bg-sky-50 text-sky-800 border border-sky-200 font-medium"
                >
                  Ward Boundary
                </button>
              </div>
            </div>
          </div>

          {/* STEP 2: WHAT HAPPENED? (COMMENT & DESCRIPTION) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700">
                2. Describe the Issue / Hazard <span className="text-rose-500">*</span>
              </label>
              <span className="text-[11px] text-slate-400 font-medium">Plain comments accepted</span>
            </div>

            {/* Quick 1-click Test Scenarios */}
            <div className="flex flex-wrap gap-1.5 text-xs">
              <button
                type="button"
                onClick={() => {
                  setDescription("Water is accumulating near a school, and an uncovered manhole is visible during heavy rain.");
                  usePresetLocation(16.5063, 80.6481, "St. Mary's Primary School, Ward 07");
                  setCategoryHint("open_manhole");
                }}
                className="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-800 font-medium border border-rose-200 transition"
              >
                🕳️ Open Manhole Near School
              </button>

              <button
                type="button"
                onClick={() => {
                  setDescription("Live electric wire has snapped and fallen into standing floodwater with active sparks.");
                  usePresetLocation(16.5050, 80.6450, "General Hospital Gate 2, Ward 08");
                  setCategoryHint("fallen_electric_pole_live_wire");
                }}
                className="px-2.5 py-1 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 font-medium border border-amber-200 transition"
              >
                ⚡ Live Wire in Floodwater
              </button>

              <button
                type="button"
                onClick={() => {
                  setDescription("Two families are trapped inside a vehicle with rising floodwater on low road.");
                  usePresetLocation(16.5030, 80.6410, "Railway Underbridge");
                  setCategoryHint("trapped_people_or_vehicles");
                }}
                className="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-800 font-medium border border-rose-200 transition"
              >
                🚗 People Trapped in Water
              </button>

              <button
                type="button"
                onClick={() => {
                  setDescription("Minor shallow water accumulating on side curb of residential street.");
                  usePresetLocation(16.5010, 80.6410, "Lane 4, Residential Area");
                  setCategoryHint("shallow_waterlogging");
                }}
                className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium border border-slate-200 transition"
              >
                💧 Routine Puddle
              </button>
            </div>

            <textarea
              required
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is happening? (e.g., 'An uncovered drain hole is submerged under murky rainwater near the school entrance, pedestrians cannot see it...')"
              className="w-full glass-input px-3.5 py-2.5 text-sm rounded-xl focus:outline-none placeholder:text-slate-400 font-medium leading-relaxed"
            />
          </div>

          {/* Optional Category Suggestion & Photo Evidence */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Category (Optional Hint)
              </label>
              <select
                value={categoryHint}
                onChange={(e) => setCategoryHint(e.target.value)}
                className="w-full glass-input px-3 py-2 text-xs rounded-xl focus:outline-none bg-white font-medium"
              >
                <option value="">-- Auto-Detect from Description --</option>
                <option value="open_manhole">Open / Missing Manhole Lid</option>
                <option value="fallen_electric_pole_live_wire">Fallen Electric Wire in Water</option>
                <option value="flooded_road_deep">Flooded Road (&gt;2.5 ft Deep)</option>
                <option value="trapped_people_or_vehicles">Trapped People or Car</option>
                <option value="waterlog_sensitive_site">Waterlogging Near School/Hospital</option>
                <option value="collapsed_road_sinkhole">Collapsed Road / Submerged Sinkhole</option>
                <option value="shallow_waterlogging">Shallow Waterlogging (&lt;1 ft)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1 flex items-center gap-1.5">
                <Camera className="h-3.5 w-3.5 text-indigo-500" />
                Attach Photo Evidence (Optional)
              </label>
              <button
                type="button"
                onClick={() => setPhotoUploaded(!photoUploaded)}
                className={`w-full py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-between transition ${
                  photoUploaded
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <span>{photoUploaded ? '✓ Photo Attached (EXIF Scrubbed)' : '+ Attach Photo'}</span>
                <span className="text-[10px] text-slate-400">EXIF Stripped</span>
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
              {error}
            </div>
          )}

          {/* STEP 3: SUBMIT */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 px-4 rounded-xl font-bold text-white bg-gradient-to-r from-sky-500 via-indigo-600 to-rose-500 hover:opacity-95 shadow-lg shadow-sky-500/25 active:scale-[0.99] transition flex items-center justify-center gap-2 text-sm"
          >
            {loading ? (
              <span>Analyzing Incident &amp; Sending to Priority Queue...</span>
            ) : (
              <>
                <Send className="h-4 w-4" />
                <span>Submit Report &amp; Send to Priority Queue</span>
              </>
            )}
          </button>

        </form>
      )}
    </div>
  );
};
