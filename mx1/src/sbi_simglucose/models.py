import torch
import torch.nn as nn

class CGMCnnEmbedding(nn.Module):
    """
    Lightweight 1D-CNN designed to extract temporal features from 
    288-step (24h) CGM data for SBI Normalizing Flows.
    """
    def __init__(self, output_dim: int = 32):
        super().__init__()
        self.output_dim = output_dim
        
        # Input shape expected from SBI: (Batch, 288)
        # We reshape to (Batch, Channels=1, 288) in forward
        
        self.conv_net = nn.Sequential(
            # layer 1
            nn.Conv1d(in_channels=1, out_channels=16, kernel_size=7, stride=2, padding=3),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2), # output roughly 288/2/2 = 72
            
            # layer 2
            nn.Conv1d(in_channels=16, out_channels=32, kernel_size=5, stride=2, padding=2),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2), # output roughly 72/2/2 = 18
            
            # layer 3
            nn.Conv1d(in_channels=32, out_channels=64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1) # output (Batch, 64, 1)
        )
        
        self.fc = nn.Sequential(
            nn.Linear(64, output_dim),
            nn.ReLU()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Check input dimensions
        if x.dim() == 2:
            x = x.unsqueeze(1) # (Batch, 1, 288)
        elif x.dim() == 1:
            x = x.unsqueeze(0).unsqueeze(0) # (1, 1, 288)
            
        features = self.conv_net(x)          # (B, 64, 1)
        features = features.squeeze(-1)      # (B, 64)
        out = self.fc(features)              # (B, 32)
        return out
