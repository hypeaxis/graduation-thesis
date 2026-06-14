import math
import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Utility: DropPath (Stochastic Depth)
# ---------------------------------------------------------------------------
def drop_path(x, drop_prob: float = 0., training: bool = False, scale_by_keep: bool = True):
    """Drop paths (Stochastic Depth) per sample (when applied in main path of residual blocks)."""
    if drop_prob == 0. or not training:
        return x
    keep_prob = 1 - drop_prob
    shape = (x.shape[0],) + (1,) * (x.ndim - 1)  # work with diff dim tensors, not just 2D ConvNets
    random_tensor = x.new_empty(shape).bernoulli_(keep_prob)
    if keep_prob > 0.0 and scale_by_keep:
        random_tensor.div_(keep_prob)
    return x * random_tensor

class DropPath(nn.Module):
    """Drop paths (Stochastic Depth) per sample."""
    def __init__(self, drop_prob: float = 0., scale_by_keep: bool = True):
        super(DropPath, self).__init__()
        self.drop_prob = drop_prob
        self.scale_by_keep = scale_by_keep

    def forward(self, x):
        return drop_path(x, self.drop_prob, self.training, self.scale_by_keep)

# ---------------------------------------------------------------------------
# Focal Loss
# ---------------------------------------------------------------------------
class FocalLoss(nn.Module):
    """
    Focal Loss cho bài toán mất cân bằng dữ liệu cực độ.
    """
    def __init__(self, gamma: float = 2.0, alpha=None, num_classes: int = 15) -> None:
        super().__init__()
        self.gamma = gamma
        self.num_classes = num_classes
        
        if alpha is None:
            self.alpha = torch.ones(num_classes) / num_classes
        elif isinstance(alpha, (float, int)):
            self.alpha = torch.full((num_classes,), float(alpha))
        else:
            self.alpha = torch.tensor(alpha, dtype=torch.float32)

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        self.alpha = self.alpha.to(inputs.device)
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce_loss)
        alpha_t = self.alpha[targets]
        focal_loss = alpha_t * (1 - pt) ** self.gamma * ce_loss
        return focal_loss.mean()

# ---------------------------------------------------------------------------
# GEGLU Activation
# ---------------------------------------------------------------------------
class GEGLU(nn.Module):
    def forward(self, x):
        x, gate = x.chunk(2, dim=-1)
        return x * F.gelu(gate)

# ---------------------------------------------------------------------------
# Feature Tokenization
# ---------------------------------------------------------------------------
class FeatureEmbedding(nn.Module):
    """
    Mã hóa từng feature vô hướng (scalar) thành vector d_model.
    """
    def __init__(self, num_features: int, d_model: int) -> None:
        super().__init__()
        self.num_features = num_features
        self.d_model = d_model
        
        # Tạo N mạng Linear độc lập cho N features
        self.feature_embeddings = nn.ModuleList([
            nn.Linear(1, d_model) for _ in range(num_features)
        ])
        
        # Token [CLS] có thể học được
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        nn.init.trunc_normal_(self.cls_token, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, N = x.shape
        assert N == self.num_features, f"Expected {self.num_features} features, got {N}"
        
        # Embed từng feature
        tokens = []
        for i in range(self.num_features):
            feat = x[:, i:i+1] # Shape: (B, 1)
            token = self.feature_embeddings[i](feat) # Shape: (B, d_model)
            tokens.append(token.unsqueeze(1)) # Shape: (B, 1, d_model)
            
        x_emb = torch.cat(tokens, dim=1) # Shape: (B, N, d_model)
        
        # Ghép [CLS] token vào đầu
        cls_tokens = self.cls_token.expand(B, -1, -1)
        x_emb = torch.cat((cls_tokens, x_emb), dim=1) # Shape: (B, N+1, d_model)
        return x_emb

# ---------------------------------------------------------------------------
# Attention & Transformer Block
# ---------------------------------------------------------------------------
class MultiHeadSelfAttention(nn.Module):
    def __init__(self, d_model: int, num_heads: int, dropout: float = 0.1) -> None:
        super().__init__()
        assert d_model % num_heads == 0
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        
        self.qkv = nn.Linear(d_model, d_model * 3)
        self.proj = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, L, D = x.shape
        qkv = self.qkv(x).reshape(B, L, 3, self.num_heads, self.d_k).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        
        attn = (q @ k.transpose(-2, -1)) / math.sqrt(self.d_k)
        attn = attn.softmax(dim=-1)
        attn = self.dropout(attn)
        
        out = (attn @ v).transpose(1, 2).reshape(B, L, D)
        out = self.proj(out)
        return self.dropout(out)

class TransformerBlock(nn.Module):
    def __init__(self, d_model: int, num_heads: int, d_ff: int, dropout: float = 0.1, drop_path: float = 0.0) -> None:
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model)
        self.attn = MultiHeadSelfAttention(d_model, num_heads, dropout)
        self.drop_path1 = DropPath(drop_path) if drop_path > 0. else nn.Identity()
        
        # LayerScale parameters
        self.ls1 = nn.Parameter(torch.ones(d_model) * 1e-4)
        self.ls2 = nn.Parameter(torch.ones(d_model) * 1e-4)
        
        self.norm2 = nn.LayerNorm(d_model)
        # GEGLU nhân đôi đầu ra trước khi chunk, nên Linear đầu tiên cần * 2 d_ff
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff * 2),
            GEGLU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model)
        )
        self.drop_path2 = DropPath(drop_path) if drop_path > 0. else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.drop_path1(self.ls1 * self.attn(self.norm1(x)))
        x = x + self.drop_path2(self.ls2 * self.ffn(self.norm2(x)))
        return x

# ---------------------------------------------------------------------------
# FT-Transformer V2
# ---------------------------------------------------------------------------
class FTTransformer(nn.Module):
    """
    FT-Transformer V2: Phiên bản tối ưu với LayerScale, DropPath và GEGLU.
    """
    def __init__(
        self,
        num_features: int,
        num_classes: int,
        d_model: int = 128,
        num_heads: int = 8,
        num_layers: int = 4,
        d_ff: int = 512,
        dropout: float = 0.1,
        drop_path_rate: float = 0.1
    ) -> None:
        super().__init__()
        self.num_features = num_features
        self.num_classes = num_classes
        
        self.feature_embedding = FeatureEmbedding(num_features, d_model)
        
        # DropPath scheduling (tăng dần theo chiều sâu mạng)
        dpr = [x.item() for x in torch.linspace(0, drop_path_rate, num_layers)]
        
        self.transformer_blocks = nn.ModuleList([
            TransformerBlock(d_model, num_heads, d_ff, dropout, drop_path=dpr[i])
            for i in range(num_layers)
        ])
        
        self.norm = nn.LayerNorm(d_model)
        
        # Classifier Head (2-layer MLP)
        self.classifier = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.feature_embedding(x)
        for block in self.transformer_blocks:
            x = block(x)
        x = self.norm(x)
        cls_token = x[:, 0, :]
        logits = self.classifier(cls_token)
        return logits

    def get_embeddings(self, x: torch.Tensor) -> torch.Tensor:
        x = self.feature_embedding(x)
        for block in self.transformer_blocks:
            x = block(x)
        x = self.norm(x)
        return x[:, 0, :]

if __name__ == "__main__":
    print("Testing FT-Transformer V2 Architecture...")
    model = FTTransformer(num_features=80, num_classes=15)
    dummy_input = torch.randn(32, 80)
    out = model(dummy_input)
    print(f"Input shape: {dummy_input.shape}")
    print(f"Output shape: {out.shape}")
    print("Architecture built successfully!")
