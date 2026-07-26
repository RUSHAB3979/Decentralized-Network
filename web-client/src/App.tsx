import React, { useEffect, useState } from 'react';
import type {
  TabType,
  GameTitle,
  SessionState,
  SessionStats,
  HealthCheckResponse,
} from './types';
import { checkOrchestratorHealth, MOCK_CATALOG } from './services/api';
import Header from './components/Header';
import CatalogView from './components/CatalogView';
import SessionPlayer from './components/SessionPlayer';
import NodeTelemetry from './components/NodeTelemetry';
import InputDebugger from './components/InputDebugger';
import PreflightModal from './components/PreflightModal';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('catalog');
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [selectedTitle, setSelectedTitle] = useState<GameTitle | null>(null);
  const [isPreflightOpen, setIsPreflightOpen] = useState(false);
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [sessionStats, setSessionStats] = useState<SessionStats | null>(null);

  useEffect(() => {
    checkOrchestratorHealth().then(setHealth);
  }, []);

  const handleSelectTitle = (title: GameTitle) => {
    setSelectedTitle(title);
    setIsPreflightOpen(true);
  };

  const handlePreflightClose = () => {
    setIsPreflightOpen(false);
  };

  const handleSessionReady = (state: SessionState) => {
    setSessionState(state);
    setIsPreflightOpen(false);
    setActiveTab('session');
    setSessionStats({
      fps: 60,
      resolution: '1920x1080',
      bitrate_kbps: 18500,
      rtt_ms: 22,
      packet_loss_pct: 0.0,
      codec: 'H.264 / NVENC High Profile',
      connection_mode: 'direct_p2p',
      frames_decoded: 3600,
      frames_dropped: 1,
    });
  };

  const handleEndSession = () => {
    setSessionState(null);
    setSessionStats(null);
    setSelectedTitle(null);
    setActiveTab('catalog');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        health={health}
        activeSessionState={sessionState ?? undefined}
      />

      <main className="flex-1 container mx-auto px-4 py-6 max-w-7xl">
        {activeTab === 'catalog' && (
          <CatalogView
            titles={MOCK_CATALOG}
            onSelectTitle={handleSelectTitle}
          />
        )}
        {activeTab === 'session' && (
          <SessionPlayer
            title={selectedTitle}
            stats={sessionStats}
            onEndSession={handleEndSession}
            onOpenDebugger={() => setActiveTab('debugger')}
          />
        )}
        {activeTab === 'telemetry' && <NodeTelemetry />}
        {activeTab === 'debugger' && <InputDebugger />}
      </main>

      {isPreflightOpen && selectedTitle && (
        <PreflightModal
          title={selectedTitle}
          onClose={handlePreflightClose}
          onSessionReady={handleSessionReady}
        />
      )}

      <footer className="border-t border-slate-800/50 py-4 text-center text-sm text-slate-500">
        <p>
          P2P Cloud Gaming &amp; Compute Marketplace &middot; v0.1.0 &middot;
          Decentralized GPU Streaming
        </p>
      </footer>
    </div>
  );
};

export default App;
