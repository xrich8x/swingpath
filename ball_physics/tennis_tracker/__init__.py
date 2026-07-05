"""tennis_tracker: monocular tennis-ball speed & spin estimation.

Subpackages:
    physics      flight simulator (numpy) + differentiable twin (torch)
    data         pinhole camera + synthetic labeled-trajectory generator
    detection    TrackNet-style heatmap ball detector (torch)
    tracking     link / smooth / bounce-detect / segment into arcs
    calibration  court geometry + homography + 2D->3D lifting
    estimation   physics-inversion fit (scipy) + learned SpinNet (torch)
    eval         metrics
    pipeline     end-to-end orchestration
"""
__version__ = "0.1.0"

from .physics import simulate, Trajectory
from .estimation import spin_vector, summarize, fit_arc, MotionReadout

__all__ = ["simulate", "Trajectory", "spin_vector", "summarize", "fit_arc", "MotionReadout"]
