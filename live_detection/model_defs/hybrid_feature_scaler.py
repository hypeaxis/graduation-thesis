import os
import joblib
import numpy as np

class HybridFeatureScaler:
    """
    Class quản lý Pipeline chuẩn hóa dữ liệu kết hợp (Hybrid):
    - scaler_77: Dùng cho 77 feature gốc (Frozen, KHÔNG re-fit).
    - scaler_3custom: Dùng cho 3 feature mới (Trainable, ĐƯỢC re-fit).
    """
    
    def __init__(self, scaler_77_path=None, scaler_3custom_path=None):
        self.scaler_77 = None
        self.scaler_3custom = None
        self.fit_stats_3custom = {} # Lưu Mean/Std để detect Data Drift
        self.version = "v4.0"
        
        if scaler_77_path and os.path.exists(scaler_77_path):
            self.scaler_77 = joblib.load(scaler_77_path)
        
        if scaler_3custom_path and os.path.exists(scaler_3custom_path):
            self.scaler_3custom = joblib.load(scaler_3custom_path)

    def load_from_pipeline(self, pipeline_path):
        """Load từ file pipeline cũ (dictionary chứa 2 scaler)"""
        pipeline = joblib.load(pipeline_path)
        self.scaler_77 = pipeline['scaler_77_original']
        self.scaler_3custom = pipeline['scaler_3_new']
        # Compute dummy fit stats if missing
        self.fit_stats_3custom = {
            'mean': np.zeros(3),
            'std': np.ones(3)
        }

    def fit_custom_scaler(self, X_new):
        """
        CHỈ fit scaler cho 3 feature mới. 
        X_new là mảng numpy chỉ chứa 3 cột feature cuối cùng.
        """
        if self.scaler_77 is None:
            raise ValueError("Chưa load scaler_77. Không được phép fit scaler_3custom nếu thiếu phần core.")
        
        # PowerTransformer (nếu muốn) hoặc MinMaxScaler
        from sklearn.preprocessing import PowerTransformer
        self.scaler_3custom = PowerTransformer()
        self.scaler_3custom.fit(X_new)
        
        # Lưu lại thống kê để check drift sau này
        self.fit_stats_3custom = {
            'mean': np.mean(X_new, axis=0),
            'std': np.std(X_new, axis=0)
        }
        print(f"[*] Đã fit xong scaler cho 3 custom features.")

    def transform(self, X):
        """
        Chuẩn hóa batch X (N x 80).
        Tự động tách 77 và 3, transform rồi ghép lại.
        """
        if X.shape[1] != 80:
            raise ValueError(f"Input X phải có đúng 80 features. (Nhận được {X.shape[1]})")
            
        X_old = X[:, :77]
        X_new = X[:, 77:]
        
        X_old_scaled = self.scaler_77.transform(X_old)
        X_new_scaled = self.scaler_3custom.transform(X_new)
        
        return np.hstack((X_old_scaled, X_new_scaled))

    def save(self, output_path):
        """Lưu toàn bộ class instance ra file joblib"""
        # Cập nhật format dict để tương thích code inference cũ nếu cần, 
        # Hoặc lưu trực tiếp object class này.
        data = {
            'scaler_77_original': self.scaler_77,
            'scaler_3_new': self.scaler_3custom,
            'fit_stats_3custom': self.fit_stats_3custom,
            'version': self.version
        }
        joblib.dump(data, output_path)
        print(f"[+] Đã lưu HybridFeatureScaler tại: {output_path}")

    @classmethod
    def load(cls, filepath):
        """Load từ file đã save()"""
        data = joblib.load(filepath)
        obj = cls()
        obj.scaler_77 = data['scaler_77_original']
        obj.scaler_3custom = data['scaler_3_new']
        obj.fit_stats_3custom = data.get('fit_stats_3custom', {})
        obj.version = data.get('version', 'unknown')
        return obj
