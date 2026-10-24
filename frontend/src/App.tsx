import React, { useEffect, useState } from 'react';
import { Navbar, NavTabType } from './components/Navbar';
import { CitizenComplaintPortal } from './components/CitizenComplaintPortal';
import { PriorityQueue } from './components/PriorityQueue';
import { IncidentDetail } from './components/IncidentDetail';
import { RiskCalculator } from './components/RiskCalculator';
import { ScenarioSimulator } from './components/ScenarioSimulator';
import { fetchPriorityQueue } from './api/client';
import { PriorityQueueItem } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTabType>('citizen');
  const [queue, setQueue] = useState<PriorityQueueItem[]>([]);
  const [loadingQueue, setLoadingQueue] = useState<boolean>(false);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>('INC-001');
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const loadQueue = async () => {
    setLoadingQueue(true);
    setIsRefreshing(true);
    try {
      const data = await fetchPriorityQueue(100);
      setQueue(data);
      if (data.length > 0 && !selectedIncidentId) {
        setSelectedIncidentId(data[0].incident_id);
      }
    } catch (err) {
      console.error('Failed to load priority queue:', err);
    } finally {
      setLoadingQueue(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const handleSelectIncident = (incidentId: string) => {
    setSelectedIncidentId(incidentId);
    setActiveTab('detail');
  };

  return (
    <div className="min-h-screen flex flex-col font-sans text-slate-800">
      
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRefresh={loadQueue}
        isRefreshing={isRefreshing}
        queueLength={queue.length}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-8 pb-12">
        {activeTab === 'citizen' && (
          <CitizenComplaintPortal
            onComplaintSubmitted={(newId) => {
              setSelectedIncidentId(newId);
              loadQueue();
            }}
            onViewInQueue={(newId) => {
              setSelectedIncidentId(newId);
              loadQueue();
              setActiveTab('queue');
            }}
          />
        )}

        {activeTab === 'queue' && (
          <PriorityQueue
            queue={queue}
            loading={loadingQueue}
            onSelectIncident={handleSelectIncident}
            onRefresh={loadQueue}
          />
        )}

        {activeTab === 'detail' && (
          <IncidentDetail
            incidentId={selectedIncidentId}
            onBack={() => setActiveTab('queue')}
            onRefresh={loadQueue}
          />
        )}

        {activeTab === 'calculator' && (
          <RiskCalculator
            onIncidentCreated={(newId) => {
              setSelectedIncidentId(newId);
              loadQueue();
            }}
          />
        )}

        {activeTab === 'simulation' && (
          <ScenarioSimulator
            onSelectIncident={handleSelectIncident}
            onRefreshQueue={loadQueue}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="w-full glass-card border-t border-white/60 py-4 px-4 text-center text-xs text-slate-500 font-medium">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>IMPACTX 2026 • Challenge 10: Your City, Your Services • <strong>Team OverClock</strong> (VIT-AP University)</span>
          <span className="text-[11px] font-mono text-slate-400">Status: Functional Prototype (Planning Stage)</span>
        </div>
      </footer>

    </div>
  );
};

export default App;
