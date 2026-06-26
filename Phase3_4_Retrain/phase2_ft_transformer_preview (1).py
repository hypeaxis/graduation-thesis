"""
FT-Transformer (Feature Tokenizer Transformer) — Architecture Preview
======================================================================
This file is a **structural preview only**. All implementation bodies have
been replaced with stubs. It exists to let collaborators review the design
(class hierarchy, data-flow, hyperparameter choices) without exposing the
full source.

Full training & inference code is not included.
"""

from __future__ import annotations
import torch
import torch.nn as nn


# ---------------------------------------------------------------------------
# Loss
# ---------------------------------------------------------------------------

class FocalLoss(nn.Module):
    """
    Focal Loss for extreme class imbalance in network intrusion data.

    Formula:  FL(p_t) = -α_t · (1 − p_t)^γ · log(p_t)

    Args:
        gamma (float): Focusing exponent γ. Larger values down-weight
                       easy / well-classified examples more aggressively.
                       γ = 2.0 recommended for NIDS.
        alpha (float | list[float]): Per-class prior-probability weight α.
                       Scalar → same weight for all classes (default 0.25).
        num_classes (int): Number of output classes.
    """

    def __init__(self, gamma: float = 2.0, alpha: float = 0.25, num_classes: int = 15) -> None:
        super().__init__()
        self.gamma = gamma
        self.num_classes = num_classes
        # alpha stored as a (num_classes,) tensor; device-moved lazily in forward
        ...

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            inputs:  Raw logits,  shape (B, C)
            targets: Class indices, shape (B,)
        Returns:
            Scalar mean focal loss.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Feature Tokenization
# ---------------------------------------------------------------------------

class FeatureEmbedding(nn.Module):
    """
    Converts each scalar feature into a learned d_model-dimensional token.

    Each of the N input features receives its own independent Linear(1 → d_model)
    projection, producing N feature tokens.  A learnable [CLS] token is prepended,
    giving a sequence of length N + 1.

    Args:
        num_features (int): Number of scalar input features (77 for CIC-IDS2017).
        d_model (int):      Token / embedding dimensionality.
    """

    def __init__(self, num_features: int, d_model: int) -> None:
        super().__init__()
        self.num_features = num_features
        self.d_model = d_model
        # num_features independent Linear(1, d_model) projections
        # + 1 learnable CLS parameter of shape (1, 1, d_model)
        ...

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Raw tabular features, shape (B, num_features)
        Returns:
            Token sequence, shape (B, num_features + 1, d_model)
            Token 0 is [CLS]; tokens 1..N are feature tokens.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Attention
# ---------------------------------------------------------------------------

class MultiHeadSelfAttention(nn.Module):
    """
    Standard scaled dot-product multi-head self-attention.

    Learns pairwise interactions between feature tokens so the model can
    capture, e.g., that high packet-length variance *combined with* short
    inter-arrival time is diagnostic for a specific attack class.

    Args:
        d_model   (int):   Total embedding dimension.
        num_heads (int):   Number of attention heads (must divide d_model).
        dropout   (float): Attention-weight dropout probability.
    """

    def __init__(self, d_model: int, num_heads: int, dropout: float = 0.1) -> None:
        super().__init__()
        assert d_model % num_heads == 0, "d_model must be divisible by num_heads"
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        # W_q, W_k, W_v: Linear(d_model, d_model) each
        # W_o: Linear(d_model, d_model) output projection
        # dropout layer
        ...

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Token sequence, shape (B, L, d_model)
        Returns:
            Attended sequence, same shape (B, L, d_model)
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Transformer Block
# ---------------------------------------------------------------------------

class TransformerBlock(nn.Module):
    """
    Pre-norm Transformer encoder block.

    Data flow (single block):
        x  →  LayerNorm  →  MHSA  →  (+residual)  →  x'
        x' →  LayerNorm  →  FFN   →  (+residual)  →  output

    FFN structure:  Linear(d_model → d_ff) → GELU → Dropout → Linear(d_ff → d_model)

    Args:
        d_model   (int):   Embedding dimension.
        num_heads (int):   Attention heads.
        d_ff      (int):   Feed-forward hidden dimension (typically 4 × d_model).
        dropout   (float): Applied after attention and inside FFN.
    """

    def __init__(self, d_model: int, num_heads: int, d_ff: int, dropout: float = 0.1) -> None:
        super().__init__()
        # attention: MultiHeadSelfAttention(d_model, num_heads, dropout)
        # ffn: Sequential(Linear, GELU, Dropout, Linear)
        # norm1, norm2: LayerNorm(d_model)
        # dropout: Dropout(dropout)
        ...

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Token sequence, shape (B, L, d_model)
        Returns:
            Transformed sequence, same shape (B, L, d_model)
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Top-level model
# ---------------------------------------------------------------------------

class FTTransformer(nn.Module):
    """
    Feature Tokenizer Transformer (FT-Transformer) for tabular NIDS classification.

    End-to-end architecture
    -----------------------
    Input (B, F)
      └─ FeatureEmbedding           → (B, F+1, d_model)   # F feature tokens + [CLS]
          └─ TransformerBlock × L   → (B, F+1, d_model)   # L stacked encoder blocks
              └─ CLS token slice    → (B, d_model)         # token 0 only
                  └─ Classifier     → (B, num_classes)     # 2-layer MLP head

    Classifier head:
        Linear(d_model, d_model) → GELU → Dropout → Linear(d_model, num_classes)

    Trained configuration (CIC-IDS2017, 15-class):
        num_features = 77,  num_classes = 15
        d_model = 128,  num_heads = 8,  num_layers = 4,  d_ff = 512
        Total trainable parameters: ~831 K

    Args:
        num_features (int):   Number of tabular input features.
        num_classes  (int):   Number of target classes.
        d_model      (int):   Embedding / token dimension.         Default: 128
        num_heads    (int):   Attention heads per block.           Default: 8
        num_layers   (int):   Number of stacked Transformer blocks. Default: 4
        d_ff         (int):   FFN hidden dimension.                Default: 512
        dropout      (float): Global dropout rate.                 Default: 0.1
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
    ) -> None:
        super().__init__()
        self.num_features = num_features
        self.num_classes = num_classes
        # feature_embedding: FeatureEmbedding(num_features, d_model)
        # transformer_blocks: ModuleList of num_layers TransformerBlock instances
        # classifier: Sequential 2-layer MLP on [CLS] token
        ...

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Full classification forward pass.

        Args:
            x: Raw tabular features, shape (B, num_features)
        Returns:
            Class logits, shape (B, num_classes)
        """
        raise NotImplementedError

    def get_embeddings(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extract the [CLS] embedding without applying the classification head.
        Used downstream by the OpenMax open-set detector.

        Args:
            x: Raw tabular features, shape (B, num_features)
        Returns:
            CLS embeddings, shape (B, d_model)
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Quick architecture sanity-check  (shapes only — no real forward pass)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("FT-Transformer architecture preview")
    print("All forward() methods are stubs — this file is for design review only.\n")

    model = FTTransformer(num_features=77, num_classes=15)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  d_model={model.num_features}, num_classes={model.num_classes}")
    print(f"  Declared parameters: {total_params:,}  (stubs → 0 until implemented)")
    print("\nClass hierarchy:")
    print("  FocalLoss           (nn.Module)")
    print("  FeatureEmbedding    (nn.Module)  — feature tokenization")
    print("  MultiHeadSelfAttention (nn.Module)")
    print("  TransformerBlock    (nn.Module)  — MHSA + FFN + LayerNorm × 2")
    print("  FTTransformer       (nn.Module)  — full model")
