```markdown
# Cẩm nang Kỹ năng: Testing & Quality Assurance (SKILL_TESTING.md)

**Mục đích:** Hướng dẫn viết tests cho từng module, đảm bảo chất lượng code và phát hiện bugs sớm.

## 1. Tổng quan Testing Strategy

| Loại Test | Mục đích | Tools | Coverage Target |
|-----------|----------|-------|-----------------|
| Unit Test | Test từng function riêng lẻ | Python: pytest, JS: Jest | > 80% |
| Integration Test | Test giao tiếp giữa modules | pytest, supertest | Critical paths |
| End-to-End Test | Test toàn bộ luồng | Custom scripts, Snort log replay | Happy path + edge cases |
| Performance Test | Đo latency, throughput | wrk, ab, custom benchmarks | Meet SLAs |
| Security Test | Tìm vulnerabilities | OWASP ZAP, manual review | No critical issues |

---

## 2. Unit Testing cho Snort Parser Service

### 2.1 Setup Parser Test Framework
```bash
# Cài đặt framework test cho parser
pip install pytest pytest-cov

# Cấu trúc thư mục
/sniffer
├── parser/
│   ├── stream_parser.py
│   ├── feature_builder.py
│   └── schema.py
├── tests/
│   ├── test_stream_parser.py
│   ├── test_feature_builder.py
│   └── test_schema_validation.py
└── pytest.ini
```

### 2.2 Ví dụ Test Case
```c
// tests/test_packet_parser.c
#include <check.h>
#include "../src/packet_parser.h"

// Test parse IP header
START_TEST(test_parse_ipv4_header)
{
    // Raw bytes của một IPv4 header hợp lệ
    unsigned char raw_packet[] = {
        0x45, 0x00, 0x00, 0x3c, // Version, IHL, TOS, Total Length
        0x1c, 0x46, 0x40, 0x00, // ID, Flags, Fragment Offset
        0x40, 0x06, 0xb1, 0xe6, // TTL, Protocol (TCP=6), Checksum
        0xac, 0x10, 0x0a, 0x63, // Src IP: 172.16.10.99
        0xac, 0x10, 0x0a, 0x0c  // Dst IP: 172.16.10.12
    };
    
    ip_header_t header;
    int result = parse_ip_header(raw_packet, sizeof(raw_packet), &header);
    
    ck_assert_int_eq(result, 0);  // Success
    ck_assert_int_eq(header.version, 4);
    ck_assert_int_eq(header.protocol, 6);  // TCP
    ck_assert_str_eq(header.src_ip, "172.16.10.99");
    ck_assert_str_eq(header.dst_ip, "172.16.10.12");
}
END_TEST

// Test xử lý packet bị truncated
START_TEST(test_parse_truncated_packet)
{
    unsigned char truncated[] = {0x45, 0x00, 0x00};  // Chỉ 3 bytes
    ip_header_t header;
    
    int result = parse_ip_header(truncated, sizeof(truncated), &header);
    
    ck_assert_int_eq(result, -1);  // Should fail
}
END_TEST

// Test suite
Suite* packet_parser_suite(void)
{
    Suite *s = suite_create("PacketParser");
    TCase *tc_core = tcase_create("Core");
    
    tcase_add_test(tc_core, test_parse_ipv4_header);
    tcase_add_test(tc_core, test_parse_truncated_packet);
    suite_add_tcase(s, tc_core);
    
    return s;
}
```

### 2.3 Test với PCAP Files
```c
// Test replay từ file pcap thật
START_TEST(test_process_real_pcap)
{
    pcap_t *handle;
    char errbuf[PCAP_ERRBUF_SIZE];
    
    // Mở file pcap mẫu (download từ Wireshark samples)
    handle = pcap_open_offline("tests/samples/http_traffic.pcap", errbuf);
    ck_assert_ptr_nonnull(handle);
    
    int packet_count = 0;
    pcap_loop(handle, -1, count_callback, (u_char*)&packet_count);
    
    ck_assert_int_gt(packet_count, 0);  // Phải có ít nhất 1 packet
    pcap_close(handle);
}
END_TEST
```

### 2.4 Makefile cho Tests
```makefile
# Makefile
CC = gcc
CFLAGS = -Wall -g
LDFLAGS = -lpcap -lcheck -lsubunit -lm -lpthread -lrt

test: test_runner
	./test_runner

test_runner: tests/*.c src/*.c
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f test_runner *.o
```

---

## 3. Unit Testing cho Python (FastAPI)

### 3.1 Setup pytest
```bash
pip install pytest pytest-cov pytest-asyncio httpx
```

### 3.2 Test Model Inference
```python
# tests/test_model.py
import pytest
import numpy as np
from app.model import load_model, predict

@pytest.fixture
def model():
    """Load model một lần cho tất cả tests"""
    return load_model("models/autoencoder.onnx")

def test_model_loads_successfully(model):
    assert model is not None

def test_predict_normal_traffic(model):
    # Vector 122 chiều đại diện traffic bình thường
    normal_vector = np.zeros(122, dtype=np.float32)
    normal_vector[0] = 0.1  # duration normalized
    
    result = predict(model, normal_vector)
    
    assert result["label"] in ["Normal", "DoS", "Probe", "R2L", "U2R"]
    assert 0.0 <= result["confidence"] <= 1.0

def test_predict_batch(model):
    # Test batch prediction
    batch = np.random.rand(10, 122).astype(np.float32)
    
    results = predict(model, batch)
    
    assert len(results) == 10

def test_invalid_input_shape():
    """Test xử lý input sai format"""
    with pytest.raises(ValueError):
        predict(model, np.zeros(100))  # Sai số features
```

### 3.3 Test FastAPI Endpoints
```python
# tests/test_api.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_predict_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/predict",
            json={"features": [0.0] * 122}
        )
    
    assert response.status_code == 200
    assert "label" in response.json()
    assert "confidence" in response.json()

@pytest.mark.asyncio
async def test_predict_invalid_input():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/predict",
            json={"features": [0.0] * 100}  # Wrong size
        )
    
    assert response.status_code == 422  # Validation error
```

### 3.4 Chạy Tests với Coverage
```bash
# Chạy tất cả tests
pytest tests/ -v

# Với coverage report
pytest tests/ --cov=app --cov-report=html

# Chỉ chạy một file test
pytest tests/test_model.py -v
```

---

## 4. Unit Testing cho Node.js

### 4.1 Setup Jest
```bash
npm install --save-dev jest supertest
```

```json
// package.json
{
  "scripts": {
    "test": "jest --coverage",
    "test:watch": "jest --watch"
  }
}
```

### 4.2 Test TCP Parser
```javascript
// tests/tcpParser.test.js
const { parseJsonStream } = require('../src/tcpParser');

describe('TCP JSON Parser', () => {
  test('parses complete JSON message', () => {
    const buffer = '{"src_ip":"192.168.1.1","features":[0.1,0.2]}\n';
    const results = parseJsonStream(buffer);
    
    expect(results).toHaveLength(1);
    expect(results[0].src_ip).toBe('192.168.1.1');
  });

  test('handles fragmented messages', () => {
    // Simulate TCP fragmentation
    let buffer = '';
    const results1 = parseJsonStream('{"src_ip":"192.', buffer);
    expect(results1.messages).toHaveLength(0);
    
    const results2 = parseJsonStream('168.1.1"}\n', results1.remaining);
    expect(results2.messages).toHaveLength(1);
  });

  test('handles multiple messages in one chunk', () => {
    const buffer = '{"id":1}\n{"id":2}\n{"id":3}\n';
    const results = parseJsonStream(buffer);
    
    expect(results).toHaveLength(3);
  });
});
```

### 4.3 Test API Endpoints
```javascript
// tests/api.test.js
const request = require('supertest');
const app = require('../src/app');

describe('REST API', () => {
  test('GET /api/health returns 200', async () => {
    const response = await request(app).get('/api/health');
    
    expect(response.status).toBe(200);
    expect(response.body.status).toBe('ok');
  });

  test('GET /api/alerts returns array', async () => {
    const response = await request(app).get('/api/alerts');
    
    expect(response.status).toBe(200);
    expect(Array.isArray(response.body)).toBe(true);
  });

  test('GET /api/alerts with pagination', async () => {
    const response = await request(app)
      .get('/api/alerts')
      .query({ page: 1, limit: 10 });
    
    expect(response.status).toBe(200);
    expect(response.body.length).toBeLessThanOrEqual(10);
  });
});
```

---

## 5. End-to-End Testing

### 5.1 Script Test Luồng Hoàn chỉnh
```bash
#!/bin/bash
# e2e_test.sh - Test toàn bộ pipeline

set -e  # Exit on error

echo "=== Starting E2E Test ==="

# 1. Start all services
docker-compose up -d
sleep 10  # Wait for services to be ready

# 2. Check health endpoints
echo "Checking health..."
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:3000/api/health || exit 1

# 3. Replay pcap file và kiểm tra alerts
echo "Replaying attack traffic..."
tcpreplay -i eth0 tests/samples/dos_attack.pcap

# 4. Wait và check for alerts
sleep 5
ALERT_COUNT=$(curl -s http://localhost:3000/api/alerts | jq length)

if [ "$ALERT_COUNT" -gt 0 ]; then
    echo "✅ E2E Test PASSED: $ALERT_COUNT alerts detected"
else
    echo "❌ E2E Test FAILED: No alerts detected"
    exit 1
fi

# 5. Cleanup
docker-compose down
```

### 5.2 Test Matrix
| Scenario | Input | Expected Output | Priority |
|----------|-------|-----------------|----------|
| Normal HTTP browse | http_normal.pcap | 0 alerts | High |
| SYN Flood attack | syn_flood.pcap | DoS alerts | High |
| Port scan | nmap_scan.pcap | Probe alerts | High |
| SSH brute force | ssh_bruteforce.pcap | R2L alerts | Medium |
| Mixed traffic | mixed.pcap | Correct labels | High |

---

## 6. Performance Testing

### 6.1 Benchmark Model API
```bash
# Sử dụng wrk để benchmark
wrk -t4 -c100 -d30s -s benchmark.lua http://localhost:8000/predict

# benchmark.lua
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"
wrk.body = '{"features": [' .. string.rep("0.0,", 121) .. '0.0]}'
```

### 6.2 Stress Test Sniffer
```bash
# Tạo traffic flood để test giới hạn
hping3 --flood -p 80 localhost &

# Monitor packet drop rate
watch -n 1 'cat /proc/net/dev | grep eth0'
```

### 6.3 Performance Metrics to Track
| Metric | Target | Tool |
|--------|--------|------|
| Model inference latency | < 10ms (p99) | wrk, custom timer |
| End-to-end response time | < 500ms | tcpreplay + dashboard |
| Packets processed/sec | > 10,000 | custom counter |
| Memory usage (Sniffer) | < 500MB | htop, valgrind |
| CPU usage (Model API) | < 80% | docker stats |

---

## 7. Continuous Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Run Tests

on: [push, pull_request]

jobs:
  test-sniffer:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: sudo apt-get install -y snort
      - name: Run parser tests
        run: cd sniffer && pytest

  test-model:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r model/requirements.txt
      - name: Run pytest
        run: cd model && pytest --cov

  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd backend && npm ci
      - name: Run Jest
        run: cd backend && npm test
```

---

## 8. Test Data Resources

### PCAP Samples
- Wireshark Sample Captures: https://wiki.wireshark.org/SampleCaptures
- DARPA Intrusion Detection: https://www.ll.mit.edu/r-d/datasets
- CTU-13 Dataset: https://www.stratosphereips.org/datasets-ctu13

### Tạo Test Data
```python
# generate_test_vectors.py
import numpy as np
import json

# Generate normal traffic vectors
normal_vectors = np.random.uniform(0, 0.3, size=(100, 122))

# Generate attack-like vectors (high certain features)
dos_vectors = np.random.uniform(0.7, 1.0, size=(50, 122))
dos_vectors[:, 22] = 0.95  # High count (feature 23)
dos_vectors[:, 24] = 0.9   # High serror_rate (feature 25)

with open('test_vectors.json', 'w') as f:
    json.dump({
        'normal': normal_vectors.tolist(),
        'dos': dos_vectors.tolist()
    }, f)
```
```
