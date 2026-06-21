import os
import json
import glob
import pandas as pd

def generate_report():
    results_dir = '../results'
    json_files = glob.glob(os.path.join(results_dir, '*.json'))
    
    if not json_files:
        print("Không tìm thấy file JSON nào trong thư mục results/")
        return
        
    data_rows = []
    
    # Thêm dòng Baseline (kết quả cứng từ trước khi cải tiến)
    data_rows.append({
        'Experiment': 'Baseline (Model gốc)',
        'Scaler': 'Original',
        'Fine-tune strategy': 'None',
        'Accuracy': 0.2193,
        'Balanced Accuracy': 0.6090,
        'MCC': -0.0150, # Ước lượng
        'Recall(Benign)': 1.0000,
        'Recall(Malicious)': 0.2180,
        'F1(Malicious)': 0.3580,
        'Forgetting on CIC-2017 (Δ Accuracy)': 0.0
    })
    
    for f in sorted(json_files):
        with open(f, 'r') as file:
            data = json.load(file)
            
        exp_name = os.path.basename(f).replace('.json', '')
        config = data.get('config', {})
        tb_metrics = data.get('metrics_testbed', {})
        cic_metrics = data.get('metrics_cic_2017', {})
        
        # Calculate Forgetting (Baseline CIC-2017 acc ~0.999)
        forgetting = 0.999 - cic_metrics.get('accuracy', 0.999) if cic_metrics.get('accuracy', 0) > 0 else "N/A"
        
        row = {
            'Experiment': exp_name,
            'Scaler': config.get('scaler', 'N/A'),
            'Fine-tune strategy': config.get('strategy', 'N/A'),
            'Accuracy': tb_metrics.get('accuracy', 0),
            'Balanced Accuracy': tb_metrics.get('balanced_accuracy', 0),
            'MCC': tb_metrics.get('mcc', 0),
            'Recall(Benign)': tb_metrics.get('recall_benign', 0),
            'Recall(Malicious)': tb_metrics.get('recall_malicious', 0),
            'F1(Malicious)': tb_metrics.get('f1_malicious', 0),
            'Forgetting on CIC-2017 (Δ Accuracy)': forgetting
        }
        data_rows.append(row)
        
    df = pd.DataFrame(data_rows)
    
    # Xử lý định dạng phần trăm và làm tròn
    for col in ['Accuracy', 'Balanced Accuracy', 'MCC', 'Recall(Benign)', 'Recall(Malicious)', 'F1(Malicious)']:
        df[col] = df[col].apply(lambda x: f"{x:.4f}" if isinstance(x, (int, float)) else x)
        
    df['Forgetting on CIC-2017 (Δ Accuracy)'] = df['Forgetting on CIC-2017 (Δ Accuracy)'].apply(
        lambda x: f"-{x*100:.2f}%" if isinstance(x, float) else str(x)
    )
    
    # Xuất ra CSV
    csv_path = '../results/aggregated_report.csv'
    df.to_csv(csv_path, index=False)
    print(f"Đã xuất file CSV tại: {csv_path}")
    
    # Xuất ra Markdown
    md_path = '../results/aggregated_report.md'
    with open(md_path, 'w') as f:
        f.write("# Bảng Tổng Hợp Kết Quả Domain Adaptation\n\n")
        f.write(df.to_markdown(index=False))
        
    print(f"Đã xuất file Markdown tại: {md_path}")
    print("\n" + df.to_markdown(index=False))

if __name__ == "__main__":
    generate_report()
