# Cẩm nang Kỹ năng: Tối ưu UI/UX React Real-time (SKILL_REACT_DASHBOARD.md)

**Mục đích:** Đảm bảo Dashboard không bị giật lag, không sập trình duyệt khi nhận hàng nghìn cảnh báo.

## 1. Ràng buộc Render (Render Throttling) cho Biểu đồ
- Tuyệt đối không gọi `setState` ngay khi nhận được dữ liệu từ WebSocket (sẽ làm UI tính toán lại liên tục).
- **Giải pháp:** Dùng `useRef` để "hứng" dữ liệu data points gửi về từ server. Dùng `setInterval` để copy data từ `ref` sang `state` định kỳ 1 giây/lần để vẽ biểu đồ.

### Code mẫu: Custom Hook cho Real-time Data
```jsx
import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Hook để throttle real-time updates
 * @param {number} intervalMs - Khoảng thời gian giữa các lần update state (ms)
 */
export function useThrottledState(initialValue, intervalMs = 1000) {
    const [state, setState] = useState(initialValue);
    const bufferRef = useRef(initialValue);
    const pendingRef = useRef(false);

    // Accumulate data vào buffer (không trigger re-render)
    const pushToBuffer = useCallback((updater) => {
        if (typeof updater === 'function') {
            bufferRef.current = updater(bufferRef.current);
        } else {
            bufferRef.current = updater;
        }
        pendingRef.current = true;
    }, []);

    // Sync buffer → state định kỳ
    useEffect(() => {
        const interval = setInterval(() => {
            if (pendingRef.current) {
                setState(bufferRef.current);
                pendingRef.current = false;
            }
        }, intervalMs);

        return () => clearInterval(interval);
    }, [intervalMs]);

    return [state, pushToBuffer];
}

// Usage example
function TrafficChart() {
    const [dataPoints, pushData] = useThrottledState([], 1000);
    
    useEffect(() => {
        socket.on('stats:update', (stats) => {
            // Không gọi setState trực tiếp!
            pushData(prev => {
                const newPoints = [...prev, { 
                    time: new Date(), 
                    value: stats.totalPackets 
                }];
                // Giữ tối đa 60 data points (1 phút)
                return newPoints.slice(-60);
            });
        });
        
        return () => socket.off('stats:update');
    }, [pushData]);
    
    return <LineChart data={dataPoints} />;
}
```

## 2. Quản lý Bộ nhớ (Tránh Memory Leak Client)
- Bảng cảnh báo (Alert Table) không được phép dài vô hạn.
- Cài đặt logic: Mảng cảnh báo chỉ giữ lại **tối đa 500 dòng mới nhất**. Khi có cảnh báo mới, đẩy vào đầu mảng và xóa phần tử ở cuối nếu vượt quá 500.

### Code mẫu: Bounded Alert List
```jsx
import { useReducer, useEffect } from 'react';

const MAX_ALERTS = 500;

const alertReducer = (state, action) => {
    switch (action.type) {
        case 'ADD_ALERT':
            // Thêm vào đầu, giới hạn độ dài
            const newAlerts = [action.payload, ...state];
            return newAlerts.slice(0, MAX_ALERTS);
            
        case 'ADD_BATCH':
            // Thêm nhiều alerts cùng lúc
            const combined = [...action.payload, ...state];
            return combined.slice(0, MAX_ALERTS);
            
        case 'ACKNOWLEDGE':
            return state.map(alert => 
                alert.id === action.payload 
                    ? { ...alert, acknowledged: true }
                    : alert
            );
            
        case 'CLEAR_ALL':
            return [];
            
        default:
            return state;
    }
};

export function useAlerts() {
    const [alerts, dispatch] = useReducer(alertReducer, []);
    
    const addAlert = (alert) => dispatch({ type: 'ADD_ALERT', payload: alert });
    const addBatch = (alerts) => dispatch({ type: 'ADD_BATCH', payload: alerts });
    const acknowledge = (id) => dispatch({ type: 'ACKNOWLEDGE', payload: id });
    const clearAll = () => dispatch({ type: 'CLEAR_ALL' });
    
    return { alerts, addAlert, addBatch, acknowledge, clearAll };
}
```

## 3. Tối ưu Component
- Bọc các component nặng (Biểu đồ Chart.js, Bảng DataTable) bằng `React.memo` để tránh bị re-render lây lan từ Component cha.
- Khi render danh sách `alerts` bằng `.map()`, bắt buộc dùng `id` duy nhất làm `key`. Không dùng `index` của mảng để React tái sử dụng DOM hiệu quả nhất.
- Nhớ gọi `socket.off()` trong hàm cleanup của `useEffect` khi component unmount.

### Code mẫu: Optimized Alert Table
```jsx
import React, { memo, useMemo } from 'react';

// Memoized Alert Row
const AlertRow = memo(function AlertRow({ alert, onAcknowledge }) {
    const severityColor = useMemo(() => {
        switch (alert.attack_type) {
            case 'U2R': return 'bg-red-600';
            case 'R2L': return 'bg-red-400';
            case 'DoS': return 'bg-yellow-500';
            case 'Probe': return 'bg-orange-400';
            default: return 'bg-green-500';
        }
    }, [alert.attack_type]);

    return (
        <tr className={`${severityColor} ${alert.acknowledged ? 'opacity-50' : ''}`}>
            <td>{new Date(alert.timestamp).toLocaleTimeString()}</td>
            <td>{alert.src_ip}:{alert.src_port}</td>
            <td>{alert.dst_ip}:{alert.dst_port}</td>
            <td>{alert.protocol}</td>
            <td className="font-bold">{alert.attack_type}</td>
            <td>{(alert.confidence * 100).toFixed(1)}%</td>
            <td>
                {!alert.acknowledged && (
                    <button 
                        onClick={() => onAcknowledge(alert.id)}
                        className="px-2 py-1 bg-white text-black rounded"
                    >
                        ACK
                    </button>
                )}
            </td>
        </tr>
    );
});

// Memoized Alert Table
const AlertTable = memo(function AlertTable({ alerts, onAcknowledge }) {
    return (
        <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-800">
                    <tr>
                        <th>Time</th>
                        <th>Source</th>
                        <th>Destination</th>
                        <th>Protocol</th>
                        <th>Type</th>
                        <th>Confidence</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {alerts.map(alert => (
                        <AlertRow 
                            key={alert.id}  // Dùng ID, không dùng index!
                            alert={alert}
                            onAcknowledge={onAcknowledge}
                        />
                    ))}
                </tbody>
            </table>
        </div>
    );
});

export default AlertTable;
```

## 4. Socket.io Client Setup

### Code mẫu: Socket Provider với Reconnection
```jsx
// contexts/SocketContext.jsx
import { createContext, useContext, useEffect, useState, useRef } from 'react';
import { io } from 'socket.io-client';

const SocketContext = createContext(null);

export function SocketProvider({ children }) {
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState(null);
    const socketRef = useRef(null);

    useEffect(() => {
        const socket = io(import.meta.env.VITE_BACKEND_URL || 'http://localhost:3000', {
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            transports: ['websocket', 'polling']
        });

        socket.on('connect', () => {
            console.log('Socket connected:', socket.id);
            setIsConnected(true);
            setConnectionError(null);
        });

        socket.on('disconnect', (reason) => {
            console.log('Socket disconnected:', reason);
            setIsConnected(false);
        });

        socket.on('connect_error', (error) => {
            console.error('Connection error:', error.message);
            setConnectionError(error.message);
        });

        socketRef.current = socket;

        return () => {
            socket.disconnect();
        };
    }, []);

    return (
        <SocketContext.Provider value={{ 
            socket: socketRef.current, 
            isConnected, 
            connectionError 
        }}>
            {children}
        </SocketContext.Provider>
    );
}

export function useSocket() {
    const context = useContext(SocketContext);
    if (!context) {
        throw new Error('useSocket must be used within SocketProvider');
    }
    return context;
}
```

### Code mẫu: Hook để subscribe events
```jsx
// hooks/useSocketEvent.js
import { useEffect, useRef } from 'react';
import { useSocket } from '../contexts/SocketContext';

export function useSocketEvent(eventName, handler) {
    const { socket } = useSocket();
    const handlerRef = useRef(handler);
    
    // Update handler ref to avoid stale closure
    useEffect(() => {
        handlerRef.current = handler;
    }, [handler]);

    useEffect(() => {
        if (!socket) return;

        const eventHandler = (...args) => {
            handlerRef.current(...args);
        };

        socket.on(eventName, eventHandler);

        return () => {
            socket.off(eventName, eventHandler);  // Quan trọng: cleanup!
        };
    }, [socket, eventName]);
}
```

## 5. Chart.js Integration

### Code mẫu: Real-time Line Chart
```jsx
import { useRef, useEffect, memo } from 'react';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js';

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

const TrafficLineChart = memo(function TrafficLineChart({ dataPoints }) {
    const chartRef = useRef(null);

    const data = {
        labels: dataPoints.map(p => 
            new Date(p.time).toLocaleTimeString('vi-VN', { 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            })
        ),
        datasets: [
            {
                label: 'Packets/sec',
                data: dataPoints.map(p => p.packetsPerSec),
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 0,  // Tắt point để vẽ nhanh hơn
            },
            {
                label: 'Alerts',
                data: dataPoints.map(p => p.alertCount),
                borderColor: 'rgb(239, 68, 68)',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 0,
            }
        ]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,  // Tắt animation để tránh lag
        plugins: {
            legend: {
                position: 'top',
                labels: { color: '#fff' }
            }
        },
        scales: {
            x: {
                ticks: { color: '#9ca3af', maxTicksLimit: 10 },
                grid: { color: 'rgba(255,255,255,0.1)' }
            },
            y: {
                ticks: { color: '#9ca3af' },
                grid: { color: 'rgba(255,255,255,0.1)' },
                beginAtZero: true
            }
        },
        interaction: {
            intersect: false,
            mode: 'index'
        }
    };

    return (
        <div className="h-64">
            <Line ref={chartRef} data={data} options={options} />
        </div>
    );
});

export default TrafficLineChart;
```

## 6. Attack Distribution Pie Chart
```jsx
import { memo } from 'react';
import { Pie } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const ATTACK_COLORS = {
    DoS: '#eab308',      // Yellow
    Probe: '#f97316',    // Orange
    R2L: '#ef4444',      // Red
    U2R: '#dc2626'       // Dark Red
};

const AttackPieChart = memo(function AttackPieChart({ attackCounts }) {
    const labels = Object.keys(attackCounts).filter(k => attackCounts[k] > 0);
    const values = labels.map(k => attackCounts[k]);
    const colors = labels.map(k => ATTACK_COLORS[k]);

    const data = {
        labels,
        datasets: [{
            data: values,
            backgroundColor: colors,
            borderColor: colors.map(c => c),
            borderWidth: 2
        }]
    };

    const options = {
        responsive: true,
        plugins: {
            legend: {
                position: 'right',
                labels: { color: '#fff', padding: 20 }
            },
            tooltip: {
                callbacks: {
                    label: (context) => {
                        const total = values.reduce((a, b) => a + b, 0);
                        const percentage = ((context.raw / total) * 100).toFixed(1);
                        return `${context.label}: ${context.raw} (${percentage}%)`;
                    }
                }
            }
        }
    };

    return <Pie data={data} options={options} />;
});

export default AttackPieChart;
```

## 7. Notification Sound cho Critical Alerts
```jsx
// hooks/useAlertSound.js
import { useCallback, useRef } from 'react';

export function useAlertSound() {
    const audioRef = useRef(null);

    // Preload audio
    if (!audioRef.current) {
        audioRef.current = new Audio('/alert-sound.mp3');
        audioRef.current.volume = 0.5;
    }

    const playAlert = useCallback((attackType) => {
        // Chỉ play sound cho U2R và R2L (critical)
        if (attackType === 'U2R' || attackType === 'R2L') {
            audioRef.current.currentTime = 0;
            audioRef.current.play().catch(e => {
                console.warn('Audio play failed:', e.message);
            });
        }
    }, []);

    return { playAlert };
}
```

## 8. Dark Mode Toggle
```jsx
// hooks/useDarkMode.js
import { useState, useEffect } from 'react';

export function useDarkMode() {
    const [isDark, setIsDark] = useState(() => {
        const saved = localStorage.getItem('darkMode');
        return saved ? JSON.parse(saved) : true;  // Default: dark
    });

    useEffect(() => {
        localStorage.setItem('darkMode', JSON.stringify(isDark));
        document.documentElement.classList.toggle('dark', isDark);
    }, [isDark]);

    return [isDark, setIsDark];
}
```

## 9. Project Structure
```
/frontend
├── src/
│   ├── components/
│   │   ├── AlertTable.jsx
│   │   ├── TrafficChart.jsx
│   │   ├── AttackPieChart.jsx
│   │   ├── StatsCards.jsx
│   │   └── Header.jsx
│   ├── contexts/
│   │   └── SocketContext.jsx
│   ├── hooks/
│   │   ├── useThrottledState.js
│   │   ├── useAlerts.js
│   │   ├── useSocketEvent.js
│   │   ├── useAlertSound.js
│   │   └── useDarkMode.js
│   ├── pages/
│   │   └── Dashboard.jsx
│   ├── App.jsx
│   └── main.jsx
├── public/
│   └── alert-sound.mp3
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.js
```

## 10. Dependencies (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-chartjs-2": "^5.2.0",
    "chart.js": "^4.4.1",
    "socket.io-client": "^4.6.1",
    "tailwindcss": "^3.4.1"
  }
}
```