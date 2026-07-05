"""Ball detection (TrackNet-style heatmap detector). PyTorch pieces import lazily."""
from .heatmap import gaussian_heatmap, decode_heatmap

__all__ = ["gaussian_heatmap", "decode_heatmap"]
