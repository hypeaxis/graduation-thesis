# Cẩm nang Kỹ năng: Node.js IPC & Real-time Server (SKILL_NODE_SOCKETIO.md)

**Mục đích:** Xử lý chịu tải cao, kết nối Parser dịch log Snort (qua TCP/IPC) và FastAPI (qua HTTP), sau đó đẩy Real-time lên React.

## 1. Xử lý TCP Stream Fragmentation (Từ Parser -> Node.js)
- TCP là stream, không phải message. JSON từ Parser Snort gửi lên qua TCP port 9000 có thể bị cắt nửa hoặc dính chùm.
- **Giải pháp:** Parser phải nối thêm `\n` vào cuối JSON. Node.js dùng một biến `buffer` kiểu chuỗi để tích lũy, sau đó dùng `.split('\n')` để tách và parse những JSON đã hoàn chỉnh.

### Code mẫu: TCP Server nhận data từ Parser Snort
```javascript
const net = require('net');

class SnifferTCPServer {
    constructor(port = 9000) {
        this.port = port;
        this.buffer = '';
        this.onDataCallback = null;
    }

    start(onData) {
        this.onDataCallback = onData;
        
        this.server = net.createServer((socket) => {
            console.log(`Parser connected: ${socket.remoteAddress}`);
            
            socket.on('data', (chunk) => {
                this.handleData(chunk.toString());
            });
            
            socket.on('close', () => {
                console.log('Parser disconnected');
                this.buffer = '';  // Reset buffer
            });
            
            socket.on('error', (err) => {
                console.error('Socket error:', err.message);
            });
        });
        
        this.server.listen(this.port, () => {
            console.log(`TCP Server listening on port ${this.port}`);
        });
    }

    handleData(chunk) {
        // Tích lũy vào buffer
        this.buffer += chunk;
        
        // Tách theo newline
        const lines = this.buffer.split('\n');
        
        // Giữ lại phần chưa hoàn chỉnh (không có \n ở cuối)
        this.buffer = lines.pop();
        
        // Parse và xử lý các JSON hoàn chỉnh
        for (const line of lines) {
            if (line.trim()) {
                try {
                    const data = JSON.parse(line);
                    if (this.onDataCallback) {
                        this.onDataCallback(data);
                    }
                } catch (err) {
                    console.error('JSON parse error:', err.message);
                    console.error('Invalid line:', line.substring(0, 100));
                }
            }
        }
    }

    stop() {
        if (this.server) {
            this.server.close();
        }
    }
}

module.exports = SnifferTCPServer;
```

## 2. Batching & Rate Limiting (Bảo vệ FastAPI)
- Nếu bị tấn công DoS, luồng dữ liệu sẽ ồ ạt. Không được dùng `axios` gọi API FastAPI cho từng vector một.
- **Giải pháp:** Tạo một Request Queue. Gom các vector lại thành mảng (VD: 100 items) hoặc đợi một khoảng thời gian ngắn (VD: 50ms), sau đó mới gọi endpoint `/batch_predict` một lần.

### Code mẫu: Request Batcher
```javascript
const axios = require('axios');

class RequestBatcher {
    constructor(options = {}) {
        this.modelApiUrl = options.modelApiUrl || 'http://localhost:8000';
        this.batchSize = options.batchSize || 100;
        this.batchTimeoutMs = options.batchTimeoutMs || 50;
        this.maxQueueSize = options.maxQueueSize || 10000;
        
        this.queue = [];
        this.pendingCallbacks = [];
        this.timer = null;
        this.isProcessing = false;
        
        // Circuit breaker state
        this.failureCount = 0;
        this.circuitOpen = false;
        this.circuitResetTimeout = null;
    }

    async add(featureVector, metadata) {
        return new Promise((resolve, reject) => {
            // Circuit breaker check
            if (this.circuitOpen) {
                return reject(new Error('Circuit breaker is open'));
            }
            
            // Queue overflow protection
            if (this.queue.length >= this.maxQueueSize) {
                console.warn('Queue overflow! Dropping oldest items');
                this.queue.splice(0, this.batchSize);
                this.pendingCallbacks.splice(0, this.batchSize);
            }
            
            this.queue.push({ features: featureVector, metadata });
            this.pendingCallbacks.push({ resolve, reject });
            
            // Start timer nếu chưa có
            if (!this.timer && !this.isProcessing) {
                this.timer = setTimeout(() => this.flush(), this.batchTimeoutMs);
            }
            
            // Flush ngay nếu đủ batch size
            if (this.queue.length >= this.batchSize) {
                this.flush();
            }
        });
    }

    async flush() {
        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
        }
        
        if (this.queue.length === 0 || this.isProcessing) {
            return;
        }
        
        this.isProcessing = true;
        
        // Lấy batch từ queue
        const batch = this.queue.splice(0, this.batchSize);
        const callbacks = this.pendingCallbacks.splice(0, this.batchSize);
        
        try {
            const samples = batch.map(item => item.features);
            
            const response = await axios.post(
                `${this.modelApiUrl}/batch_predict`,
                { samples },
                { timeout: 5000 }
            );
            
            // Reset circuit breaker on success
            this.failureCount = 0;
            
            // Resolve all callbacks
            const predictions = response.data.predictions;
            callbacks.forEach((cb, i) => {
                cb.resolve({
                    prediction: predictions[i],
                    metadata: batch[i].metadata
                });
            });
            
        } catch (error) {
            console.error('Batch predict failed:', error.message);
            
            // Circuit breaker logic
            this.failureCount++;
            if (this.failureCount >= 5) {
                this.openCircuit();
            }
            
            // Reject all callbacks
            callbacks.forEach(cb => cb.reject(error));
        }
        
        this.isProcessing = false;
        
        // Process remaining queue
        if (this.queue.length > 0) {
            this.timer = setTimeout(() => this.flush(), this.batchTimeoutMs);
        }
    }

    openCircuit() {
        console.error('Circuit breaker OPEN - FastAPI seems down');
        this.circuitOpen = true;
        
        // Auto-reset sau 30 giây
        this.circuitResetTimeout = setTimeout(() => {
            console.log('Circuit breaker RESET - Retrying...');
            this.circuitOpen = false;
            this.failureCount = 0;
        }, 30000);
    }

    getStats() {
        return {
            queueLength: this.queue.length,
            isProcessing: this.isProcessing,
            circuitOpen: this.circuitOpen,
            failureCount: this.failureCount
        };
    }
}

module.exports = RequestBatcher;
```

## 3. Tối ưu WebSocket (Socket.io)
- **Chỉ Push Alert:** Chỉ emit sự kiện `alert:new` khi model trả về nhãn là Tấn công. Không push traffic "Normal" (chiếm đa số) lên UI để tránh lag.
- **Gom Stats:** Tổng hợp lưu lượng băng thông/số lượng request tại Backend và chỉ emit sự kiện `stats:update` mỗi 1 giây/lần.

### Code mẫu: Socket.io Server
```javascript
const { Server } = require('socket.io');

class RealtimeServer {
    constructor(httpServer) {
        this.io = new Server(httpServer, {
            cors: {
                origin: ['http://localhost:3000', 'http://localhost:5173'],
                methods: ['GET', 'POST']
            },
            pingTimeout: 60000,
            pingInterval: 25000
        });
        
        // Stats accumulator (gom stats, emit mỗi 1 giây)
        this.stats = {
            totalPackets: 0,
            totalAlerts: 0,
            attackCounts: { DoS: 0, Probe: 0, R2L: 0, U2R: 0 },
            lastMinutePackets: []
        };
        
        this.connectedClients = 0;
        
        this.setupConnectionHandlers();
        this.startStatsEmitter();
    }

    setupConnectionHandlers() {
        this.io.on('connection', (socket) => {
            this.connectedClients++;
            console.log(`Client connected: ${socket.id} (Total: ${this.connectedClients})`);
            
            // Send current stats immediately
            socket.emit('stats:initial', this.stats);
            
            socket.on('disconnect', () => {
                this.connectedClients--;
                console.log(`Client disconnected: ${socket.id}`);
            });
            
            // Handle client requests
            socket.on('alerts:fetch', async (params, callback) => {
                // Fetch from database and respond
                const alerts = await this.fetchAlerts(params);
                callback(alerts);
            });
        });
    }

    startStatsEmitter() {
        // Emit stats mỗi 1 giây
        setInterval(() => {
            if (this.connectedClients > 0) {
                this.io.emit('stats:update', {
                    ...this.stats,
                    connectedClients: this.connectedClients,
                    timestamp: Date.now()
                });
            }
            
            // Reset per-second counters
            this.stats.lastMinutePackets.push(this.stats.totalPackets);
            if (this.stats.lastMinutePackets.length > 60) {
                this.stats.lastMinutePackets.shift();
            }
        }, 1000);
    }

    // Được gọi khi có prediction result
    handlePrediction(result) {
        this.stats.totalPackets++;
        
        const { prediction, metadata } = result;
        
        // Chỉ emit và count nếu là attack
        if (prediction.label !== 'Normal') {
            this.stats.totalAlerts++;
            this.stats.attackCounts[prediction.label]++;
            
            // Emit alert ngay lập tức
            const alert = {
                id: Date.now(),
                timestamp: new Date().toISOString(),
                src_ip: metadata.src_ip,
                dst_ip: metadata.dst_ip,
                src_port: metadata.src_port,
                dst_port: metadata.dst_port,
                protocol: metadata.protocol,
                attack_type: prediction.label,
                confidence: prediction.confidence,
                reconstruction_error: prediction.reconstruction_error
            };
            
            this.io.emit('alert:new', alert);
            
            return alert;  // Return để lưu vào database
        }
        
        return null;
    }

    getStats() {
        return {
            ...this.stats,
            connectedClients: this.connectedClients
        };
    }
}

module.exports = RealtimeServer;
```

## 4. Main Server Integration

### Code mẫu: Express + Socket.io + TCP Server
```javascript
// server.js
const express = require('express');
const http = require('http');
const cors = require('cors');

const SnifferTCPServer = require('./services/SnifferTCPServer');
const RequestBatcher = require('./services/RequestBatcher');
const RealtimeServer = require('./services/RealtimeServer');
const AlertRepository = require('./repositories/AlertRepository');

const app = express();
const server = http.createServer(app);

// Middleware
app.use(cors());
app.use(express.json());

// Initialize services
const alertRepo = new AlertRepository();
const batcher = new RequestBatcher({
    modelApiUrl: process.env.MODEL_API_URL || 'http://localhost:8000',
    batchSize: 100,
    batchTimeoutMs: 50
});
const realtimeServer = new RealtimeServer(server);
const tcpServer = new SnifferTCPServer(9000);

// Connect the pipeline
tcpServer.start(async (data) => {
    try {
        const result = await batcher.add(data.features, {
            src_ip: data.src_ip,
            dst_ip: data.dst_ip,
            src_port: data.src_port,
            dst_port: data.dst_port,
            protocol: data.protocol
        });
        
        const alert = realtimeServer.handlePrediction(result);
        
        if (alert) {
            await alertRepo.save(alert);
        }
    } catch (error) {
        console.error('Pipeline error:', error.message);
    }
});

// REST API routes
app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        batcher: batcher.getStats(),
        realtime: realtimeServer.getStats()
    });
});

app.get('/api/alerts', async (req, res) => {
    const { page = 1, limit = 100, type, since } = req.query;
    const alerts = await alertRepo.find({ page, limit, type, since });
    res.json(alerts);
});

app.get('/api/stats', (req, res) => {
    res.json(realtimeServer.getStats());
});

// Start server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`Backend server running on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('Shutting down...');
    tcpServer.stop();
    server.close();
    process.exit(0);
});
```

## 5. Package.json
```json
{
  "name": "ids-backend",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js",
    "test": "jest"
  },
  "dependencies": {
    "axios": "^1.6.5",
    "cors": "^2.8.5",
    "express": "^4.18.2",
    "socket.io": "^4.6.1",
    "better-sqlite3": "^9.4.1"
  },
  "devDependencies": {
    "jest": "^29.7.0",
    "nodemon": "^3.0.3",
    "supertest": "^6.3.4"
  }
}
```

## 6. Environment Variables
```bash
# .env
PORT=3000
MODEL_API_URL=http://localhost:8000
SNIFFER_PORT=9000
DATABASE_PATH=./data/ids.db
NODE_ENV=development
```