import React, { useState, useEffect } from 'react';
import { WebSocketProvider } from './contexts/WebSocketContext';
import BootSequence from './components/boot/BootSequence';
import HUDOverlay from './components/hud/HUDOverlay';
import OrbScene from './components/orb/OrbScene';
import VoiceWaveform from './components/hud/VoiceWaveform';
import SystemMonitor from './components/hud/SystemMonitor';
import CommandLog from './components/hud/CommandLog';
import { useWebSocket } from './contexts/WebSocketContext';
import { useVoice } from './hooks/useVoice';
import { useCamera } from './hooks/useCamera';
import './styles/App.css';

const MainApp = () => {
  const [inputText, setInputText] = useState('');
  const { isConnected, messages, sendCommand } = useWebSocket();
  const { isListening, startListening, stopListening, speak } = useVoice();
  const { isActive: cameraActive, startCamera, stopCamera, videoRef, canvasRef } = useCamera();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputText.trim()) {
      speak(inputText);
      setInputText('');
    }
  };

  const toggleVoice = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const toggleCamera = () => {
    if (cameraActive) {
      stopCamera();
    } else {
      startCamera();
    }
  };

  const quickCommands = [
    'Hello Jarvis',
    'What time is it?',
    'System status',
    'How are you?'
  ];

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-gradient-to-br from-dark-900 via-dark-800 to-dark-700">
      {/* Particle Background */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(50)].map((_, i) => (
          <div
            key={i}
            className="particle absolute w-1 h-1 bg-primary-500 rounded-full opacity-50 animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${5 + Math.random() * 10}s`
            }}
          />
        ))}
      </div>

      {/* Status Bar */}
      <div className="absolute top-0 left-0 right-0 h-16 bg-black bg-opacity-70 backdrop-blur-md border-b border-primary-500 border-opacity-30 flex items-center justify-between px-6 z-50">
        <div className="flex items-center space-x-6">
          <h1 className="text-2xl font-bold text-primary-500 tracking-wider">J.A.R.V.I.S.</h1>
          <div className={`flex items-center space-x-2 ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-sm">{isConnected ? 'ONLINE' : 'OFFLINE'}</span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <button
            onClick={toggleVoice}
            className={`px-4 py-2 rounded-lg ${isListening ? 'bg-red-500' : 'bg-primary-500'} bg-opacity-20 border border-current hover:bg-opacity-30 transition-all`}
          >
            {isListening ? '🎤 Listening...' : '🎤 Voice'}
          </button>
          
          <button
            onClick={toggleCamera}
            className={`px-4 py-2 rounded-lg ${cameraActive ? 'bg-green-500' : 'bg-primary-500'} bg-opacity-20 border border-current hover:bg-opacity-30 transition-all`}
          >
            {cameraActive ? '📷 Camera On' : '📷 Camera Off'}
          </button>

          <div className="text-primary-500 text-sm">
            {new Date().toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Central Orb */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 z-10">
        <OrbScene isListening={isListening} isConnected={isConnected} />
        <VoiceWaveform isListening={isListening} />
      </div>

      {/* Command Input */}
      <div className="absolute bottom-32 left-1/2 transform -translate-x-1/2 w-full max-w-2xl px-4 z-30">
        <form onSubmit={handleSubmit} className="flex space-x-2 mb-4">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Speak or type your command..."
            className="flex-1 px-6 py-4 bg-black bg-opacity-50 backdrop-blur-md border border-primary-500 border-opacity-50 rounded-full text-white placeholder-gray-400 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-opacity-50"
          />
          <button
            type="submit"
            className="px-8 py-4 bg-gradient-to-r from-primary-500 to-blue-500 rounded-full text-black font-semibold hover:shadow-lg hover:shadow-primary-500/50 transition-all transform hover:scale-105"
          >
            Send
          </button>
        </form>

        {/* Quick Commands */}
        <div className="flex justify-center space-x-2 flex-wrap">
          {quickCommands.map((cmd, idx) => (
            <button
              key={idx}
              onClick={() => speak(cmd)}
              className="px-4 py-2 bg-primary-500 bg-opacity-10 border border-primary-500 border-opacity-30 rounded-full text-primary-500 text-sm hover:bg-opacity-20 transition-all"
            >
              {cmd}
            </button>
          ))}
        </div>
      </div>

      {/* Side Panels */}
      <div className="absolute left-6 top-24 bottom-24 w-80 z-20">
        <SystemMonitor />
      </div>

      <div className="absolute right-6 top-24 bottom-24 w-96 z-20">
        <CommandLog messages={messages} />
      </div>

      {/* Hidden Camera Elements */}
      <video ref={videoRef} className="hidden" />
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
};

const App = () => {
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setBooting(false);
    }, 6000);

    return () => clearTimeout(timer);
  }, []);

  if (booting) {
    return <BootSequence />;
  }

  return (
    <WebSocketProvider>
      <MainApp />
    </WebSocketProvider>
  );
};

export default App;
