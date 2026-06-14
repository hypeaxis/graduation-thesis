import torch
import sys

path = "/home/ning/Graduation-Thesis/best_model (1).pt"
try:
    ckpt = torch.load(path, map_location='cpu')
    print("Checkpoint Keys:", ckpt.keys())
    if 'model_state_dict' in ckpt:
        sd = ckpt['model_state_dict']
    else:
        sd = ckpt
    
    # Check shape of feature embedding and classifier
    embed_shape = sd.get('feature_embedding.feature_proj.weight', None)
    if embed_shape is not None:
        print("Feature embedding shape:", embed_shape.shape)
    else:
        print("Keys in state_dict (first 10):", list(sd.keys())[:10])
        
    cls_weight = [v.shape for k, v in sd.items() if 'classifier' in k and 'weight' in k]
    if cls_weight:
        print("Classifier shapes:", cls_weight)
        
    print("Epoch:", ckpt.get('epoch', 'N/A'))
    print("Val F1:", ckpt.get('val_f1', 'N/A'))
except Exception as e:
    print("Error:", e)
