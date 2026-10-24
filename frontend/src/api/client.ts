/**
 * REST API client for the Explainable Civic Risk Scoring & Priority Engine.
 */

import {
  RiskAssessmentResponse,
  PriorityQueueItem,
  IncidentDetailResponse,
  SimulationResult,
  RiskModelConfig
} from '../types';

const API_BASE = (import.meta as any).env?.VITE_API_URL || '';

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function createIncident(data: any): Promise<RiskAssessmentResponse> {
  const res = await fetch(`${API_BASE}/incidents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to create incident');
  }
  return res.json();
}

export async function assessIncident(incidentId: string, data: any): Promise<RiskAssessmentResponse> {
  const res = await fetch(`${API_BASE}/incidents/${encodeURIComponent(incidentId)}/assess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to assess incident');
  }
  return res.json();
}

export async function fetchIncidentRisk(incidentId: string): Promise<RiskAssessmentResponse> {
  const res = await fetch(`${API_BASE}/incidents/${encodeURIComponent(incidentId)}/risk`);
  if (!res.ok) throw new Error(`Failed to fetch incident risk: ${res.statusText}`);
  return res.json();
}

export async function fetchIncidentDetail(incidentId: string): Promise<IncidentDetailResponse> {
  const res = await fetch(`${API_BASE}/incidents/${encodeURIComponent(incidentId)}`);
  if (!res.ok) throw new Error(`Failed to fetch incident detail: ${res.statusText}`);
  return res.json();
}

export async function fetchPriorityQueue(limit: number = 100): Promise<PriorityQueueItem[]> {
  const res = await fetch(`${API_BASE}/priority-queue?limit=${limit}`);
  if (!res.ok) throw new Error(`Failed to fetch priority queue: ${res.statusText}`);
  return res.json();
}

export async function applyManualOverride(
  incidentId: string,
  data: { authorized_by: string; role: string; reason: string; target_severity: string }
): Promise<RiskAssessmentResponse> {
  const res = await fetch(`${API_BASE}/incidents/${encodeURIComponent(incidentId)}/override`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to record override');
  }
  return res.json();
}

export async function fetchRiskModelConfig(): Promise<RiskModelConfig> {
  const res = await fetch(`${API_BASE}/config/risk-model`);
  if (!res.ok) throw new Error(`Failed to fetch risk configuration: ${res.statusText}`);
  return res.json();
}

export async function updateRiskModelConfig(data: any): Promise<RiskModelConfig> {
  const res = await fetch(`${API_BASE}/config/risk-model`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to update configuration');
  }
  return res.json();
}

export async function runSimulation(): Promise<SimulationResult> {
  const res = await fetch(`${API_BASE}/simulation/run-140-reports`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to run 140-report simulation: ${res.statusText}`);
  return res.json();
}

export async function fetchSimulationStatus(): Promise<SimulationResult> {
  const res = await fetch(`${API_BASE}/simulation/status`);
  if (!res.ok) throw new Error(`Failed to fetch simulation status: ${res.statusText}`);
  return res.json();
}

// ==========================================
// CITIZEN INTAKE & ADMIN DASHBOARD ENDPOINTS
// ==========================================

export async function submitCitizenComplaint(data: any): Promise<any> {
  const res = await fetch(`${API_BASE}/api/complaints`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to submit citizen complaint');
  }
  return res.json();
}

export async function fetchCitizenComplaint(complaintId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/complaints/${encodeURIComponent(complaintId)}`);
  if (!res.ok) throw new Error(`Failed to fetch complaint: ${res.statusText}`);
  return res.json();
}

export async function fetchAdminDashboard(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/admin/dashboard`);
  if (!res.ok) throw new Error(`Failed to fetch dashboard metrics: ${res.statusText}`);
  return res.json();
}

export async function updateComplaintStatus(complaintId: string, data: { status: string; officer_name: string; notes?: string }): Promise<any> {
  const res = await fetch(`${API_BASE}/api/admin/complaints/${encodeURIComponent(complaintId)}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to update complaint status');
  }
  return res.json();
}

export async function updateComplaintAssignment(complaintId: string, data: { assigned_department: string; assigned_ward?: string; authorized_by: string; reason: string }): Promise<any> {
  const res = await fetch(`${API_BASE}/api/admin/complaints/${encodeURIComponent(complaintId)}/assignment`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to reassign complaint');
  }
  return res.json();
}

export async function analyzeTextWithAI(data: { description: string; location?: string; category_hint?: string }): Promise<any> {
  const res = await fetch(`${API_BASE}/api/ai/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to complete automated text analysis');
  }
  return res.json();
}

export async function fetchAIStatus(): Promise<any> {
  const res = await fetch(`${API_BASE}/api/ai/status`);
  if (!res.ok) throw new Error(`Failed to fetch AI status: ${res.statusText}`);
  return res.json();
}
