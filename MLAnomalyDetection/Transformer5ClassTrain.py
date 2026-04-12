import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import json
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
import matplotlib.pyplot as plt
import seaborn as sns
import math

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super().__init__()
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * 
                           (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        
        self.register_buffer('pe', pe)
        
    def forward(self, x):
        return x + self.pe[:x.size(0), :]

class TabularTransformerClassifier(nn.Module):
    def __init__(self, input_dim, d_model=128, nhead=8, num_layers=4, 
                 num_classes=5, dropout=0.1):
        super().__init__()
        
        self.input_dim = input_dim
        self.d_model = d_model
        self.num_classes = num_classes
        
        # Feature embedding - treat each feature as a token
        self.feature_embedding = nn.Linear(1, d_model)
        
        # Positional encoding for features
        self.pos_encoding = PositionalEncoding(d_model, input_dim)
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=False  # (seq_len, batch, features)
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers)
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(d_model * input_dim, 512),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, num_classes)
        )
        
        # Alternative: Use attention pooling
        self.attention_pool = nn.Sequential(
            nn.Linear(d_model, 1),
            nn.Softmax(dim=0)
        )
        
        self.final_classifier = nn.Sequential(
            nn.Linear(d_model, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )
        
    def forward(self, x, use_attention_pool=True):
        # x shape: (batch_size, input_dim)
        batch_size, seq_len = x.shape
        
        # Treat each feature as a separate token
        x = x.unsqueeze(-1)  # (batch_size, input_dim, 1)
        x = x.transpose(0, 1)  # (input_dim, batch_size, 1)
        
        # Feature embedding
        x = self.feature_embedding(x)  # (input_dim, batch_size, d_model)
        
        # Add positional encoding
        x = self.pos_encoding(x)  # (input_dim, batch_size, d_model)
        
        # Apply transformer
        x = self.transformer_encoder(x)  # (input_dim, batch_size, d_model)
        
        if use_attention_pool:
            # Attention pooling
            attention_weights = self.attention_pool(x)  # (input_dim, batch_size, 1)
            x = torch.sum(x * attention_weights, dim=0)  # (batch_size, d_model)
            
            # Final classification
            output = self.final_classifier(x)  # (batch_size, num_classes)
        else:
            # Flatten and classify
            x = x.transpose(0, 1)  # (batch_size, input_dim, d_model)
            x = x.reshape(batch_size, -1)  # (batch_size, input_dim * d_model)
            output = self.classifier(x)  # (batch_size, num_classes)
        
        return output

class Transformer5ClassClassifier:
    def __init__(self, input_dim, d_model=128, nhead=8, num_layers=4, 
                 num_classes=5, dropout=0.1):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
        self.model = TabularTransformerClassifier(
            input_dim=input_dim,
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers,
            num_classes=num_classes,
            dropout=dropout
        ).to(self.device)
        
        self.scaler = MinMaxScaler()
        self.input_dim = input_dim
        self.num_classes = num_classes
        
    def fit(self, X_train, y_train, X_val=None, y_val=None, epochs=100, 
            batch_size=128, lr=0.001, use_class_weights=True, validation_split=0.2):
        """Train the Transformer model"""
        print("Preprocessing data...")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_train)
        
        # Handle validation split
        if X_val is None and validation_split > 0:
            from sklearn.model_selection import train_test_split
            X_scaled, X_val_scaled, y_train_split, y_val = train_test_split(
                X_scaled, y_train, test_size=validation_split, 
                stratify=y_train, random_state=42
            )
        elif X_val is not None:
            X_val_scaled = self.scaler.transform(X_val)
            y_train_split = y_train
        else:
            y_train_split = y_train
            X_val_scaled, y_val = None, None
        
        # Prepare data loaders
        train_dataset = torch.utils.data.TensorDataset(
            torch.FloatTensor(X_scaled), torch.LongTensor(y_train_split)
        )
        train_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True
        )
        
        if X_val_scaled is not None:
            val_dataset = torch.utils.data.TensorDataset(
                torch.FloatTensor(X_val_scaled), torch.LongTensor(y_val)
            )
            val_loader = torch.utils.data.DataLoader(
                val_dataset, batch_size=batch_size, shuffle=False
            )
        
        # Setup loss function with class weights
        if use_class_weights:
            class_weights = compute_class_weight(
                'balanced', classes=np.unique(y_train_split), y=y_train_split
            )
            class_weights = torch.FloatTensor(class_weights).to(self.device)
            criterion = nn.CrossEntropyLoss(weight=class_weights)
        else:
            criterion = nn.CrossEntropyLoss()
        
        # Setup optimizer
        optimizer = optim.Adam(self.model.parameters(), lr=lr, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=10
        )
        
        # Training loop
        train_losses = []
        val_losses = []
        train_accs = []
        val_accs = []
        
        print("Starting training...")
        for epoch in range(epochs):
            # Training phase
            self.model.train()
            total_train_loss = 0
            correct_train = 0
            total_train = 0
            
            for batch_x, batch_y in train_loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                
                optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                
                optimizer.step()
                
                total_train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total_train += batch_y.size(0)
                correct_train += (predicted == batch_y).sum().item()
            
            avg_train_loss = total_train_loss / len(train_loader)
            train_acc = 100 * correct_train / total_train
            
            train_losses.append(avg_train_loss)
            train_accs.append(train_acc)
            
            # Validation phase
            if X_val_scaled is not None:
                self.model.eval()
                total_val_loss = 0
                correct_val = 0
                total_val = 0
                
                with torch.no_grad():
                    for batch_x, batch_y in val_loader:
                        batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                        
                        outputs = self.model(batch_x)
                        loss = criterion(outputs, batch_y)
                        
                        total_val_loss += loss.item()
                        _, predicted = torch.max(outputs.data, 1)
                        total_val += batch_y.size(0)
                        correct_val += (predicted == batch_y).sum().item()
                
                avg_val_loss = total_val_loss / len(val_loader)
                val_acc = 100 * correct_val / total_val
                
                val_losses.append(avg_val_loss)
                val_accs.append(val_acc)
                
                scheduler.step(avg_val_loss)
                
                if epoch % 10 == 0:
                    print(f'Epoch {epoch:3d}: Train Loss={avg_train_loss:.4f}, '
                          f'Train Acc={train_acc:.2f}%, Val Loss={avg_val_loss:.4f}, '
                          f'Val Acc={val_acc:.2f}%')
            else:
                if epoch % 10 == 0:
                    print(f'Epoch {epoch:3d}: Train Loss={avg_train_loss:.4f}, '
                          f'Train Acc={train_acc:.2f}%')
        
        return {
            'train_losses': train_losses,
            'val_losses': val_losses,
            'train_accs': train_accs,
            'val_accs': val_accs
        }
    
    def predict(self, X_test):
        """Predict using the trained model"""
        X_scaled = self.scaler.transform(X_test)
        test_dataset = torch.utils.data.TensorDataset(torch.FloatTensor(X_scaled))
        test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=256, shuffle=False)
        
        predictions = []
        probabilities = []
        
        self.model.eval()
        with torch.no_grad():
            for (batch_x,) in test_loader:
                batch_x = batch_x.to(self.device)
                outputs = self.model(batch_x)
                probs = torch.softmax(outputs, dim=1)
                _, predicted = torch.max(outputs, 1)
                
                predictions.extend(predicted.cpu().numpy())
                probabilities.extend(probs.cpu().numpy())
        
        return np.array(predictions), np.array(probabilities)
    
    def evaluate(self, X_test, y_test):
        """Evaluate model performance"""
        predictions, probabilities = self.predict(X_test)
        
        class_names = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']
        report = classification_report(
            y_test, predictions,
            target_names=class_names,
            output_dict=True
        )
        
        print("=== Transformer 5-Class Classification Report ===")
        print(classification_report(y_test, predictions, target_names=class_names))
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, predictions)
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=class_names, yticklabels=class_names)
        plt.title('Transformer 5-Class Classification - Confusion Matrix')
        plt.ylabel('Actual')
        plt.xlabel('Predicted')
        plt.tight_layout()
        plt.savefig('transformer_5class_confusion_matrix.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return report, cm

def main():
    print("=== Transformer 5-Class Classification ===")
    
    # Load data
    train_df = pd.read_csv("cleaned5Grouped_v2_KddTrain+.csv")
    test_df = pd.read_csv("cleaned5Grouped_v2_KddTest+.csv")
    
    # Prepare data
    X_train = train_df.drop('label', axis=1).values
    y_train = train_df['label'].values
    X_test = test_df.drop('label', axis=1).values
    y_test = test_df['label'].values
    
    print(f"Training data shape: {X_train.shape}")
    print(f"Test data shape: {X_test.shape}")
    print(f"Number of features: {X_train.shape[1]}")
    
    # Initialize Transformer model
    transformer_model = Transformer5ClassClassifier(
        input_dim=X_train.shape[1],
        d_model=128,
        nhead=8,
        num_layers=6,
        num_classes=5,
        dropout=0.1
    )
    
    print("Training Transformer model...")
    history = transformer_model.fit(
        X_train, y_train,
        epochs=100,
        batch_size=256,
        lr=0.001,
        use_class_weights=True,
        validation_split=0.2
    )
    
    print("Evaluating model...")
    report, cm = transformer_model.evaluate(X_test, y_test)

    baseline_metrics = {
        'accuracy': report.get('accuracy', 0.0),
        'macro_f1': report.get('macro avg', {}).get('f1-score', 0.0),
        'weighted_f1': report.get('weighted avg', {}).get('f1-score', 0.0),
        'normal_f1': report.get('Normal', {}).get('f1-score', 0.0),
        'dos_f1': report.get('DoS', {}).get('f1-score', 0.0),
        'probe_f1': report.get('Probe', {}).get('f1-score', 0.0),
        'r2l_f1': report.get('R2L', {}).get('f1-score', 0.0),
        'u2r_f1': report.get('U2R', {}).get('f1-score', 0.0),
    }

    with open('transformer_v2_baseline_metrics.json', 'w', encoding='utf-8') as f:
        json.dump(baseline_metrics, f, ensure_ascii=True, indent=2)

    print('Saved baseline metrics to transformer_v2_baseline_metrics.json')
    
    # Plot training history
    plt.figure(figsize=(15, 5))
    
    plt.subplot(1, 3, 1)
    plt.plot(history['train_losses'], label='Training Loss')
    if history['val_losses']:
        plt.plot(history['val_losses'], label='Validation Loss')
    plt.title('Training Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    
    plt.subplot(1, 3, 2)
    plt.plot(history['train_accs'], label='Training Accuracy')
    if history['val_accs']:
        plt.plot(history['val_accs'], label='Validation Accuracy')
    plt.title('Training Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy (%)')
    plt.legend()
    
    plt.subplot(1, 3, 3)
    class_f1 = [
        baseline_metrics['normal_f1'],
        baseline_metrics['dos_f1'],
        baseline_metrics['probe_f1'],
        baseline_metrics['r2l_f1'],
        baseline_metrics['u2r_f1'],
    ]
    class_names = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']
    plt.bar(class_names, class_f1)
    plt.title('Per-Class F1 (Baseline v2)')
    plt.ylim(0, 1)
    plt.ylabel('F1-score')
    
    plt.tight_layout()
    plt.savefig('transformer_5class_training_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("Transformer 5-Class Classification Complete!")
    
    # Save model
    torch.save(transformer_model.model.state_dict(), 'transformer_5class_model.pth')
    print("Model saved!")

if __name__ == "__main__":
    main()