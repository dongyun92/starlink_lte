import React from 'react';
import type { FlightScenario } from '@/types/flight';

interface FlightSelectorProps {
  scenarios: FlightScenario[];
  selectedFlightId: number | null;
  onFlightSelect: (flightId: number | null) => void;
}

export const FlightSelector: React.FC<FlightSelectorProps> = ({
  scenarios,
  selectedFlightId,
  onFlightSelect,
}) => {
  // Don't show selector if only one flight
  if (scenarios.length <= 1) {
    return null;
  }

  return (
    <div className="absolute top-[30rem] left-4 bg-white rounded-lg shadow-lg p-3 z-10 min-w-[280px] max-w-[320px]">
      <h3 className="text-sm font-bold mb-2">Flight Scenarios</h3>

      <div className="space-y-2">
        {/* All Flights option */}
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="radio"
            name="flight"
            checked={selectedFlightId === null}
            onChange={() => onFlightSelect(null)}
            className="w-3 h-3 text-blue-600"
          />
          <span className="text-sm text-gray-700">
            All Flights ({scenarios.reduce((sum, s) => sum + s.data_points, 0)} points)
          </span>
        </label>

        {/* Individual flight options */}
        {scenarios.map((scenario) => (
          <label
            key={scenario.flight_id}
            className="flex items-center space-x-2 cursor-pointer"
          >
            <input
              type="radio"
              name="flight"
              checked={selectedFlightId === scenario.flight_id}
              onChange={() => onFlightSelect(scenario.flight_id)}
              className="w-3 h-3 text-blue-600"
            />
            <div className="flex-1">
              <div className="text-sm font-medium text-gray-900">
                Flight {scenario.flight_id + 1}: {scenario.scenario_name}
              </div>
              <div className="text-xs text-gray-500">
                {scenario.data_points.toLocaleString()} points
              </div>
            </div>
          </label>
        ))}
      </div>

      {/* Selected flight details */}
      {selectedFlightId !== null && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          {(() => {
            const selected = scenarios.find((s) => s.flight_id === selectedFlightId);
            if (!selected) return null;

            const startTime = new Date(selected.time_range.start);
            const endTime = new Date(selected.time_range.end);
            const durationSec = (endTime.getTime() - startTime.getTime()) / 1000;
            const durationMin = Math.floor(durationSec / 60);
            const durationSecRem = Math.floor(durationSec % 60);

            return (
              <div className="space-y-1">
                <div className="text-xs text-gray-600">
                  <span className="font-semibold">Duration:</span> {durationMin}m {durationSecRem}s
                </div>
                <div className="text-xs text-gray-600">
                  <span className="font-semibold">Altitude:</span>{' '}
                  {selected.coordinates.alt_min.toFixed(1)}m - {selected.coordinates.alt_max.toFixed(1)}m
                </div>
                <div className="text-xs text-gray-600">
                  <span className="font-semibold">Time:</span>{' '}
                  {startTime.toLocaleTimeString()} - {endTime.toLocaleTimeString()}
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};
