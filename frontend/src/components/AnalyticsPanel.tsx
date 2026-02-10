import React, { useState, useEffect, useRef } from 'react';
import { getSessionCharts, retryAnalysis, getSessionStatus, type ChartInfo } from '@/services/api';

interface AnalyticsPanelProps {
  sessionId: string | null;
  flightId: number | null;
  metric?: string;
}

interface Position {
  x: number;
  y: number;
}

interface ChartCategory {
  title: string;
  icon: string;
  charts: ChartInfo[];
}

export const AnalyticsPanel: React.FC<AnalyticsPanelProps> = ({
  sessionId,
  flightId,
  metric
}) => {
  const [charts, setCharts] = useState<ChartInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['basic']));
  const [selectedChart, setSelectedChart] = useState<ChartInfo | null>(null);
  const [isReanalyzing, setIsReanalyzing] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);

  // Draggable state
  const [position, setPosition] = useState<Position>({ x: window.innerWidth - 420, y: 16 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState<Position>({ x: 0, y: 0 });
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) return;

    const loadCharts = async () => {
      setLoading(true);
      setError(null);
      try {
        const chartList = await getSessionCharts(sessionId);
        setCharts(chartList);
        console.log(`📊 Loaded ${chartList.length} charts for session ${sessionId}`);
      } catch (err) {
        console.error('Failed to load charts:', err);
        setError('Failed to load analysis charts');
      } finally {
        setLoading(false);
      }
    };

    loadCharts();
  }, [sessionId]);

  const categorizeCharts = (): ChartCategory[] => {
    const categories: ChartCategory[] = [
      {
        title: 'Basic Analysis',
        icon: '',
        charts: charts.filter(c =>
          ['statistics_summary', 'quality_over_time', 'correlation_matrix',
           'correlation_heatmap', 'comprehensive_correlations', 'altitude_quality',
           'quality_distribution'].includes(c.name)
        )
      },
      {
        title: 'Starlink Satellite',
        icon: '',
        charts: charts.filter(c =>
          ['satellite_position_polar', 'satellite_quality_correlation'].includes(c.name)
        )
      },
      {
        title: 'Deep Analysis',
        icon: '',
        charts: charts.filter(c =>
          ['starlink_altitude_analysis', 'starlink_speed_analysis',
           'starlink_distance_analysis', 'starlink_throughput_timeseries',
           'starlink_3d_altitude_speed'].includes(c.name)
        )
      },
      {
        title: 'Advanced Charts',
        icon: '',
        charts: charts.filter(c =>
          c.name.startsWith('chart')
        )
      }
    ];

    return categories.filter(cat => cat.charts.length > 0);
  };

  const toggleCategory = (categoryTitle: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(categoryTitle)) {
        newSet.delete(categoryTitle);
      } else {
        newSet.add(categoryTitle);
      }
      return newSet;
    });
  };

  const handleReanalyze = async () => {
    if (!sessionId || isReanalyzing) return;

    setIsReanalyzing(true);
    setError(null);

    try {
      await retryAnalysis(sessionId);
      alert('재분석이 시작되었습니다. 완료되면 차트가 자동으로 업데이트됩니다.');

      // Poll for updates every 3 seconds
      const pollInterval = setInterval(async () => {
        try {
          // Check session status first
          const status = await getSessionStatus(sessionId);

          if (status.status === 'completed') {
            // Analysis complete - fetch charts
            const chartList = await getSessionCharts(sessionId);
            setCharts(chartList);
            clearInterval(pollInterval);
            setIsReanalyzing(false);
            alert('재분석이 완료되었습니다! 차트가 업데이트되었습니다.');
          } else if (status.status === 'failed') {
            // Analysis failed
            clearInterval(pollInterval);
            setIsReanalyzing(false);
            setError('재분석에 실패했습니다');
          }
          // Otherwise keep polling (processing state)
        } catch (err) {
          // Status check failed, continue polling
          console.log('Polling status check:', err);
        }
      }, 3000);

      // Stop polling after 2 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        setIsReanalyzing(false);
      }, 120000);
    } catch (err) {
      console.error('Failed to trigger re-analysis:', err);
      setError('재분석 시작에 실패했습니다');
      setIsReanalyzing(false);
    }
  };

  const categories = categorizeCharts();

  // Drag handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (panelRef.current) {
      const rect = panelRef.current.getBoundingClientRect();
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
      });
      setIsDragging(true);
    }
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        setPosition({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffset]);

  return (
    <>
      <div
        ref={panelRef}
        className="absolute bg-white rounded-lg shadow-xl z-[100] w-[450px] max-h-[calc(100vh-120px)] flex flex-col"
        style={{
          left: `${position.x}px`,
          top: `${position.y}px`,
          cursor: isDragging ? 'grabbing' : 'default'
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between p-3 border-b bg-gray-50 rounded-t-lg flex-shrink-0 cursor-grab active:cursor-grabbing"
          onMouseDown={handleMouseDown}
        >
          <h3 className="text-sm font-bold text-gray-800 select-none">Analysis Charts</h3>
          <div className="flex items-center gap-3">
            <div className="text-xs text-gray-600">
              {charts.length} chart{charts.length !== 1 ? 's' : ''}
            </div>
            <button
              onClick={handleReanalyze}
              disabled={isReanalyzing || !sessionId}
              onMouseDown={(e) => e.stopPropagation()}
              className="px-3 py-1 text-xs font-semibold bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded transition-colors"
              title="재분석 (한글 폰트 적용)"
            >
              {isReanalyzing ? '분석중...' : '🔄 재분석'}
            </button>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-gray-600 hover:text-gray-800 text-sm font-bold"
              onMouseDown={(e) => e.stopPropagation()}
            >
              {isExpanded ? '−' : '+'}
            </button>
          </div>
        </div>

        {/* Content */}
        {isExpanded && (
          <div className="overflow-y-auto flex-1">
          {loading ? (
            <div className="text-center text-gray-500 text-sm py-8">Loading charts...</div>
          ) : error ? (
            <div className="text-center text-red-500 text-sm py-8">{error}</div>
          ) : charts.length === 0 ? (
            <div className="text-center text-gray-500 text-sm py-8">
              No analysis charts available
            </div>
          ) : (
            <div className="p-4 space-y-3">
              {categories.map((category) => (
                <div key={category.title} className="border rounded-lg overflow-hidden">
                  {/* Category Header */}
                  <button
                    onClick={() => toggleCategory(category.title)}
                    className="w-full flex items-center justify-between p-2 bg-gray-50 hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{category.icon}</span>
                      <span className="text-xs font-semibold text-gray-800">
                        {category.title}
                      </span>
                      <span className="text-xs text-gray-500">
                        ({category.charts.length})
                      </span>
                    </div>
                    <span className="text-gray-600 text-sm">
                      {expandedCategories.has(category.title) ? '−' : '+'}
                    </span>
                  </button>

                  {/* Category Content */}
                  {expandedCategories.has(category.title) && (
                    <div className="p-3 space-y-3 bg-white">
                      {category.charts.map((chart) => (
                        <div
                          key={chart.name}
                          className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                          onClick={() => setSelectedChart(chart)}
                        >
                          <div className="p-2 bg-gray-50 border-b">
                            <p className="text-xs font-semibold text-gray-800">
                              {chart.title}
                            </p>
                          </div>
                          <div className="p-2">
                            <img
                              src={chart.url}
                              alt={chart.title}
                              className="w-full h-auto rounded"
                              loading="lazy"
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          </div>
        )}
      </div>

      {/* Chart Modal (Full Size View) */}
      {selectedChart && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedChart(null)}
        >
          <div className="relative max-w-6xl max-h-[90vh] bg-white rounded-lg overflow-hidden">
            <div className="p-4 bg-gray-50 border-b flex items-center justify-between">
              <h3 className="text-sm font-bold text-gray-800">{selectedChart.title}</h3>
              <button
                onClick={() => setSelectedChart(null)}
                className="text-gray-600 hover:text-gray-800 text-lg font-bold px-3"
              >
                ✕
              </button>
            </div>
            <div className="p-4 overflow-auto max-h-[calc(90vh-64px)]">
              <img
                src={selectedChart.url}
                alt={selectedChart.title}
                className="w-full h-auto"
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
};
