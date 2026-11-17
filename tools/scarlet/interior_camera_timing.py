"""Frame-rate-independent interpolation model for Scarlet's indoor camera.

This is a *reference model*, not a hook into the game's Lua interpreter. The
verified 30 Hz smoothing coefficient is an input: don't guess it from a count
of 1/30 constants. Applying this formula in gameplay still requires identifying
and validating the InteriorCameraBehavior call site and original coefficient.
"""
import argparse
import math

BASE_STEP_S = 1.0 / 30.0


def effective_alpha(alpha_30: float, elapsed_s: float) -> float:
    """Convert a per-30-Hz step blend into a blend for real elapsed time.

    For fixed targets, two 60-Hz blends reproduce one 30-Hz blend:
        1 - (1 - alpha_60)**2 == alpha_30
    """
    if not math.isfinite(alpha_30) or not 0.0 <= alpha_30 <= 1.0:
        raise ValueError('alpha_30 must be finite and within [0,1]')
    if not math.isfinite(elapsed_s) or elapsed_s < 0.0:
        raise ValueError('elapsed_s must be finite and nonnegative')
    if elapsed_s == 0.0 or alpha_30 == 0.0:
        return 0.0
    if alpha_30 == 1.0:
        return 1.0
    return -math.expm1((elapsed_s / BASE_STEP_S) * math.log1p(-alpha_30))


def smooth(current: float, target: float, alpha_30: float, elapsed_s: float) -> float:
    if not math.isfinite(current) or not math.isfinite(target):
        raise ValueError('camera coordinates must be finite')
    return current + (target - current) * effective_alpha(alpha_30, elapsed_s)


def sample(alpha_30: float, seconds: float, fps: int) -> float:
    if fps <= 0 or seconds < 0.0 or not math.isfinite(seconds):
        raise ValueError('positive FPS and finite nonnegative duration required')
    frames = round(fps * seconds)
    if not math.isclose(frames / fps, seconds, abs_tol=1e-9):
        raise ValueError('duration must contain an integral number of frames')
    x = 0.0
    for _ in range(frames):
        x = smooth(x, 1.0, alpha_30, 1.0 / fps)
    return x


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alpha30', type=float, required=True,
                        help='Observed 30-Hz camera blend (not a guessed value)')
    parser.add_argument('--seconds', type=float, default=2.0)
    args = parser.parse_args()
    for fps in (30, 60):
        print(f'{fps} FPS: position={sample(args.alpha30, args.seconds, fps):.12f} '
              f'alpha/frame={effective_alpha(args.alpha30, 1/fps):.12f}')
