from __future__ import annotations

from typing import Iterable, List, Union

import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    def __init__(self, gamma: float = 2.0, alpha: Union[float, Iterable[float]] = 0.25, num_classes: int = 5) -> None:
        super().__init__()
        self.gamma = gamma
        if isinstance(alpha, (float, int)):
            alpha_tensor = torch.full((num_classes,), float(alpha), dtype=torch.float32)
        else:
            alpha_tensor = torch.tensor(list(alpha), dtype=torch.float32)
        self.register_buffer('alpha', alpha_tensor)

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        log_probs = F.log_softmax(inputs, dim=1)
        probs = log_probs.exp()
        targets = targets.long()
        log_pt = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        pt = probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        alpha_t = self.alpha.to(inputs.device).gather(0, targets)
        return (-alpha_t * (1.0 - pt).pow(self.gamma) * log_pt).mean()


class NumericFeatureTokenizer(nn.Module):
    def __init__(self, num_numeric_features: int, d_model: int) -> None:
        super().__init__()
        self.num_numeric_features = num_numeric_features
        self.projections = nn.ModuleList([nn.Linear(1, d_model) for _ in range(num_numeric_features)])
        for projection in self.projections:
            nn.init.xavier_uniform_(projection.weight)
            nn.init.zeros_(projection.bias)

    def forward(self, x_numeric: torch.Tensor) -> torch.Tensor:
        tokens = [projection(x_numeric[:, index:index + 1]) for index, projection in enumerate(self.projections)]
        return torch.stack(tokens, dim=1)


class TabularTransformer41Emb(nn.Module):
    def __init__(
        self,
        num_numeric_features: int,
        categorical_cardinalities: List[int],
        num_classes: int,
        d_model: int = 128,
        num_heads: int = 8,
        num_layers: int = 4,
        d_ff: int = 512,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.num_numeric_features = num_numeric_features
        self.categorical_cardinalities = categorical_cardinalities
        self.num_classes = num_classes

        self.numeric_tokenizer = NumericFeatureTokenizer(num_numeric_features, d_model)
        self.categorical_embeddings = nn.ModuleList([
            nn.Embedding(cardinality, d_model) for cardinality in categorical_cardinalities
        ])
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        nn.init.normal_(self.cls_token, mean=0.0, std=0.02)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=num_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            batch_first=True,
            activation='gelu',
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.final_norm = nn.LayerNorm(d_model)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, num_classes),
        )

    def forward(self, x_numeric: torch.Tensor, x_categorical: torch.Tensor) -> torch.Tensor:
        numeric_tokens = self.numeric_tokenizer(x_numeric)
        categorical_tokens = [
            embedding(x_categorical[:, index])
            for index, embedding in enumerate(self.categorical_embeddings)
        ]
        categorical_tokens = torch.stack(categorical_tokens, dim=1)
        cls_token = self.cls_token.expand(x_numeric.size(0), -1, -1)

        tokens = torch.cat([cls_token, numeric_tokens, categorical_tokens], dim=1)
        tokens = self.transformer(tokens)
        cls_embedding = self.final_norm(tokens[:, 0, :])
        return self.classifier(cls_embedding)