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
  const [isOpen, setIsOpen] = useState(false);

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
      <div className="absolute bottom-4 left-4 z-20 bg-gray-900/90 text-white px-3 py-2 rounded-lg shadow-lg">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="absolute bottom-4 left-4 z-20 bg-red-900/90 text-white px-3 py-2 rounded-lg shadow-lg max-w-xs">
        <div className="flex items-start gap-2">
          <span>⚠️</span>
          <div>
            <div className="font-semibold text-sm">Error</div>
            <div className="text-xs mt-1">{error}</div>
            <button
              onClick={loadSessions}
              className="mt-2 px-2 py-1 bg-red-700 hover:bg-red-600 rounded text-xs transition"
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
      <div className="absolute bottom-4 left-4 z-20 bg-gray-900/90 text-white px-3 py-2 rounded-lg shadow-lg">
        <div className="flex items-center gap-2 text-sm">
          <span>📭</span>
          <span>No sessions</span>
        </div>
      </div>
    );
  }

  const selectedSession = sessions.find((s) => s.id === selectedSessionId);

  return (
    <div className="absolute bottom-4 left-4 z-20">
      {/* Compact dropdown button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="bg-gray-900/95 text-white px-3 py-2 rounded-lg shadow-lg hover:bg-gray-800/95 transition min-w-[280px]"
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex-1 text-left">
            <div className="font-medium text-sm truncate">
              {selectedSession?.name || 'Select Session'}
            </div>
            {selectedSession && (
              <div className="flex gap-2 text-xs text-gray-400 mt-1">
                <span>✈️ {selectedSession.file_count.flight_logs}</span>
                <span>📡 {selectedSession.file_count.lte_data}</span>
                <span>🛰️ {selectedSession.file_count.starlink_data}</span>
              </div>
            )}
          </div>
          <span className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <>
          {/* Backdrop to close dropdown */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown content */}
          <div className="absolute left-0 bottom-full mb-2 bg-gray-900/95 text-white rounded-lg shadow-xl overflow-hidden min-w-[280px] max-w-[320px] z-20">
            <div className="px-3 py-2 border-b border-gray-700">
              <h3 className="font-semibold text-xs text-gray-400">
                SESSIONS ({sessions.length})
              </h3>
            </div>

            <div className="max-h-[400px] overflow-y-auto">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => {
                    onSessionSelect(session.id);
                    setIsOpen(false);
                  }}
                  className={`
                    w-full text-left px-3 py-2 transition border-l-2 text-sm
                    ${
                      selectedSessionId === session.id
                        ? 'bg-blue-900/50 border-blue-500'
                        : 'border-transparent hover:bg-gray-800/50'
                    }
                  `}
                >
                  <div className="font-medium truncate">{session.name}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {new Date(session.created_at).toLocaleString('ko-KR', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                  <div className="flex gap-2 text-xs text-gray-500 mt-1">
                    <span>✈️ {session.file_count.flight_logs}</span>
                    <span>📡 {session.file_count.lte_data}</span>
                    <span>🛰️ {session.file_count.starlink_data}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
