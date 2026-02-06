import { useEffect, useState } from 'react';
import { getFlightSessions } from '@/services/api';
import type { FlightSession } from '@/types/flight';

interface SessionSelectorProps {
  onSessionSelect: (sessionId: string) => void;
  selectedSessionId: string | null;
}

/**
 * Session selector component for choosing flight sessions
 */
export default function SessionSelector({ onSessionSelect, selectedSessionId }: SessionSelectorProps) {
  const [sessions, setSessions] = useState<FlightSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getFlightSessions();
      setSessions(data);

      // Auto-select first session if none selected
      if (data.length > 0 && !selectedSessionId) {
        onSessionSelect(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
      console.error('Failed to load sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="absolute top-4 left-4 z-10 bg-gray-900/90 text-white px-4 py-2 rounded-lg shadow-lg">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          <span>Loading sessions...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="absolute top-4 left-4 z-10 bg-red-900/90 text-white px-4 py-3 rounded-lg shadow-lg max-w-md">
        <div className="flex items-start gap-2">
          <span className="text-xl">⚠️</span>
          <div>
            <div className="font-semibold">Error loading sessions</div>
            <div className="text-sm mt-1">{error}</div>
            <button
              onClick={loadSessions}
              className="mt-2 px-3 py-1 bg-red-700 hover:bg-red-600 rounded text-sm transition"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="absolute top-4 left-4 z-10 bg-gray-900/90 text-white px-4 py-3 rounded-lg shadow-lg">
        <div className="flex items-center gap-2">
          <span>📭</span>
          <span>No flight sessions available</span>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute top-4 left-4 z-10 bg-gray-900/95 text-white rounded-lg shadow-lg overflow-hidden min-w-[320px]">
      <div className="px-4 py-3 border-b border-gray-700">
        <h3 className="font-semibold text-sm">Flight Sessions ({sessions.length})</h3>
      </div>

      <div className="max-h-[400px] overflow-y-auto">
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onSessionSelect(session.id)}
            className={`
              w-full text-left px-4 py-3 transition border-l-4
              ${
                selectedSessionId === session.id
                  ? 'bg-blue-900/50 border-blue-500'
                  : 'bg-transparent border-transparent hover:bg-gray-800/50'
              }
            `}
          >
            <div className="font-medium text-sm">{session.name}</div>
            <div className="text-xs text-gray-400 mt-1">
              {new Date(session.created_at).toLocaleString()}
            </div>
            <div className="flex gap-3 text-xs text-gray-500 mt-2">
              <span>✈️ {session.file_count.flight_logs} logs</span>
              <span>📡 {session.file_count.lte_data} LTE</span>
              <span>🛰️ {session.file_count.starlink_data} Starlink</span>
            </div>
          </button>
        ))}
      </div>

      <div className="px-4 py-2 bg-gray-800/50 border-t border-gray-700 text-xs text-gray-400">
        Select a session to visualize
      </div>
    </div>
  );
}
