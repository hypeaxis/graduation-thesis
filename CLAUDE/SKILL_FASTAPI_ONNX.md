# Cẩm nang Kỹ năng: FastAPI & ONNX Runtime (SKILL_FASTAPI_ONNX.md)

**Mục đích:** Đưa mô hình ML (Autoencoder + Transformer) lên production với độ trễ siêu thấp (< 10ms).

## 1. Tối ưu ONNX Runtime (ORT)
- Mô hình phải được export sang ONNX với **Dynamic Axes** ở chiều `batch_size` để chịu tải khi bị flood attack.
- Cấu hình Session Options bật `GraphOptimizationLevel.ORT_ENABLE_ALL`.
- Giới hạn số luồng (threads) bằng số nhân vật lý để tránh overhead do context switching. Ưu tiên `CPUExecutionProvider`.

### Code mẫu: Export PyTorch sang ONNX
```python
import torch
import torch.onnx

def export_autoencoder_to_onnx(model, output_path="models/autoencoder.onnx"):
    model.eval()
    
    # Dummy input với dynamic batch size
    dummy_input = torch.randn(1, 122)  # batch=1, features=122
    
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output', 'reconstruction_error'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'},
            'reconstruction_error': {0: 'batch_size'}
        }
    )
    print(f"Model exported to {output_path}")

# Quantization INT8 để giảm size và tăng tốc
def quantize_model(model_path, output_path):
    from onnxruntime.quantization import quantize_dynamic, QuantType
    
    quantize_dynamic(
        model_path,
        output_path,
        weight_type=QuantType.QInt8
    )
    print(f"Quantized model saved to {output_path}")
```

## 2. Quản lý Vòng đời (Lifespan)
- **Quy tắc sống còn:** KHÔNG ĐƯỢC khởi tạo `InferenceSession` (load file .onnx) bên trong endpoint.
- Phải load mô hình 1 lần duy nhất khi FastAPI khởi động thông qua `lifespan`.
- Thực hiện **Warm-up**: Chạy thử một batch dữ liệu ảo (dummy numpy array) ngay lúc startup để đưa mô hình vào cache CPU.

### Code mẫu: FastAPI với Lifespan
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import onnxruntime as ort
import numpy as np

# Global model storage
models = {}

def load_onnx_model(model_path: str) -> ort.InferenceSession:
    """Load ONNX model với optimal settings"""
    sess_options = ort.SessionOptions()
    
    # Enable all optimizations
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    
    # Limit threads to physical cores
    sess_options.intra_op_num_threads = 4
    sess_options.inter_op_num_threads = 2
    
    # Enable memory pattern optimization
    sess_options.enable_mem_pattern = True
    sess_options.enable_cpu_mem_arena = True
    
    session = ort.InferenceSession(
        model_path,
        sess_options,
        providers=['CPUExecutionProvider']
    )
    
    return session

def warmup_model(session: ort.InferenceSession, input_name: str):
    """Warm-up để load model vào CPU cache"""
    dummy_input = np.zeros((1, 122), dtype=np.float32)
    for _ in range(10):  # Chạy 10 lần warm-up
        session.run(None, {input_name: dummy_input})
    print("Model warmed up successfully")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load models
    print("Loading ONNX models...")
    
    models['autoencoder'] = load_onnx_model("models/autoencoder.onnx")
    models['transformer'] = load_onnx_model("models/transformer.onnx")
    
    # Warm-up
    warmup_model(models['autoencoder'], 'input')
    warmup_model(models['transformer'], 'input')
    
    print("All models loaded and ready!")
    
    yield  # App is running
    
    # Shutdown: Cleanup
    models.clear()
    print("Models unloaded")

app = FastAPI(
    title="IDS Model API",
    version="1.0.0",
    lifespan=lifespan
)
```

## 3. Data Validation với Pydantic
- Mọi request đẩy vào `/predict` hoặc `/batch_predict` phải đi qua schema Pydantic.
- Xác thực chặt chẽ: Input phải là mảng `float` có độ dài chính xác 122 phần tử (tương ứng 122 features của NSL-KDD). Block ngay các request thiếu dữ liệu bằng mã lỗi 422.

### Code mẫu: Pydantic Schemas
```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal

class PredictRequest(BaseModel):
    features: List[float] = Field(
        ...,
        min_length=122,
        max_length=122,
        description="Vector 122 features NSL-KDD"
    )
    
    @field_validator('features')
    @classmethod
    def validate_features(cls, v):
        if len(v) != 122:
            raise ValueError(f"Expected 122 features, got {len(v)}")
        # Check for NaN/Inf
        for i, val in enumerate(v):
            if not (-1e10 < val < 1e10):
                raise ValueError(f"Feature {i} has invalid value: {val}")
        return v

class PredictResponse(BaseModel):
    label: Literal["Normal", "DoS", "Probe", "R2L", "U2R"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reconstruction_error: float
    processing_time_ms: float

class BatchPredictRequest(BaseModel):
    samples: List[List[float]] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Batch of feature vectors"
    )

class BatchPredictResponse(BaseModel):
    predictions: List[PredictResponse]
    total_time_ms: float

class HealthResponse(BaseModel):
    status: str
    models_loaded: List[str]
    uptime_seconds: float
```

## 4. Implement Endpoints

### Code mẫu: API Endpoints
```python
from fastapi import HTTPException
import numpy as np
import time

# Attack type mapping (từ model output index)
ATTACK_LABELS = ["Normal", "DoS", "Probe", "R2L", "U2R"]

# Threshold cho anomaly detection (tune based on validation set)
ANOMALY_THRESHOLD = 0.5

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        models_loaded=list(models.keys()),
        uptime_seconds=time.time() - app.state.start_time
    )

@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    start_time = time.perf_counter()
    
    try:
        # Prepare input
        input_array = np.array([request.features], dtype=np.float32)
        
        # Stage 1: Autoencoder (anomaly detection)
        ae_session = models['autoencoder']
        ae_input_name = ae_session.get_inputs()[0].name
        ae_outputs = ae_session.run(None, {ae_input_name: input_array})
        
        reconstruction = ae_outputs[0]
        reconstruction_error = float(np.mean((input_array - reconstruction) ** 2))
        
        # Stage 2: Transformer (classification) nếu là anomaly
        if reconstruction_error > ANOMALY_THRESHOLD:
            tf_session = models['transformer']
            tf_input_name = tf_session.get_inputs()[0].name
            tf_outputs = tf_session.run(None, {tf_input_name: input_array})
            
            class_probs = tf_outputs[0][0]
            predicted_class = int(np.argmax(class_probs))
            confidence = float(class_probs[predicted_class])
            label = ATTACK_LABELS[predicted_class]
        else:
            label = "Normal"
            confidence = 1.0 - reconstruction_error
        
        processing_time = (time.perf_counter() - start_time) * 1000
        
        return PredictResponse(
            label=label,
            confidence=confidence,
            reconstruction_error=reconstruction_error,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch_predict", response_model=BatchPredictResponse)
async def batch_predict(request: BatchPredictRequest):
    start_time = time.perf_counter()
    
    # Validate all samples
    for i, sample in enumerate(request.samples):
        if len(sample) != 122:
            raise HTTPException(
                status_code=422, 
                detail=f"Sample {i} has {len(sample)} features, expected 122"
            )
    
    # Batch inference
    input_array = np.array(request.samples, dtype=np.float32)
    
    ae_session = models['autoencoder']
    ae_outputs = ae_session.run(None, {ae_session.get_inputs()[0].name: input_array})
    
    reconstructions = ae_outputs[0]
    errors = np.mean((input_array - reconstructions) ** 2, axis=1)
    
    # Classify anomalies
    predictions = []
    anomaly_mask = errors > ANOMALY_THRESHOLD
    
    if np.any(anomaly_mask):
        anomaly_inputs = input_array[anomaly_mask]
        tf_session = models['transformer']
        tf_outputs = tf_session.run(None, {tf_session.get_inputs()[0].name: anomaly_inputs})
        class_probs = tf_outputs[0]
        anomaly_idx = 0
    
    for i in range(len(request.samples)):
        if anomaly_mask[i]:
            probs = class_probs[anomaly_idx]
            pred_class = int(np.argmax(probs))
            predictions.append(PredictResponse(
                label=ATTACK_LABELS[pred_class],
                confidence=float(probs[pred_class]),
                reconstruction_error=float(errors[i]),
                processing_time_ms=0
            ))
            anomaly_idx += 1
        else:
            predictions.append(PredictResponse(
                label="Normal",
                confidence=1.0 - float(errors[i]),
                reconstruction_error=float(errors[i]),
                processing_time_ms=0
            ))
    
    total_time = (time.perf_counter() - start_time) * 1000
    
    return BatchPredictResponse(
        predictions=predictions,
        total_time_ms=total_time
    )
```

## 5. Concurrency
- Chạy FastAPI bằng Uvicorn với nhiều workers (`--workers 4`) để tận dụng đa nhân CPU, nhưng cần theo dõi RAM vì mỗi worker sẽ load một bản sao của mô hình.

### Chạy Production Server
```bash
# Development (single worker, auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production (multiple workers)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Với Gunicorn (recommended for production)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 6. Error Handling & Logging

```python
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ids-model-api")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )

# Middleware để log request latency
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}ms"
    )
    
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    return response
```

## 7. Requirements.txt
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
onnxruntime==1.16.3
numpy==1.26.3
pydantic==2.5.3
```