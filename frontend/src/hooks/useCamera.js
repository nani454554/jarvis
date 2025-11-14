import { useState, useRef, useCallback, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';

export const useCamera = () => {
  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState(null);
  const [detectedFaces, setDetectedFaces] = useState([]);
  const [emotion, setEmotion] = useState(null);
  
  const { sendCameraFrame, messages } = useWebSocket();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);

  const startCamera = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        }
      });

      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setIsActive(true);
      
      // Start sending frames
      startFrameCapture();
      
      console.log('📷 Camera started');
    } catch (err) {
      console.error('Camera access error:', err);
      setError('Failed to access camera');
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setIsActive(false);
    console.log('🛑 Camera stopped');
  }, []);

  const captureFrame = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return null;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    return canvas.toDataURL('image/jpeg', 0.8);
  }, []);

  const startFrameCapture = useCallback(() => {
    // Send frame every 2 seconds
    intervalRef.current = setInterval(() => {
      const frameData = captureFrame();
      if (frameData) {
        sendCameraFrame(frameData);
      }
    }, 2000);
  }, [captureFrame, sendCameraFrame]);

  // Listen for vision updates from WebSocket
  useEffect(() => {
    const latestMessage = messages[messages.length - 1];
    
    if (latestMessage?.type === 'vision_update') {
      setDetectedFaces(latestMessage.faces || []);
      setEmotion(latestMessage.emotion);
    }
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return {
    isActive,
    error,
    detectedFaces,
    emotion,
    videoRef,
    canvasRef,
    startCamera,
    stopCamera,
    captureFrame
  };
};
