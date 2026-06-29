import numpy as np
import logging

def check_drift(batch_new, fit_stats, feature_names=None, z_score_threshold=3.0):
    """
    Kiểm tra xem batch dữ liệu mới (batch_new) có phân phối lệch (drift) quá xa
    so với phân phối gốc (fit_stats) lúc huấn luyện hay không.
    
    Args:
        batch_new (np.ndarray): Mảng N x D (số sample x số features).
        fit_stats (dict): Dictionary chứa 'mean' và 'std' của tập train.
        feature_names (list): Danh sách tên các feature (để in log).
        z_score_threshold (float): Ngưỡng z-score trung bình để báo động.
        
    Returns:
        bool: True nếu phát hiện Drift, False nếu an toàn.
    """
    if 'mean' not in fit_stats or 'std' not in fit_stats:
        logging.warning("Không có thống kê Mean/Std lúc fit. Bỏ qua kiểm tra Drift.")
        return False
        
    train_mean = np.array(fit_stats['mean'])
    train_std = np.array(fit_stats['std']) + 1e-9 # Tránh chia cho 0
    
    # Tính Mean thực tế của batch mới
    batch_mean = np.mean(batch_new, axis=0)
    
    # Tính Z-Score của Mean lô mới so với phân phối gốc
    z_scores = np.abs((batch_mean - train_mean) / train_std)
    
    drift_detected = False
    for i, z in enumerate(z_scores):
        if z > z_score_threshold:
            feat_name = feature_names[i] if feature_names else f"Feature {i}"
            logging.warning(f"[DATA DRIFT ALARM] {feat_name} bị lệch nghiêm trọng: Z-Score = {z:.2f} (Ngưỡng: {z_score_threshold})")
            drift_detected = True
            
    return drift_detected
