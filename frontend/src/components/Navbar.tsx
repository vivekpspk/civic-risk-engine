import React, { useEffect, useState } from 'react';
import { ShieldAlert, Activity, Cpu, Layers, RefreshCw, Send } from 'lucide-react';
import { fetchHealth } from '../api/client';

export type NavTabType = 'citizen' | 'queue' | 'detail' | 'calculator' | 'simulation';

interface NavbarProps {
  activeTab: NavTabType;
  setActiveTab: (tab: NavTabType) => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  queueLength?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  onRefresh,
  isRefreshing,
  queueLength,
}) => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(() => setIsHealthy(true))
      .catch(() => setIsHealthy(false));
  }, []);

  return (
    <header className="sticky top-0 z-40 w-full glass-card border-b border-white/60 px-4 lg:px-8 py-3 mb-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand & Team Info */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-sky-400 via-indigo-500 to-rose-400 flex items-center justify-center text-white shadow-md shadow-sky-500/20">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-slate-800 tracking-tight text-base sm:text-lg">
                OVERCLOCK // <span className="text-sky-600 font-black">RISK ENGINE</span>
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-300/50">
                CHALLENGE 10
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              IMPACTX 2026 • Automatic Civic Incident Risk Triage
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center p-1 rounded-xl bg-slate-200/50 border border-white/50 text-xs sm:text-sm font-semibold text-slate-600 overflow-x-auto max-w-full">
          <button
            onClick={() => setActiveTab('citizen')}
            className={`px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 shrink-0 ${
              activeTab === 'citizen'
                ? 'bg-white text-sky-700 shadow-sm font-bold'
                : 'hover:text-slate-900 hover:bg-white/40'
            }`}
          >
            <Send className="h-4 w-4 text-sky-500" />
            <span>Report Issue</span>
          </button>

          <button
            onClick={() => setActiveTab('queue')}
            className={`px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 shrink-0 ${
              activeTab === 'queue'
                ? 'bg-white text-indigo-700 shadow-sm font-bold'
                : 'hover:text-slate-900 hover:bg-white/40'
            }`}
          >
            <Layers className="h-4 w-4 text-indigo-500" />
            <span>Priority Queue</span>
          </button>

          <button
            onClick={() => setActiveTab('detail')}
            className={`px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 shrink-0 ${
              activeTab === 'detail'
                ? 'bg-white text-emerald-700 shadow-sm font-bold'
                : 'hover:text-slate-900 hover:bg-white/40'
            }`}
          >
            <ShieldAlert className="h-4 w-4 text-emerald-500" />
            <span>Incident Audit</span>
          </button>

          <button
            onClick={() => setActiveTab('calculator')}
            className={`px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 shrink-0 ${
              activeTab === 'calculator'
                ? 'bg-white text-purple-700 shadow-sm font-bold'
                : 'hover:text-slate-900 hover:bg-white/40'
            }`}
          >
            <Activity className="h-4 w-4 text-purple-500" />
            <span>Formula Inspector</span>
          </button>

          <button
            onClick={() => setActiveTab('simulation')}
            className={`px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 shrink-0 ${
              activeTab === 'simulation'
                ? 'bg-white text-rose-700 shadow-sm font-bold'
                : 'hover:text-slate-900 hover:bg-white/40'
            }`}
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
            </span>
            <span>140-Report Simulator</span>
          </button>
        </nav>

        {/* Status Pills */}
        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="p-2 rounded-lg bg-white/70 hover:bg-white text-slate-600 border border-slate-200 shadow-sm hover:shadow transition disabled:opacity-50"
              title="Refresh Queue and Metrics"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin text-sky-600' : ''}`} />
            </button>
          )}

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/80 border border-slate-200 text-xs font-semibold text-slate-700 shadow-sm">
            <span
              className={`h-2 w-2 rounded-full ${
                isHealthy === true
                  ? 'bg-emerald-500 ring-2 ring-emerald-200'
                  : isHealthy === false
                  ? 'bg-rose-500 ring-2 ring-rose-200'
                  : 'bg-amber-400 animate-pulse'
              }`}
            />
            <span className="font-mono text-[11px]">API: {isHealthy ? 'ONLINE' : 'CONNECTING'}</span>
          </div>

          <div className="hidden sm:flex items-center px-2.5 py-1.5 rounded-lg bg-sky-50 border border-sky-200 text-[11px] font-mono text-sky-800 font-bold">
            Queue: {queueLength ?? 0}
          </div>
        </div>

      </div>
    </header>
  );
};
