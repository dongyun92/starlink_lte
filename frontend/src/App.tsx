import { useState, useEffect } from 'react';
import CesiumViewer from './components/CesiumViewer';
import { getFlightSessions } from './services/api';
import type { FlightSession } from './types/flight';

function App() {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<FlightSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await getFlightSessions();
      setSessions(data);
      // No auto-selection - user must manually select a session
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="w-full h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-lg">Loading sessions...</div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="w-full h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-lg">No sessions available</div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen bg-gray-900 relative">
      <CesiumViewer
        selectedSessionId={selectedSessionId}
        sessions={sessions}
        onSessionSelect={setSelectedSessionId}
      />
    </div>
  );
}

export default App;
