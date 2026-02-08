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

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onFlightSelect(value === 'all' ? null : parseInt(value, 10));
  };

  return (
    <div className="absolute top-[16.5rem] left-4 bg-white rounded-lg shadow-lg p-3 z-10 min-w-[280px] max-w-[320px]">
      <label className="block">
        <span className="text-sm font-bold text-gray-700 mb-2 block">Flight Scenario</span>
        <select
          value={selectedFlightId === null ? 'all' : selectedFlightId.toString()}
          onChange={handleChange}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="all">
            All Flights ({scenarios.reduce((sum, s) => sum + s.data_points, 0).toLocaleString()} pts)
          </option>
          {scenarios.map((scenario) => (
            <option key={scenario.flight_id} value={scenario.flight_id}>
              Flight {scenario.flight_id + 1}: {scenario.scenario_name} ({scenario.data_points.toLocaleString()} pts)
            </option>
          ))}
        </select>
      </label>
    </div>
  );
};
