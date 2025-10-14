import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os
from io import BytesIO

def generate_simple_heatmap(buttons, images, out_path=None):
    """
    Generate attention heatmap for website analysis
    Shows where users focus on different parts of the page
    """
    # Grid setup: 6 rows (top to bottom), 12 columns (left to right)
    H, W = 6, 12
    grid = np.zeros((H, W))
    
    # Calculate weights based on content
    btn_w = max(1, len(buttons))      # More buttons = more focus
    img_w = max(1, len(images))       # More images = more focus
    
    # Assign focus areas
    grid[0:2, :] += btn_w * 0.6       # Top 2 rows: buttons/navigation
    grid[2:4, :] += img_w * 0.8       # Middle 2 rows: images/content
    grid[4:, :] += 0.3                # Bottom 2 rows: footer/other
    
    # Add realistic variation (noise)
    grid += np.random.rand(H, W) * 0.25
    
    # Normalize to 0-1 range
    grid = grid / grid.max()
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
    
    # Create heatmap with seaborn
    sns.heatmap(
        grid,
        ax=ax,
        cmap="RdYlGn_r",           # Red (high focus) to Green (low focus)
        annot=True,                # Show numbers in cells
        fmt=".2f",                 # Format: 2 decimal places
        linewidths=0.5,            # Grid lines between cells
        linecolor='gray',          # Grid color
        cbar_kws={
            'label': 'Attention Focus Level',
            'shrink': 0.8
        },
        annot_kws={'size': 8},     # Annotation font size
        vmin=0,                    # Minimum value (green)
        vmax=1,                    # Maximum value (red)
    )
    
    # Labels and title
    ax.set_title(
        "Estimated User Attention Heatmap",
        fontsize=14,
        fontweight='bold',
        pad=20
    )
    ax.set_xlabel("Page Width Sections →", fontsize=11, fontweight='bold')
    ax.set_ylabel("Page Height Sections ↓", fontsize=11, fontweight='bold')
    ax.invert_yaxis()  # Top of page at top
    
    # Make it look professional
    ax.set_xticklabels([f'{i}' for i in range(W)], rotation=0)
    ax.set_yticklabels([f'{i}' for i in range(H)], rotation=0)
    
    plt.tight_layout()
    
    if out_path:
        # Save to file
        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
        fig.savefig(out_path, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return out_path
    else:
        # Return in-memory BytesIO for Streamlit
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        buf.seek(0)
        return buf


def generate_heatmap_with_stats(buttons, images, out_path=None):
    """
    Advanced version: Heatmap + statistics side-by-side
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor='white')
    
    # Left: Heatmap
    H, W = 6, 12
    grid = np.zeros((H, W))
    btn_w = max(1, len(buttons))
    img_w = max(1, len(images))
    
    grid[0:2, :] += btn_w * 0.6
    grid[2:4, :] += img_w * 0.8
    grid[4:, :] += 0.3
    grid += np.random.rand(H, W) * 0.25
    grid = grid / grid.max()
    
    sns.heatmap(
        grid,
        ax=ax1,
        cmap="RdYlGn_r",
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        cbar_kws={'label': 'Focus Level'},
        annot_kws={'size': 7},
        vmin=0,
        vmax=1,
    )
    ax1.set_title("Attention Heatmap", fontsize=12, fontweight='bold')
    ax1.invert_yaxis()
    
    # Right: Statistics
    ax2.axis('off')
    
    stats_text = f"""
HEATMAP ANALYSIS SUMMARY

Content Distribution:
├─ Buttons/Links: {len(buttons)}
├─ Images: {len(images)}
└─ Focus Areas: 3 (Nav, Content, Footer)

High Focus Zones (Red):
• Header/Navigation (rows 0-1)
• Main Content (rows 2-3)

Low Focus Zones (Green):
• Footer/Bottom (rows 4-5)

User Attention Pattern:
Top-to-bottom scanning with
emphasis on interactive elements
and visual content.
"""
    
    ax2.text(0.1, 0.5, stats_text, 
             fontsize=11, 
             family='monospace',
             verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    plt.tight_layout()
    
    if out_path:
        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
        fig.savefig(out_path, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return out_path
    else:
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        buf.seek(0)
        return buf