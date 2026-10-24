import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Flame,
  Clock,
  CloudRain,
  MapPin,
  Users,
  Repeat,
  ShieldCheck,
  CheckCircle2,
  Info,
  Sparkles,
  ArrowRight,
  Activity,
  Play
} from 'lucide-react';
import { assessIncident, createIncident } from '../api/client';
import { FactorInputs, RiskAssessmentResponse } from '../types';

interface RiskCalculatorProps {
  onIncidentCreated?: (incidentId: string) => void;
}

export const RiskCalculator: React.FC<RiskCalculatorProps> = ({ onIncidentCreated }) => {
  const [incidentId, setIncidentId] = useState<string>('INC-001');
  const [hazardType, setHazardType] = useState<string>('open_manhole');
  const [evidenceStatus, setEvidenceStatus] = useState<string>('corroborated');
  const [ward, setWard] = useState<string>('Ward 07');

  // Exact Section 8 sample factors as initial state:
  const [factors, setFactors] = useState<FactorInputs>({
    hazard_severity: 1.0,
    sensitive_site_proximity: 0.9,
    population_exposed: 0.7,
    weather_risk: 0.8,
    time_outstanding: 0.2,
    recurrence: 0.3,
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<RiskAssessmentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSliderChange = (key: keyof FactorInputs, val: number) => {
    setFactors((prev) => ({
      ...prev,
      [key]: Math.round(val * 100) / 100,
    }));
  };

  const handleCalculate = async () => {
    setLoading(true);
    setError(null);
    try {
      // Create or assess incident
      const payload = {
        incident_id: incidentId.trim() || `INC-${Date.now().toString().slice(-4)}`,
        hazard_type: hazardType,
        ward: ward,
        evidence_status: evidenceStatus,
        factors: factors,
        sla_deadline: new Date(Date.now() + 2 * 3600 * 1000).toISOString(),
      };

      let assessment: RiskAssessmentResponse;
      try {
        assessment = await createIncident(payload);
      } catch (err: any) {
        if (err.message && (err.message.includes('already exists') || err.message.includes('400'))) {
          assessment = await assessIncident(payload.incident_id, {
            factors: factors,
            hazard_type: hazardType,
            evidence_status: evidenceStatus,
          });
        } else {
          throw err;
        }
      }

      setResult(assessment);
      if (onIncidentCreated) {
        onIncidentCreated(payload.incident_id);
      }
    } catch (err: any) {
      setError(err.message || 'Error computing risk assessment.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleCalculate();
  }, []);

  // Quick Presets
  const applyPreset = (presetName: string) => {
    if (presetName === 'sample') {
      setIncidentId('INC-001');
      setHazardType('open_manhole');
      setEvidenceStatus('corroborated');
      setFactors({
        hazard_severity: 1.0,
        sensitive_site_proximity: 0.9,
        population_exposed: 0.7,
        weather_risk: 0.8,
        time_outstanding: 0.2,
        recurrence: 0.3,
      });
    } else if (presetName === 'school_manhole') {
      setIncidentId('INC-SCH-104');
      setHazardType('open_manhole');
      setEvidenceStatus('officially_verified');
      setFactors({
        hazard_severity: 1.0,
        sensitive_site_proximity: 0.95,
        population_exposed: 0.85,
        weather_risk: 0.90,
        time_outstanding: 0.35,
        recurrence: 0.80,
      });
    } else if (presetName === 'pothole') {
      setIncidentId('INC-POT-201');
      setHazardType('pothole');
      setEvidenceStatus('reported');
      setFactors({
        hazard_severity: 0.30,
        sensitive_site_proximity: 0.10,
        population_exposed: 0.25,
        weather_risk: 0.40,
        time_outstanding: 0.35,
        recurrence: 0.40,
      });
    } else if (presetName === 'electrical_flood') {
      setIncidentId('INC-ELEC-909');
      setHazardType('exposed_electrical_hazard');
      setEvidenceStatus('corroborated');
      setFactors({
        hazard_severity: 1.0,
        sensitive_site_proximity: 0.85,
        population_exposed: 0.75,
        weather_risk: 0.90,
        time_outstanding: 0.20,
        recurrence: 0.20,
      });
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Title & Presets Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card p-5 rounded-2xl">
        <div>
          <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-sky-500" />
            Explainable Civic Risk Calculator
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Deterministic weighted risk evaluation: <code className="bg-slate-100 px-1 py-0.5 rounded text-sky-700 font-semibold">100 × (0.25H + 0.20S + 0.20P + 0.15W + 0.10T + 0.10C)</code>
          </p>
        </div>

        {/* Quick Presets */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <span className="font-semibold text-slate-500 mr-1">Presets:</span>
          <button
            onClick={() => applyPreset('sample')}
            className="px-2.5 py-1 rounded-lg bg-sky-100/80 hover:bg-sky-200 text-sky-800 font-semibold transition"
          >
            Exact Sample (74.0)
          </button>
          <button
            onClick={() => applyPreset('school_manhole')}
            className="px-2.5 py-1 rounded-lg bg-rose-100/80 hover:bg-rose-200 text-rose-800 font-semibold transition"
          >
            School Hazard (Critical)
          </button>
          <button
            onClick={() => applyPreset('electrical_flood')}
            className="px-2.5 py-1 rounded-lg bg-amber-100/80 hover:bg-amber-200 text-amber-800 font-semibold transition"
          >
            Live Wire In Rain
          </button>
          <button
            onClick={() => applyPreset('pothole')}
            className="px-2.5 py-1 rounded-lg bg-slate-200/80 hover:bg-slate-300 text-slate-700 font-semibold transition"
          >
            Routine Pothole
          </button>
        </div>
      </div>

      {/* Main Grid: Inputs Left, Live Results Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Left Column: Form & Sliders (7 cols) */}
        <div className="lg:col-span-7 space-y-5">
          <div className="glass-card p-6 rounded-2xl space-y-5">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 flex items-center gap-2">
              <Info className="h-4 w-4 text-sky-500" />
              Incident Metadata & Categorization
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Incident ID</label>
                <input
                  type="text"
                  value={incidentId}
                  onChange={(e) => setIncidentId(e.target.value)}
                  className="w-full glass-input px-3 py-2 text-sm font-mono rounded-xl focus:outline-none"
                  placeholder="INC-001"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Ward Location</label>
                <input
                  type="text"
                  value={ward}
                  onChange={(e) => setWard(e.target.value)}
                  className="w-full glass-input px-3 py-2 text-sm rounded-xl focus:outline-none"
                  placeholder="Ward 07"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Hazard Category</label>
                <select
                  value={hazardType}
                  onChange={(e) => setHazardType(e.target.value)}
                  className="w-full glass-input px-3 py-2 text-sm rounded-xl focus:outline-none bg-white font-medium"
                >
                  <option value="open_manhole">Open Manhole Chamber (Catastrophic)</option>
                  <option value="exposed_electrical_hazard">Exposed Live Electrical Wire</option>
                  <option value="blocked_hospital_access">Blocked Hospital Ambulance Route</option>
                  <option value="severe_flooding">Severe Flooding (&gt;2.5 ft)</option>
                  <option value="shallow_waterlogging">Shallow Waterlogging (&lt;1 ft)</option>
                  <option value="pothole">Pothole in Roadway</option>
                  <option value="tree_debris_blocking_road">Fallen Tree / Debris</option>
                  <option value="street_light_outage">Street Light Cluster Outage</option>
                  <option value="garbage_dump">Overfilled Garbage Dump</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Evidence Status</label>
                <select
                  value={evidenceStatus}
                  onChange={(e) => setEvidenceStatus(e.target.value)}
                  className="w-full glass-input px-3 py-2 text-sm rounded-xl focus:outline-none bg-white font-medium"
                >
                  <option value="reported">Reported (Single Unverified Source)</option>
                  <option value="corroborated">Corroborated (Multiple Independent Citations)</option>
                  <option value="officially_verified">Officially Verified (Field Staff Check-in)</option>
                </select>
              </div>
            </div>

            <hr className="border-slate-200/60" />

            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 flex items-center justify-between">
              <span>6-Factor Normalized Inputs [0.0 - 1.0]</span>
              <span className="text-xs text-sky-600 font-mono font-bold">Sum of Weights = 100%</span>
            </h3>

            {/* 6 Sliders */}
            <div className="space-y-4">
              
              {/* Factor 1: H */}
              <div className="p-3 rounded-xl bg-slate-50/70 border border-slate-200/50 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700 flex items-center gap-1.5">
                    <Flame className="h-3.5 w-3.5 text-rose-500" />
                    Hazard Severity (H) — Weight: 25%
                  </span>
                  <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                    {factors.hazard_severity.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={factors.hazard_severity}
                  onChange={(e) => handleSliderChange('hazard_severity', parseFloat(e.target.value))}
                  className="w-full accent-rose-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0.0: Cosmetic</span>
                  <span>0.5: Moderate</span>
                  <span>1.0: Lethal Fall / Electrocution</span>
                </div>
              </div>

              {/* Factor 2: S */}
              <div className="p-3 rounded-xl bg-slate-50/70 border border-slate-200/50 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700 flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5 text-sky-500" />
                    Sensitive-Site Proximity (S) — Weight: 20%
                  </span>
                  <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                    {factors.sensitive_site_proximity.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={factors.sensitive_site_proximity}
                  onChange={(e) => handleSliderChange('sensitive_site_proximity', parseFloat(e.target.value))}
                  className="w-full accent-sky-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0.0: &gt;500m (Isolated)</span>
                  <span>0.5: ~250m</span>
                  <span>1.0: &lt;50m (School / Hospital Gate)</span>
                </div>
              </div>

              {/* Factor 3: P */}
              <div className="p-3 rounded-xl bg-slate-50/70 border border-slate-200/50 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700 flex items-center gap-1.5">
                    <Users className="h-3.5 w-3.5 text-indigo-500" />
                    Population Exposed (P) — Weight: 20%
                  </span>
                  <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                    {factors.population_exposed.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={factors.population_exposed}
                  onChange={(e) => handleSliderChange('population_exposed', parseFloat(e.target.value))}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0.0: Confirmed Zero</span>
                  <span>0.5: Moderate Traffic</span>
                  <span>1.0: Heavy Pedestrian / Commuter Surge</span>
                </div>
              </div>

              {/* Factor 4: W */}
              <div className="p-3 rounded-xl bg-slate-50/70 border border-slate-200/50 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700 flex items-center gap-1.5">
                    <CloudRain className="h-3.5 w-3.5 text-cyan-500" />
                    Weather / Flood Risk (W) — Weight: 15%
                  </span>
                  <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                    {factors.weather_risk.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={factors.weather_risk}
                  onChange={(e) => handleSliderChange('weather_risk', parseFloat(e.target.value))}
                  className="w-full accent-cyan-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0.0: Dry / Clear</span>
                  <span>0.5: 50mm/hr Rain</span>
                  <span>1.0: Severe Cloudburst (&gt;100mm/hr)</span>
                </div>
              </div>

              {/* Factor 5: T */}
              <div className="p-3 rounded-xl bg-slate-50/70 border border-slate-200/50 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700 flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5 text-amber-500" />
                    Time Outstanding (T) — Weight: 10%
                  </span>
                  <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                    {factors.time_outstanding.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={factors.time_outstanding}
                  onChange={(e) => handleSliderChange('time_outstanding', parseFloat(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0.0: Just Submitted</span>
                  <span>0.5: 12 Hours Active</span>
                  <span>1.0: &gt;= 24 Hours Unresolved (Capped)</span>
                </div>
              </div>

              {/* Factor 6: C */}
              <div className="p-3 rounded-xl bg-slate-50/70 border border-slate-200/50 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-bold text-slate-700 flex items-center gap-1.5">
                    <Repeat className="h-3.5 w-3.5 text-violet-500" />
                    Historical Recurrence (C) — Weight: 10%
                  </span>
                  <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                    {factors.recurrence.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={factors.recurrence}
                  onChange={(e) => handleSliderChange('recurrence', parseFloat(e.target.value))}
                  className="w-full accent-violet-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>0.0: First Occurrence</span>
                  <span>0.4: 2 Prior Incidents</span>
                  <span>1.0: 5+ Repeat Failures (Chronic Asset)</span>
                </div>
              </div>

            </div>

            {/* Calculate Button */}
            <button
              onClick={handleCalculate}
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl font-bold text-white bg-gradient-to-r from-sky-500 via-indigo-600 to-rose-500 hover:opacity-95 shadow-lg shadow-sky-500/25 active:scale-[0.99] transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <span>Evaluating Risk Model...</span>
              ) : (
                <>
                  <span>Run Deterministic Assessment</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>

            {error && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Live Assessment Output (5 cols) */}
        <div className="lg:col-span-5 space-y-5">
          {result ? (
            <div className="space-y-5">
              
              {/* Score Display Card */}
              <div className="glass-card p-6 rounded-2xl relative overflow-hidden">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Calculated Risk Score
                  </span>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${
                    result.priority_band === 'Critical'
                      ? 'bg-rose-100 text-rose-700 border border-rose-300'
                      : result.priority_band === 'High'
                      ? 'bg-amber-100 text-amber-800 border border-amber-300'
                      : result.priority_band === 'Medium'
                      ? 'bg-sky-100 text-sky-800 border border-sky-300'
                      : 'bg-slate-100 text-slate-700 border border-slate-300'
                  }`}>
                    {result.priority_band} PRIORITY
                  </span>
                </div>

                <div className="mt-4 flex items-baseline gap-2">
                  <span className="text-5xl font-black text-slate-800 tracking-tight font-mono">
                    {result.risk_score.toFixed(1)}
                  </span>
                  <span className="text-slate-400 font-semibold text-lg">/ 100</span>
                </div>

                <p className="mt-3 text-xs text-slate-500 font-medium border-t border-slate-100 pt-3 italic">
                  *This score reflects comparative operational urgency, not the physical probability of an accident.
                </p>
              </div>

              {/* Safety Override Card */}
              {result.safety_override.active && (
                <div className="p-4 rounded-2xl bg-rose-50/90 border-2 border-rose-400 shadow-md space-y-2">
                  <div className="flex items-center gap-2 text-rose-800 font-bold text-sm">
                    <AlertTriangle className="h-5 w-5 text-rose-600 animate-pulse" />
                    EMERGENCY SAFETY OVERRIDE ACTIVE
                  </div>
                  <p className="text-xs text-rose-700">
                    {result.safety_override.summary}
                  </p>
                  {result.safety_override.triggered_rules.map((rule, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-white/80 border border-rose-200 text-xs text-slate-700">
                      <div className="font-bold text-rose-800">{rule.rule_id}: {rule.rule_name}</div>
                      <div className="text-[11px] text-slate-600 mt-0.5">{rule.explanation}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Factor Contribution Breakdown */}
              <div className="glass-card p-5 rounded-2xl space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Factor Contributions (Points Added)
                </h4>

                <div className="space-y-2 text-xs">
                  {Object.entries(result.factor_contributions).map(([key, pts]) => {
                    const label = key.replace('_', ' ').toUpperCase();
                    return (
                      <div key={key} className="space-y-1">
                        <div className="flex justify-between font-semibold">
                          <span className="text-slate-600 capitalize">{label}</span>
                          <span className="font-mono text-slate-900 font-bold">+{pts.toFixed(1)} pts</span>
                        </div>
                        <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-sky-400 to-indigo-500 rounded-full"
                            style={{ width: `${Math.min(100, (pts / 25) * 100)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Recommended Action & SLA */}
              <div className="glass-card p-5 rounded-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Recommended Response
                  </h4>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    result.sla_status === 'breached'
                      ? 'bg-rose-100 text-rose-700'
                      : 'bg-emerald-100 text-emerald-800'
                  }`}>
                    {result.sla_status.toUpperCase()}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800">
                  {result.recommended_action}
                </div>

                {result.uncertainty_flags.length > 0 && (
                  <div className="space-y-1.5 pt-2">
                    <span className="text-[11px] font-bold text-amber-800 block">
                      Uncertainty &amp; Missing Data Warnings:
                    </span>
                    {result.uncertainty_flags.map((w, idx) => (
                      <div key={idx} className="p-2 rounded-lg bg-amber-50/80 border border-amber-200 text-[11px] text-amber-900">
                        • {w}
                      </div>
                    ))}
                  </div>
                )}
              </div>

            </div>
          ) : (
            /* Empty State */
            <div className="glass-card p-8 rounded-2xl text-center space-y-3 text-slate-400 h-full flex flex-col items-center justify-center">
              <Activity className="h-12 w-12 text-slate-300 stroke-[1.5]" />
              <h4 className="font-bold text-slate-600">No Assessment Calculated Yet</h4>
              <p className="text-xs max-w-xs">
                Adjust the 6 factor sliders on the left or select a preset, then click <strong>Run Deterministic Assessment</strong>.
              </p>
              <button
                onClick={handleCalculate}
                className="mt-3 px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-600 text-white text-xs font-bold shadow-md shadow-sky-500/20 transition flex items-center gap-1.5"
              >
                <Play className="h-3.5 w-3.5 fill-white" />
                <span>Evaluate INC-001 Sample Now</span>
              </button>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
