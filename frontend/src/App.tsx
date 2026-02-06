import { useState } from 'react';
import CesiumViewer from './components/CesiumViewer';
import SessionSelector from './components/SessionSelector';

function App() {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  return (
    <div className="w-full h-screen bg-gray-900 relative">
      <SessionSelector
        selectedSessionId={selectedSessionId}
        onSessionSelect={setSelectedSessionId}
      />
      <CesiumViewer selectedSessionId={selectedSessionId} />
    </div>
  );
}

export default App;
