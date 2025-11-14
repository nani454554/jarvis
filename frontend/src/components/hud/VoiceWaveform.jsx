import React, { useRef, useEffect } from 'react';

const VoiceWaveform = ({ isListening, audioData = [] }) => {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      if (isListening) {
        // Draw circular waveform
        const numBars = 64;
        const radius = 120;

        for (let i = 0; i < numBars; i++) {
          const angle = (i / numBars) * Math.PI * 2;
          const barHeight = audioData[i] || Math.random() * 50 + 10;
          
          const x1 = centerX + Math.cos(angle) * radius;
          const y1 = centerY + Math.sin(angle) * radius;
          const x2 = centerX + Math.cos(angle) * (radius + barHeight);
          const y2 = centerY + Math.sin(angle) * (radius + barHeight);

          const gradient = ctx.createLinearGradient(x1, y1, x2, y2);
          gradient.addColorStop(0, 'rgba(0, 217, 255, 0.2)');
          gradient.addColorStop(1, 'rgba(0, 217, 255, 1)');

          ctx.strokeStyle = gradient;
          ctx.lineWidth = 3;
          ctx.lineCap = 'round';

          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }

        // Draw inner circle
        ctx.strokeStyle = 'rgba(0, 217, 255, 0.5)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.stroke();
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isListening, audioData]);

  return (
    <canvas
      ref={canvasRef}
      width={400}
      height={400}
      className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none"
    />
  );
};

export default VoiceWaveform;
