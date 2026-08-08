"""Orientation field dip-isogon contours and multi-layer ridge extraction.

Extracts local bedding orientation theta(x, y) via the structure tensor,
renders continuous dip-isogon iso-contours across multi-layer folds, and
detects layer boundaries using Frangi ridge filtering.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from scipy.ndimage import gaussian_filter
from skimage.color import rgb2gray
from skimage.filters import frangi
from skimage.morphology import skeletonize


def compute_structure_tensor(img_gray: np.ndarray,
                             sigma: float = 2.0,
                             rho: float = 6.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Computes structure tensor components Jxx, Jyy, Jxy with inner scale sigma and integration scale rho."""
    # Gradients
    gy, gx = np.gradient(gaussian_filter(img_gray, sigma=sigma))

    # Outer product
    jxx = gaussian_filter(gx * gx, sigma=rho)
    jyy = gaussian_filter(gy * gy, sigma=rho)
    jxy = gaussian_filter(gx * gy, sigma=rho)

    return jxx, jyy, jxy


def compute_orientation_and_coherence(jxx: np.ndarray,
                                     jyy: np.ndarray,
                                     jxy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Derives local bedding orientation theta(x, y) in radians in [0, pi) and coherence C(x, y) in [0, 1]."""
    # Gradient direction orientation (double angle)
    theta_grad = 0.5 * np.arctan2(2 * jxy, jxx - jyy)

    # Tangent orientation (perpendicular to gradient)
    theta_tangent = (theta_grad + np.pi / 2) % np.pi

    # Coherence confidence mask
    diff = jxx - jyy
    num = np.sqrt(diff ** 2 + 4 * jxy ** 2)
    denom = jxx + jyy + 1e-10
    coherence = np.clip(num / denom, 0.0, 1.0)

    return theta_tangent, coherence


def extract_multi_layer_ridges(img_gray: np.ndarray,
                              sigmas: tuple[float, ...] = (1.0, 2.0, 3.0, 4.0)) -> tuple[np.ndarray, np.ndarray]:
    """Applies Frangi vesselness filter to extract curvilinear bedding ridges."""
    ridge_map = frangi(img_gray, sigmas=sigmas, black_ridges=True)
    # Normalize
    ridge_norm = ridge_map / (ridge_map.max() + 1e-10)
    # Skeletonize strong ridges
    skeleton = skeletonize(ridge_norm > 0.15)
    return ridge_norm, skeleton


def process_image(img_path: str,
                  output_path: str = "orientation_isogons.png",
                  min_coherence: float = 0.2) -> None:
    """Processes outcrop photograph and outputs 4-panel multi-layer orientation field and dip isogon map."""
    img = plt.imread(img_path)
    if img.ndim == 3:
        img_gray = rgb2gray(img[:, :, :3])
    else:
        img_gray = img.astype(float)
        img_gray /= img_gray.max()

    # Structure tensor & orientation
    jxx, jyy, jxy = compute_structure_tensor(img_gray, sigma=2.0, rho=8.0)
    theta, coherence = compute_orientation_and_coherence(jxx, jyy, jxy)

    # Frangi multi-layer ridge extraction
    ridge_map, skeleton = extract_multi_layer_ridges(img_gray)

    # Create 4-panel output plot
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle(f"Multi-Layer Orientation Field & Dip Isogons ({Path(img_path).name})",
                 fontsize=14, fontweight="bold")

    # Panel 1: Original image + Frangi ridge skeleton
    ax1 = axes[0, 0]
    ax1.imshow(img, cmap="gray" if img.ndim == 2 else None)
    sy, sx = np.where(skeleton)
    ax1.scatter(sx, sy, c="tab:cyan", s=0.5, alpha=0.6, label="Detected Ridge Centerlines")
    ax1.set_title("1. Multi-Layer Bedding Ridge Skeleton")
    ax1.legend(fontsize=8, loc="upper right")
    ax1.axis("off")

    # Panel 2: Orientation Field theta(x, y)
    ax2 = axes[0, 1]
    # Mask orientation by coherence threshold
    theta_masked = np.where(coherence >= min_coherence, np.degrees(theta), np.nan)
    im2 = ax2.imshow(theta_masked, cmap="hsv", vmin=0, vmax=180)
    ax2.set_title("2. Local Bedding Orientation Field theta(x, y)")
    plt.colorbar(im2, ax=ax2, label="Orientation (deg)")
    ax2.axis("off")

    # Panel 3: Coherence Confidence Mask C(x, y)
    ax3 = axes[1, 0]
    im3 = ax3.imshow(coherence, cmap="inferno", vmin=0, vmax=1)
    ax3.set_title("3. Structure Tensor Coherence Mask C(x, y)")
    plt.colorbar(im3, ax=ax3, label="Coherence [0, 1]")
    ax3.axis("off")

    # Panel 4: Continuous Dip Isogon Iso-Contours
    ax4 = axes[1, 1]
    ax4.imshow(img, cmap="gray" if img.ndim == 2 else None)

    # Smooth orientation field slightly for clean contour rendering
    theta_smooth = gaussian_filter(theta, sigma=3.0)
    masked_theta_smooth = np.where(coherence >= min_coherence, np.degrees(theta_smooth), np.nan)

    # Contour levels (e.g. every 10 degrees from 10 to 170)
    levels = np.arange(10.0, 170.0, 10.0)
    contours = ax4.contour(masked_theta_smooth, levels=levels, cmap="coolwarm", linewidths=1.2, alpha=0.85)
    ax4.clabel(contours, inline=True, fontsize=6, fmt="%1.0f°")
    ax4.set_title("4. Continuous Dip Isogon Contours (theta = alpha)")
    ax4.axis("off")

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Saved multi-layer orientation field plot -> {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Multi-layer orientation field and dip isogon extraction.")
    parser.add_argument("image", nargs="?", default="test-fold.png", help="Path to input fold image")
    parser.add_argument("--output", default="orientation_isogons.png", help="Output plot filename")
    parser.add_argument("--min-coherence", type=float, default=0.2, help="Minimum coherence threshold")
    args = parser.parse_args()

    process_image(args.image, output_path=args.output, min_coherence=args.min_coherence)


if __name__ == "__main__":
    main()
