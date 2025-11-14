import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const SystemMonitor = () => {
  const [stats, setStats] = useState({ cpu: 0, memory: 0 });
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get('/api/v1/system/stats');
        const data = response.data;

        setStats({
          cpu: data.cpu_usage,
          memory: data.memory_usage
        });

        setHistory(prev => {
          const newHistory = [
            ...prev,
            {
              time: new Date().toLocaleTimeString(),
              cpu: data.cpu_usage,
              memory: data.memory_usage
            }
          ];
          return newHistory.slice(-20); // Keep last 20 points
        });
      } catch (error) {
        console.error('Failed to fetch system stats:', error);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000);

    return () => clearInterval(interval);
  }, []);

  const CircularProgress = ({ value, label, color }) => {
    const radius = 40;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (value / 100) * circumference;

    return (
      <div className="flex flex-col items-center">
        <svg width="120" height="120" className="transform -rotate-90">
          <circle
            cx="60"
            cy="60"
            r={radius}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="8"
            fill="none"
          />
          <circle
            cx="60"
            cy="60"
            r={radius}
            stroke={color}
            strokeWidth="8"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-500"
            style={{
              filter: `drop-shadow(0 0 8px ${color})`
            }}
          />
          <text
            x="60"
            y="60"
            textAnchor="middle"
            dy="7"
            className="transform rotate-90"
            style={{ transformOrigin: '60px 60px' }}
            fill="#00D9FF"
            fontSize="20"
            fontWeight="bold"
          >
            {value.toFixed(1)}%
          </text>
        </svg>
        <span className="mt-2 text-sm text-gray-400">{label}</span>
      </div>
    );
  };

  return (
    <div className="bg-black bg-opacity-50 backdrop-blur-md rounded-lg p-6 border border-primary-500 border-opacity-30">
      <h3 className="text-lg font-semibold text-primary-500 mb-4">System Vitals</h3>
      
      {/* Circular Gauges */}
      <div className="flex justify-around mb-6">
        <CircularProgress value={stats.cpu} label="CPU" color="#00D9FF" />
        <CircularProgress value={stats.memory} label="Memory" color="#0080FF" />
      </div>

      {/* History Chart */}
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={history}>
            <XAxis 
              dataKey="time" 
              stroke="#00D9FF"
              fontSize={10}
              tick={{ fill: '#00D9FF' }}
            />
            <YAxis 
              stroke="#00D9FF"
              fontSize={10}
              tick={{ fill: '#00D9FF' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                border: '1px solid #00D9FF',
                borderRadius: '4px'
              }}
            />
            <Line
              type="monotone"
              dataKey="cpu"
              stroke="#00D9FF"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="memory"
              stroke="#0080FF"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default SystemMonitor;
