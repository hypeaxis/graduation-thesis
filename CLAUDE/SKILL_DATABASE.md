```markdown
# Cẩm nang Kỹ năng: Database Design & Query Optimization (SKILL_DATABASE.md)

**Mục đích:** Hướng dẫn thiết kế schema và tối ưu truy vấn cho việc lưu trữ và truy xuất cảnh báo IDS với tốc độ cao.

## 1. Lựa chọn Database Engine
- **SQLite:** Phù hợp cho development, demo, hoặc hệ thống single-node. File-based, không cần cài đặt server riêng.
- **PostgreSQL:** Phù hợp cho production, hỗ trợ concurrent writes tốt hơn, có JSONB và Full-text search.
- **Khuyến nghị:** Bắt đầu với SQLite để nhanh chóng prototype, migrate sang PostgreSQL khi cần scale.

| Tiêu chí | SQLite | PostgreSQL |
|----------|--------|------------|
| Setup | Zero config | Cần cài đặt server |
| Concurrent writes | Kém (file locking) | Tốt (MVCC) |
| Performance | Tốt cho read-heavy | Tốt cho cả read/write |
| Scaling | Không scale | Horizontal scaling |
| Dung lượng | Tốt cho < 1GB | Tốt cho TB+ |
| Deployment | Copy file | Docker/Server |

## 2. Schema Design cho Alert Storage

### Bảng `alerts` (Lưu cảnh báo)
```sql
CREATE TABLE alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    src_ip          VARCHAR(45) NOT NULL,  -- Hỗ trợ IPv6
    dst_ip          VARCHAR(45) NOT NULL,
    src_port        INTEGER,
    dst_port        INTEGER,
    protocol        VARCHAR(10) NOT NULL,  -- TCP, UDP, ICMP
    attack_type     VARCHAR(20) NOT NULL,  -- Normal, DoS, Probe, R2L, U2R
    confidence      REAL NOT NULL,         -- 0.0 - 1.0
    feature_vector  TEXT,                  -- JSON array 122 features (optional)
    is_acknowledged BOOLEAN DEFAULT FALSE,
    notes           TEXT
);

-- Index cho truy vấn nhanh
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp DESC);
CREATE INDEX idx_alerts_attack_type ON alerts(attack_type);
CREATE INDEX idx_alerts_src_ip ON alerts(src_ip);
CREATE INDEX idx_alerts_dst_ip ON alerts(dst_ip);
```

### Bảng `stats_hourly` (Thống kê theo giờ)
```sql
CREATE TABLE stats_hourly (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    hour_start      DATETIME NOT NULL UNIQUE,
    total_packets   INTEGER DEFAULT 0,
    total_alerts    INTEGER DEFAULT 0,
    dos_count       INTEGER DEFAULT 0,
    probe_count     INTEGER DEFAULT 0,
    r2l_count       INTEGER DEFAULT 0,
    u2r_count       INTEGER DEFAULT 0,
    avg_latency_ms  REAL
);

CREATE INDEX idx_stats_hour ON stats_hourly(hour_start DESC);
```

### Bảng `connection_logs` (Optional - để debug)
```sql
CREATE TABLE connection_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    src_ip          VARCHAR(45) NOT NULL,
    dst_ip          VARCHAR(45) NOT NULL,
    src_port        INTEGER,
    dst_port        INTEGER,
    protocol        VARCHAR(10) NOT NULL,
    duration_sec    REAL,
    src_bytes       INTEGER,
    dst_bytes       INTEGER,
    flag            VARCHAR(10),  -- TCP flag: SF, S0, REJ, etc.
    prediction      VARCHAR(20),
    confidence      REAL
);

-- Index cho debug queries
CREATE INDEX idx_conn_timestamp ON connection_logs(timestamp DESC);
```

## 3. Node.js Integration (better-sqlite3)

### Cài đặt
```bash
npm install better-sqlite3
```

### Alert Repository Class
```javascript
// repositories/AlertRepository.js
const Database = require('better-sqlite3');
const path = require('path');

class AlertRepository {
    constructor(dbPath = './data/ids.db') {
        this.db = new Database(dbPath, { verbose: console.log });
        this.db.pragma('journal_mode = WAL');  // Write-Ahead Logging - tăng performance
        this.db.pragma('synchronous = NORMAL');
        this.initTables();
        this.prepareStatements();
    }

    initTables() {
        this.db.exec(`
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                src_ip VARCHAR(45) NOT NULL,
                dst_ip VARCHAR(45) NOT NULL,
                src_port INTEGER,
                dst_port INTEGER,
                protocol VARCHAR(10) NOT NULL,
                attack_type VARCHAR(20) NOT NULL,
                confidence REAL NOT NULL,
                reconstruction_error REAL,
                is_acknowledged BOOLEAN DEFAULT FALSE
            );
            
            CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                ON alerts(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_alerts_attack_type 
                ON alerts(attack_type);
        `);
    }

    prepareStatements() {
        // Prepared statements cho performance
        this.insertStmt = this.db.prepare(`
            INSERT INTO alerts 
            (timestamp, src_ip, dst_ip, src_port, dst_port, protocol, 
             attack_type, confidence, reconstruction_error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        `);

        this.findRecentStmt = this.db.prepare(`
            SELECT * FROM alerts
            WHERE timestamp > datetime('now', '-' || ? || ' minutes')
            ORDER BY timestamp DESC
            LIMIT ?
        `);

        this.statsStmt = this.db.prepare(`
            SELECT 
                attack_type,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence
            FROM alerts
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY attack_type
        `);
    }

    save(alert) {
        return this.insertStmt.run(
            alert.timestamp || new Date().toISOString(),
            alert.src_ip,
            alert.dst_ip,
            alert.src_port,
            alert.dst_port,
            alert.protocol,
            alert.attack_type,
            alert.confidence,
            alert.reconstruction_error || null
        );
    }

    // Batch insert với transaction (quan trọng cho performance!)
    saveBatch(alerts) {
        const insertMany = this.db.transaction((items) => {
            for (const alert of items) {
                this.save(alert);
            }
        });
        return insertMany(alerts);
    }

    findRecent(minutesBack = 60, limit = 100) {
        return this.findRecentStmt.all(minutesBack, limit);
    }

    findByFilters({ page = 1, limit = 100, type, since }) {
        let sql = 'SELECT * FROM alerts WHERE 1=1';
        const params = [];

        if (type) {
            sql += ' AND attack_type = ?';
            params.push(type);
        }

        if (since) {
            sql += ' AND timestamp > ?';
            params.push(since);
        }

        sql += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?';
        params.push(limit, (page - 1) * limit);

        return this.db.prepare(sql).all(...params);
    }

    getStats() {
        return this.statsStmt.all();
    }

    acknowledge(id) {
        return this.db.prepare(
            'UPDATE alerts SET is_acknowledged = TRUE WHERE id = ?'
        ).run(id);
    }

    cleanup(daysOld = 30) {
        const result = this.db.prepare(`
            DELETE FROM alerts 
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        `).run(daysOld);
        
        this.db.pragma('vacuum');
        return result.changes;
    }

    close() {
        this.db.close();
    }
}

module.exports = AlertRepository;
```

## 4. Query Patterns thường dùng

### Lấy alerts mới nhất (cho Dashboard)
```sql
SELECT id, timestamp, src_ip, dst_ip, attack_type, confidence
FROM alerts
WHERE timestamp > datetime('now', '-1 hour')
ORDER BY timestamp DESC
LIMIT 100;
```

### Thống kê phân bố tấn công (cho Pie Chart)
```sql
SELECT attack_type, COUNT(*) as count
FROM alerts
WHERE timestamp > datetime('now', '-24 hours')
  AND attack_type != 'Normal'
GROUP BY attack_type;
```

### Aggregation cho Line Chart (số lượng alert theo phút)
```sql
SELECT 
    strftime('%Y-%m-%d %H:%M', timestamp) as minute,
    COUNT(*) as alert_count
FROM alerts
WHERE timestamp > datetime('now', '-1 hour')
GROUP BY minute
ORDER BY minute;
```

### Top attacker IPs
```sql
SELECT 
    src_ip,
    COUNT(*) as attack_count,
    GROUP_CONCAT(DISTINCT attack_type) as attack_types
FROM alerts
WHERE timestamp > datetime('now', '-24 hours')
  AND attack_type != 'Normal'
GROUP BY src_ip
ORDER BY attack_count DESC
LIMIT 10;
```

### Alert timeline (cho heatmap)
```sql
SELECT 
    strftime('%H', timestamp) as hour,
    strftime('%w', timestamp) as day_of_week,
    COUNT(*) as count
FROM alerts
WHERE timestamp > datetime('now', '-7 days')
GROUP BY hour, day_of_week;
```

## 5. Tối ưu hiệu năng

### Batch Insert (Từ Node.js)
- **Sai:** Insert từng alert một trong vòng lặp.
- **Đúng:** Gom nhiều alerts lại, dùng một transaction với `BEGIN`/`COMMIT`:
```sql
BEGIN TRANSACTION;
INSERT INTO alerts (src_ip, dst_ip, ...) VALUES (...);
INSERT INTO alerts (src_ip, dst_ip, ...) VALUES (...);
-- ... nhiều INSERT khác
COMMIT;
```

### SQLite PRAGMA Settings
```javascript
// Optimal settings cho IDS workload
db.pragma('journal_mode = WAL');      // Write-Ahead Log cho concurrent reads
db.pragma('synchronous = NORMAL');    // Faster writes (vẫn safe)
db.pragma('cache_size = -64000');     // 64MB cache
db.pragma('temp_store = MEMORY');     // Temp tables in RAM
db.pragma('mmap_size = 268435456');   // Memory-mapped I/O (256MB)
```

### Partition by Time (PostgreSQL)
- Khi bảng `alerts` quá lớn (> 10 triệu rows), cân nhắc partition theo tháng.
- Giúp query trên time range nhanh hơn đáng kể và dễ dàng xóa dữ liệu cũ.

```sql
-- PostgreSQL partitioning example
CREATE TABLE alerts (
    id SERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    src_ip VARCHAR(45),
    -- ... other columns
) PARTITION BY RANGE (timestamp);

CREATE TABLE alerts_2026_03 PARTITION OF alerts
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
    
CREATE TABLE alerts_2026_04 PARTITION OF alerts
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

### Connection Pooling (PostgreSQL)
```javascript
// Using pg-pool for PostgreSQL
const { Pool } = require('pg');

const pool = new Pool({
    host: 'localhost',
    database: 'ids_db',
    user: 'ids_user',
    password: process.env.DB_PASSWORD,
    min: 2,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000
});

// Usage
const client = await pool.connect();
try {
    const result = await client.query('SELECT * FROM alerts LIMIT 10');
    return result.rows;
} finally {
    client.release();  // Return to pool
}
```

## 6. Data Retention Policy
- Alerts cũ hơn 30 ngày nên được archive hoặc xóa để giữ database nhẹ.
- Cronjob chạy hàng ngày:

### Cleanup Script
```javascript
// scripts/cleanup.js
const AlertRepository = require('../repositories/AlertRepository');

async function runCleanup() {
    const repo = new AlertRepository();
    
    console.log('Starting cleanup...');
    
    // Delete old alerts
    const deleted = repo.cleanup(30);  // 30 days
    console.log(`Deleted ${deleted} old alerts`);
    
    // Archive to CSV (optional)
    const oldAlerts = repo.db.prepare(`
        SELECT * FROM alerts 
        WHERE timestamp < datetime('now', '-7 days')
          AND timestamp > datetime('now', '-30 days')
    `).all();
    
    if (oldAlerts.length > 0) {
        const fs = require('fs');
        const csv = oldAlerts.map(a => 
            `${a.timestamp},${a.src_ip},${a.dst_ip},${a.attack_type}`
        ).join('\n');
        
        const filename = `archive_${new Date().toISOString().split('T')[0]}.csv`;
        fs.writeFileSync(`./data/archives/${filename}`, csv);
        console.log(`Archived ${oldAlerts.length} alerts to ${filename}`);
    }
    
    repo.close();
}

runCleanup();
```

### Cron Setup
```bash
# Add to crontab -e
# Run cleanup daily at 3 AM
0 3 * * * cd /path/to/backend && node scripts/cleanup.js >> /var/log/ids-cleanup.log 2>&1
```

## 7. Migration Script (SQLite → PostgreSQL)
```javascript
// scripts/migrate-to-postgres.js
const Database = require('better-sqlite3');
const { Pool } = require('pg');

async function migrate() {
    const sqlite = new Database('./data/ids.db');
    const pg = new Pool({ /* connection config */ });

    // Create table in PostgreSQL
    await pg.query(`
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            src_ip VARCHAR(45) NOT NULL,
            dst_ip VARCHAR(45) NOT NULL,
            src_port INTEGER,
            dst_port INTEGER,
            protocol VARCHAR(10) NOT NULL,
            attack_type VARCHAR(20) NOT NULL,
            confidence REAL NOT NULL,
            reconstruction_error REAL,
            is_acknowledged BOOLEAN DEFAULT FALSE
        )
    `);

    // Batch migrate
    const alerts = sqlite.prepare('SELECT * FROM alerts').all();
    const batchSize = 1000;

    for (let i = 0; i < alerts.length; i += batchSize) {
        const batch = alerts.slice(i, i + batchSize);
        const values = batch.map(a => 
            `('${a.timestamp}', '${a.src_ip}', '${a.dst_ip}', 
              ${a.src_port}, ${a.dst_port}, '${a.protocol}',
              '${a.attack_type}', ${a.confidence}, ${a.reconstruction_error || 'NULL'},
              ${a.is_acknowledged})`
        ).join(',');

        await pg.query(`
            INSERT INTO alerts 
            (timestamp, src_ip, dst_ip, src_port, dst_port, protocol,
             attack_type, confidence, reconstruction_error, is_acknowledged)
            VALUES ${values}
        `);

        console.log(`Migrated ${Math.min(i + batchSize, alerts.length)}/${alerts.length}`);
    }

    sqlite.close();
    await pg.end();
    console.log('Migration complete!');
}

migrate().catch(console.error);
```
