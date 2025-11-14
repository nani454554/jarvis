import { useState, useRef, useCallback, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';

export const useVoice = () => {
  const [isListening, setIsListening] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState(null);
  
  const { sendCommand, sendMessage } = useWebSocket();
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);

  const startListening = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // Convert to base64
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64Audio = reader.result.split(',')[1];
          
          // Send to backend via WebSocket
          sendMessage({
            type: 'audio_chunk',
            audio: base64Audio,
            is_final: true
          });
        };
        reader.readAsDataURL(audioBlob);
      };

      mediaRecorder.start();
      setIsListening(true);
      setIsRecording(true);
      
      console.log('🎤 Started recording');
    } catch (err) {
      console.error('Microphone access error:', err);
      setError('Failed to access microphone');
    }
  }, [sendMessage]);

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsListening(false);
      
      console.log('🛑 Stopped recording');
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  }, [isRecording]);

  const speak = useCallback((text) => {
    return sendCommand(text);
  }, [sendCommand]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopListening();
    };
  }, [stopListening]);

  return {
    isListening,
    isRecording,
    transcript,
    error,
    startListening,
    stopListening,
    speak,
    setTranscript
  };
};
