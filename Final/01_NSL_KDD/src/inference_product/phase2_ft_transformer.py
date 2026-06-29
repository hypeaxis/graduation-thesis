from __future__ import annotations

from typing import Iterable, List, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    def __init__(self, gamma: float = 2.0, alpha: float | Iterable[float] = 0.25, num_classes: int = 15) -> None:
        super().__init__()
        self.gamma = gamma
        self.num_classes = num_classes

        if isinstance(alpha, (float, int)):
            alpha_tensor = torch.full((num_classes,), float(alpha), dtype=torch.float32)
        else:
            alpha_tensor = torch.tensor(list(alpha), dtype=torch.float32)
            if alpha_tensor.numel() != num_classes:
                raise ValueError(f"alpha must have {num_classes} values, got {alpha_tensor.numel()}")

        self.register_buffer('alpha', alpha_tensor)

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if inputs.ndim != 2:
            raise ValueError(f"inputs must have shape (batch, classes), got {tuple(inputs.shape)}")
        if targets.ndim != 1:
            raise ValueError(f"targets must have shape (batch,), got {tuple(targets.shape)}")

        log_probs = F.log_softmax(inputs, dim=1)
        probs = log_probs.exp()

        targets = targets.long()
        log_pt = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        pt = probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        alpha_t = self.alpha.to(inputs.device).gather(0, targets)

        loss = -alpha_t * torch.pow(1.0 - pt, self.gamma) * log_pt
        return loss.mean()


class LabelSmoothingFocalLoss(nn.Module):
    """Focal Loss with label smoothing for better generalization."""

    def __init__(
        self,
        gamma: float = 2.0,
        alpha: float | Iterable[float] = 0.25,
        num_classes: int = 5,
        smoothing: float = 0.1,
    ) -> None:
        super().__init__()
        self.gamma = gamma
        self.num_classes = num_classes
        self.smoothing = smoothing

        if isinstance(alpha, (float, int)):
            alpha_tensor = torch.full((num_classes,), float(alpha), dtype=torch.float32)
        else:
            alpha_tensor = torch.tensor(list(alpha), dtype=torch.float32)
            if alpha_tensor.numel() != num_classes:
                raise ValueError(f"alpha must have {num_classes} values, got {alpha_tensor.numel()}")

        self.register_buffer('alpha', alpha_tensor)

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if inputs.ndim != 2:
            raise ValueError(f"inputs must have shape (batch, classes), got {tuple(inputs.shape)}")
        if targets.ndim != 1:
            raise ValueError(f"targets must have shape (batch,), got {tuple(targets.shape)}")

        log_probs = F.log_softmax(inputs, dim=1)
        probs = log_probs.exp()

        targets = targets.long()

        # Build smoothed target distribution
        smooth_targets = torch.full_like(log_probs, self.smoothing / (self.num_classes - 1))
        smooth_targets.scatter_(1, targets.unsqueeze(1), 1.0 - self.smoothing)

        # pt under smoothed distribution
        pt = (smooth_targets * probs).sum(dim=1).clamp(min=1e-8, max=1.0)
        log_pt = (smooth_targets * log_probs).sum(dim=1)

        alpha_t = self.alpha.to(inputs.device).gather(0, targets)
        loss = -alpha_t * torch.pow(1.0 - pt, self.gamma) * log_pt
        return loss.mean()


# ---------------------------------------------------------------------------
# Feature Embeddings
# ---------------------------------------------------------------------------

class FeatureEmbedding(nn.Module):
    """Original per-feature linear projection (v1 – kept for backward compat)."""

    def __init__(self, num_features: int, d_model: int) -> None:
        super().__init__()
        self.num_features = num_features
        self.d_model = d_model
        self.feature_projections = nn.ModuleList([nn.Linear(1, d_model) for _ in range(num_features)])
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.normal_(self.cls_token, mean=0.0, std=0.02)
        for projection in self.feature_projections:
            nn.init.xavier_uniform_(projection.weight)
            nn.init.zeros_(projection.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 2:
            raise ValueError(f"x must have shape (batch, num_features), got {tuple(x.shape)}")
        if x.shape[1] != self.num_features:
            raise ValueError(f"expected {self.num_features} features, got {x.shape[1]}")

        feature_tokens = [
            projection(x[:, index:index + 1])
            for index, projection in enumerate(self.feature_projections)
        ]
        tokens = torch.stack(feature_tokens, dim=1)
        cls = self.cls_token.expand(x.size(0), -1, -1)
        return torch.cat([cls, tokens], dim=1)


# Default NSL-KDD 122-feature group layout:
#   38 numeric features (indices 0-37)
#   3  protocol_type one-hot (indices 38-40)
#   70 service one-hot (indices 41-110)
#   11 flag one-hot (indices 111-121)
DEFAULT_FEATURE_GROUPS: List[Tuple[str, int, int]] = [
    ('numeric', 0, 38),
    ('protocol', 38, 41),
    ('service', 41, 111),
    ('flag', 111, 122),
]


class FeatureGroupEmbedding(nn.Module):
    """Project feature groups with shared linear layers → fewer tokens for attention.

    Instead of 122 individual tokens, we produce len(groups) tokens (default 4)
    plus a CLS token → attention matrix shrinks from 123×123 to 5×5.
    """

    def __init__(
        self,
        d_model: int,
        feature_groups: List[Tuple[str, int, int]] | None = None,
    ) -> None:
        super().__init__()
        if feature_groups is None:
            feature_groups = DEFAULT_FEATURE_GROUPS

        self.feature_groups = feature_groups
        self.d_model = d_model
        total_features = max(end for _, _, end in feature_groups)
        self.num_features = total_features

        self.group_projections = nn.ModuleList()
        for _name, start, end in feature_groups:
            dim_in = end - start
            self.group_projections.append(
                nn.Sequential(
                    nn.Linear(dim_in, d_model),
                    nn.LayerNorm(d_model),
                    nn.GELU(),
                )
            )

        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.normal_(self.cls_token, mean=0.0, std=0.02)
        for proj in self.group_projections:
            nn.init.xavier_uniform_(proj[0].weight)
            nn.init.zeros_(proj[0].bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 2:
            raise ValueError(f"x must have shape (batch, num_features), got {tuple(x.shape)}")

        tokens = []
        for idx, (_name, start, end) in enumerate(self.feature_groups):
            group_input = x[:, start:end]
            tokens.append(self.group_projections[idx](group_input))

        tokens = torch.stack(tokens, dim=1)  # (B, num_groups, d_model)
        cls = self.cls_token.expand(x.size(0), -1, -1)
        return torch.cat([cls, tokens], dim=1)  # (B, 1+num_groups, d_model)


# ---------------------------------------------------------------------------
# Transformer blocks
# ---------------------------------------------------------------------------

class MultiHeadSelfAttention(nn.Module):
    def __init__(self, d_model: int, num_heads: int, dropout: float = 0.1) -> None:
        super().__init__()
        if d_model % num_heads != 0:
            raise ValueError('d_model must be divisible by num_heads')

        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

        self.w_q = nn.Linear(d_model, d_model)
        self.w_k = nn.Linear(d_model, d_model)
        self.w_v = nn.Linear(d_model, d_model)
        self.w_o = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, seq_len, _ = x.shape

        q = self.w_q(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        k = self.w_k(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        v = self.w_v(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)

        scores = torch.matmul(q, k.transpose(-2, -1)) / (self.d_k ** 0.5)
        attention = torch.softmax(scores, dim=-1)
        attention = self.dropout(attention)

        attended = torch.matmul(attention, v)
        attended = attended.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)
        return self.w_o(attended)


class TransformerBlock(nn.Module):
    def __init__(self, d_model: int, num_heads: int, d_ff: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.attention = MultiHeadSelfAttention(d_model, num_heads, dropout)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
        )
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.dropout(self.attention(self.norm1(x)))
        x = x + self.dropout(self.ffn(self.norm2(x)))
        return x


# ---------------------------------------------------------------------------
# Model classes
# ---------------------------------------------------------------------------

class FTTransformer(nn.Module):
    """Original v1 FT-Transformer (kept for backward compat / checkpoint loading)."""

    def __init__(
        self,
        num_features: int,
        num_classes: int,
        d_model: int = 128,
        num_heads: int = 8,
        num_layers: int = 4,
        d_ff: int = 512,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.num_features = num_features
        self.num_classes = num_classes

        self.feature_embedding = FeatureEmbedding(num_features, d_model)
        self.embedding_dropout = nn.Dropout(dropout)
        self.transformer_blocks = nn.ModuleList(
            [TransformerBlock(d_model, num_heads, d_ff, dropout) for _ in range(num_layers)]
        )
        self.final_norm = nn.LayerNorm(d_model)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        cls_embeddings = self.get_embeddings(x)
        return self.classifier(cls_embeddings)

    def get_embeddings(self, x: torch.Tensor) -> torch.Tensor:
        x = self.feature_embedding(x)
        x = self.embedding_dropout(x)

        for block in self.transformer_blocks:
            x = block(x)

        x = self.final_norm(x)
        return x[:, 0, :]


class FTTransformerV2(nn.Module):
    """Improved FT-Transformer v2 with grouped feature embedding and deeper classifier."""

    def __init__(
        self,
        num_features: int,
        num_classes: int,
        d_model: int = 192,
        num_heads: int = 8,
        num_layers: int = 4,
        d_ff: int = 512,
        dropout: float = 0.15,
        feature_groups: List[Tuple[str, int, int]] | None = None,
        use_grouped_embedding: bool = True,
    ) -> None:
        super().__init__()
        self.num_features = num_features
        self.num_classes = num_classes

        if use_grouped_embedding:
            self.feature_embedding = FeatureGroupEmbedding(d_model, feature_groups)
        else:
            self.feature_embedding = FeatureEmbedding(num_features, d_model)

        self.embedding_dropout = nn.Dropout(dropout)
        self.transformer_blocks = nn.ModuleList(
            [TransformerBlock(d_model, num_heads, d_ff, dropout) for _ in range(num_layers)]
        )
        self.final_norm = nn.LayerNorm(d_model)

        # Deeper classifier head with BatchNorm for better minority-class performance
        self.classifier = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.BatchNorm1d(d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, d_model // 2),
            nn.BatchNorm1d(d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(d_model // 2, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        cls_embeddings = self.get_embeddings(x)
        return self.classifier(cls_embeddings)

    def get_embeddings(self, x: torch.Tensor) -> torch.Tensor:
        x = self.feature_embedding(x)
        x = self.embedding_dropout(x)

        for block in self.transformer_blocks:
            x = block(x)

        x = self.final_norm(x)
        return x[:, 0, :]