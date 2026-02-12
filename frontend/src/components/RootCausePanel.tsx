import React, { useState, useEffect } from 'react';
import { getRootCauseAnalysis, type RootCauseAnalysis } from '@/services/api';

interface RootCausePanelProps {
  sessionId: string;
  isVisible: boolean;
  onClose: () => void;
}

export default function RootCausePanel({ sessionId, isVisible, onClose }: RootCausePanelProps) {
  const [rootCauseData, setRootCauseData] = useState<RootCauseAnalysis | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [position, setPosition] = useState({ x: 20, y: 100 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (isVisible && sessionId) {
      loadRootCauseData();
    }
  }, [sessionId, isVisible]);

  const loadRootCauseData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRootCauseAnalysis(sessionId);
      setRootCauseData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load root cause analysis');
      console.error('Root cause analysis error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('.root-cause-content')) return;
    setIsDragging(true);
    setDragOffset({
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    });
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (isDragging) {
      setPosition({
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset]);

  if (!isVisible) return null;

  return (
    <div
      className="fixed bg-white rounded-lg shadow-2xl z-50 border-2 border-gray-300"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: '680px',
        maxHeight: '85vh',
        cursor: isDragging ? 'grabbing' : 'grab',
      }}
      onMouseDown={handleMouseDown}
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white px-4 py-3 rounded-t-lg flex justify-between items-center">
        <h2 className="text-lg font-bold">🔍 Root Cause Analysis</h2>
        <button
          onClick={onClose}
          className="text-white hover:text-gray-200 text-xl font-bold leading-none"
        >
          ×
        </button>
      </div>

      {/* Content */}
      <div className="root-cause-content p-4 overflow-y-auto" style={{ maxHeight: 'calc(85vh - 60px)' }}>
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="text-gray-600">Loading root cause analysis...</div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {rootCauseData && (
          <div className="space-y-6">
            {/* Summary Statistics */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="text-xs text-blue-600 font-semibold mb-1">Total Segments</div>
                <div className="text-2xl font-bold text-blue-900">
                  {rootCauseData.summary.total_segments}
                </div>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                <div className="text-xs text-green-600 font-semibold mb-1">Avg Duration</div>
                <div className="text-2xl font-bold text-green-900">
                  {typeof rootCauseData.summary.avg_duration === 'number' && !isNaN(rootCauseData.summary.avg_duration) ? rootCauseData.summary.avg_duration.toFixed(1) : 'N/A'}s
                </div>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <div className="text-xs text-purple-600 font-semibold mb-1">Total Impact</div>
                <div className="text-2xl font-bold text-purple-900">
                  {Math.floor(rootCauseData.summary.total_impact_time / 60)}m {Math.floor(rootCauseData.summary.total_impact_time % 60)}s
                </div>
              </div>
            </div>

            {/* Cause Breakdown - Pie Chart */}
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-bold text-gray-700 mb-3">📊 Signal Loss by Cause</h3>
              <div className="flex items-center gap-6">
                {/* Simple Pie Chart using CSS */}
                <div className="relative w-40 h-40">
                  {rootCauseData.cause_breakdown.lte_only.count > 0 && (
                    <div
                      className="absolute w-full h-full rounded-full"
                      style={{
                        background: `conic-gradient(
                          #ef4444 0% ${rootCauseData.cause_breakdown.lte_only.percentage}%,
                          #f97316 ${rootCauseData.cause_breakdown.lte_only.percentage}% ${rootCauseData.cause_breakdown.lte_only.percentage + rootCauseData.cause_breakdown.starlink_only.percentage}%,
                          #dc2626 ${rootCauseData.cause_breakdown.lte_only.percentage + rootCauseData.cause_breakdown.starlink_only.percentage}% 100%
                        )`,
                      }}
                    />
                  )}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="bg-white rounded-full w-20 h-20 flex items-center justify-center">
                      <span className="text-xs font-bold text-gray-600">100%</span>
                    </div>
                  </div>
                </div>

                {/* Legend */}
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-red-500 rounded"></div>
                      <span className="text-xs text-gray-700">LTE Only</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-900">
                      {rootCauseData.cause_breakdown.lte_only.count} ({rootCauseData.cause_breakdown.lte_only.percentage}%)
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-orange-500 rounded"></div>
                      <span className="text-xs text-gray-700">Starlink Only</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-900">
                      {rootCauseData.cause_breakdown.starlink_only.count} ({rootCauseData.cause_breakdown.starlink_only.percentage}%)
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-red-600 rounded"></div>
                      <span className="text-xs text-gray-700">Both Systems</span>
                    </div>
                    <div className="text-xs font-semibold text-gray-900">
                      {rootCauseData.cause_breakdown.both.count} ({rootCauseData.cause_breakdown.both.percentage}%)
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Altitude Distribution - Bar Chart */}
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-bold text-gray-700 mb-3">🏔️ Signal Loss by Altitude</h3>
              <div className="space-y-2">
                {rootCauseData.altitude_distribution.map((item, index) => (
                  <div key={index}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-gray-600">{item.range}</span>
                      <span className="font-semibold text-gray-900">
                        {item.count} segments ({item.percentage}%) • Avg {typeof item.avg_duration === 'number' && !isNaN(item.avg_duration) ? item.avg_duration.toFixed(1) : 'N/A'}s
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className="bg-gradient-to-r from-blue-400 to-blue-600 h-3 rounded-full transition-all"
                        style={{ width: `${item.percentage}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Time Distribution - Bar Chart */}
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-bold text-gray-700 mb-3">⏱️ Signal Loss by Flight Period</h3>
              <div className="space-y-2">
                {rootCauseData.time_distribution.map((item, index) => (
                  <div key={index}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-gray-600">{item.period}</span>
                      <span className="font-semibold text-gray-900">
                        {item.count} segments ({item.percentage}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className="bg-gradient-to-r from-purple-400 to-purple-600 h-3 rounded-full transition-all"
                        style={{ width: `${item.percentage}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
