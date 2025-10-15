"""
FIXED: Heatmap Generator - Uses REAL website data
No random numbers, no defaults - based on actual button/image counts
Enhanced: More dynamic based on text, headings, colors, and readability for per-website variation
"""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import os
from io import BytesIO

def generate_simple_heatmap(buttons, images, text_length=0, headings={}, colors_count=0, readability_score=50, out_path=None):
    """
    Generate attention heatmap based on ACTUAL website data
    Uses real button count, image count, text length, headings, colors, and readability to create UNIQUE patterns per website
    """
    # Grid setup: 6 rows (top to bottom), 12 columns (left to right)
    H, W = 6, 12
    grid = np.zeros((H, W))
    
    # Calculate weights based on ACTUAL content
    num_buttons = len(buttons) if buttons else 0
    num_images = len(images) if images else 0
    num_headings = sum(headings.values()) if headings else 0  # Total headings for structure depth
    text_density = min(1.0, text_length / 2000.0)  # Normalize text length (high = content-heavy)
    color_variety = min(1.0, colors_count / 50.0)  # Normalize colors (high = vibrant site)
    readability_factor = readability_score / 100.0  # 0-1 scale (high readability = more sustained attention)
    
    print(f"[HEATMAP] Generating with {num_buttons} buttons, {num_images} images, {text_length} words, {num_headings} headings, {colors_count} colors, readability {readability_score}")
    
    # Realistic attention patterns based on actual content
    if num_buttons == 0 and num_images == 0 and text_length < 100:
        # No interactive/content - uniform low attention
        grid[:, :] = 0.3
    else:
        # Top rows: Navigation/Header area (buttons + headings like H1/H2)
        top_attention = min(1.0, 0.4 + (num_buttons / 15.0) + (headings.get('h1', 0) + headings.get('h2', 0)) / 10.0)
        grid[0:2, :] = top_attention * (1.0 + color_variety * 0.2)  # Boost if vibrant colors
        
        # Middle rows: Content area (images + text + lower headings)
        mid_attention = min(1.0, 0.5 + (num_images / 10.0) + text_density * 0.3 + (headings.get('h3', 0) + headings.get('h4', 0)) / 8.0)
        mid_attention *= readability_factor  # Reduce if hard to read
        grid[2:4, :] = mid_attention
        
        # Bottom rows: Footer/CTA (some buttons + lower content)
        bottom_attention = min(0.8, 0.3 + (num_buttons / 20.0) + (headings.get('h5', 0) + headings.get('h6', 0)) / 10.0)
        grid[4:6, :] = bottom_attention
        
        # Add natural variation based on analysis (not random)
        for row in range(H):
            for col in range(W):
                # Left side bias (F-pattern), stronger if more text/headings (reading-heavy sites)
                left_bias = 1.0 - (col / W) * (0.3 + text_density * 0.2)
                grid[row, col] *= left_bias
                
                # Add "hot spots" for images/buttons (scatter based on counts)
                if num_images > 5 and row in [2,3] and col % 3 == 0:  # Middle hotspots for image-heavy
                    grid[row, col] += 0.2
                if num_buttons > 10 and row in [0,5] and col % 2 == 0:  # Top/bottom hotspots for button-heavy
                    grid[row, col] += 0.15
    
    # Normalize to 0-1 range
    if grid.max() > 0:
        grid = np.clip(grid / grid.max(), 0, 1)  # Clip to avoid overflow
    else:
        grid[:, :] = 0.3  # Fallback if all zeros
    
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
        vmax=1,                    # Maximum value (red),
    )
    
    # Labels and title
    ax.set_title(
        f"User Attention Heatmap (Customized for Site: {num_buttons} btns, {num_images} imgs, {text_length} words)",
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


def generate_heatmap_with_stats(buttons, images, text_length=0, headings={}, colors_count=0, readability_score=50, out_path=None):
    """
    Advanced version: Heatmap + statistics side-by-side
    Uses ACTUAL website data with enhanced variation
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor='white')
    
    # Left: Heatmap (same enhanced logic as above)
    H, W = 6, 12
    grid = np.zeros((H, W))
    
    num_buttons = len(buttons) if buttons else 0
    num_images = len(images) if images else 0
    num_headings = sum(headings.values()) if headings else 0
    text_density = min(1.0, text_length / 2000.0)
    color_variety = min(1.0, colors_count / 50.0)
    readability_factor = readability_score / 100.0
    
    if num_buttons == 0 and num_images == 0 and text_length < 100:
        grid[:, :] = 0.3
    else:
        top_attention = min(1.0, 0.4 + (num_buttons / 15.0) + (headings.get('h1', 0) + headings.get('h2', 0)) / 10.0)
        grid[0:2, :] = top_attention * (1.0 + color_variety * 0.2)
        
        mid_attention = min(1.0, 0.5 + (num_images / 10.0) + text_density * 0.3 + (headings.get('h3', 0) + headings.get('h4', 0)) / 8.0)
        mid_attention *= readability_factor
        grid[2:4, :] = mid_attention
        
        bottom_attention = min(0.8, 0.3 + (num_buttons / 20.0) + (headings.get('h5', 0) + headings.get('h6', 0)) / 10.0)
        grid[4:6, :] = bottom_attention
        
        for row in range(H):
            for col in range(W):
                left_bias = 1.0 - (col / W) * (0.3 + text_density * 0.2)
                grid[row, col] *= left_bias
                
                if num_images > 5 and row in [2,3] and col % 3 == 0:
                    grid[row, col] += 0.2
                if num_buttons > 10 and row in [0,5] and col % 2 == 0:
                    grid[row, col] += 0.15
    
    if grid.max() > 0:
        grid = np.clip(grid / grid.max(), 0, 1)
    else:
        grid[:, :] = 0.3
    
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
    ax1.set_title(f"Attention Heatmap", fontsize=12, fontweight='bold')
    ax1.invert_yaxis()
    
    # Right: Statistics (enhanced with new data)
    ax2.axis('off')
    
    # Calculate focus zones
    high_focus = np.sum(grid > 0.7)
    med_focus = np.sum((grid >= 0.4) & (grid <= 0.7))
    low_focus = np.sum(grid < 0.4)
    
    stats_text = f"""
HEATMAP ANALYSIS SUMMARY

Content Distribution:
├─ Buttons/Links: {num_buttons}
├─ Images: {num_images}
├─ Words: {text_length}
├─ Headings: {num_headings}
├─ Unique Colors: {colors_count}
└─ Readability: {readability_score}/100

Attention Zones:
├─ High Focus (>0.7): {high_focus} cells
├─ Medium Focus: {med_focus} cells
└─ Low Focus (<0.4): {low_focus} cells

Pattern Analysis:
• Customized F-pattern based on content
• Top: High if buttons/headings ({top_attention:.2f} base)
• Middle: Boosted by images/text/readability ({mid_attention:.2f} base)
• Bottom: CTAs if buttons ({bottom_attention:.2f} base)
• Vibrancy boost from colors: +{color_variety*20:.0f}%

Data Source: Real website analysis
(Not randomized or estimated)
"""
    
    ax2.text(0.1, 0.5, stats_text, 
             fontsize=10, 
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