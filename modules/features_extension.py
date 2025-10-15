from modules.colorblind_simulator import MATRICES  # Import for colorblind matrices
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

# Helper: Convert hex to RGB
def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join(c * 2 for c in hex_str)
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

# Helper: Calculate relative luminance (WCAG standard)
def luminance(rgb):
    def linearize(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = [linearize(v) for v in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

# Helper: Standard contrast ratio (WCAG)
def contrast_ratio(fg_hex, bg_hex):
    l1 = luminance(hex_to_rgb(fg_hex))
    l2 = luminance(hex_to_rgb(bg_hex))
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

# Helper: Colorblind transformation and contrast ratio
def colorblind_contrast_ratio(fg_hex, bg_hex, cb_type):
    mat = MATRICES[cb_type]
    fg_rgb = hex_to_rgb(fg_hex)
    bg_rgb = hex_to_rgb(bg_hex)
    fg_cb = colorblind_transform(fg_rgb, mat)
    bg_cb = colorblind_transform(bg_rgb, mat)
    l1 = luminance(fg_cb)
    l2 = luminance(bg_cb)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

def colorblind_transform(rgb, mat):
    flat = np.array(rgb).astype(float) / 255.0
    transformed = flat @ mat.T
    return np.clip(transformed, 0, 1) * 255
def compute_wcag_compliance_score(issues, pairs):
    """Compute a WCAG compliance score based on the number of contrast issues."""
    try:
        total_pairs = len(pairs)
        issues_count = len(issues)
        score = 100 - (issues_count / total_pairs * 100) if total_pairs else 100
        return round(max(0, min(100, score)), 1)
    except Exception as e:
        print(f"[ERROR] Failed to compute WCAG score: {e}")
        return 0
# New Function: Plot lowest contrast pairs based on website palette and colorblind simulations
def plot_lowest_contrast_pairs(issues, buf=True):
    if not issues:
        return None
    
    # Enhance issues with colorblind ratios (if not already present)
    for issue in issues:
        if 'cb_ratios' not in issue:
            issue['cb_ratios'] = {}
            for cb_type in MATRICES:
                issue['cb_ratios'][cb_type] = colorblind_contrast_ratio(issue['fg'], issue['bg'], cb_type)
    
    # Compute min_ratio for sorting (lowest across normal + colorblind)
    for issue in issues:
        all_ratios = [issue['ratio']] + list(issue['cb_ratios'].values())
        issue['min_ratio'] = min(all_ratios)
    
    # Select and sort top 5 lowest by min_ratio
    lowest = sorted(issues, key=lambda x: x['min_ratio'])[:5]
    
    if not lowest:
        return None
    
    # Plot grouped bars
    fig, ax = plt.subplots(figsize=(12, 6))
    types = ['Normal'] + list(MATRICES.keys())
    width = 0.2
    ind = np.arange(len(lowest))
    
    for j, t in enumerate(types):
        ratios = [p['ratio'] if t == 'Normal' else p['cb_ratios'][t] for p in lowest]
        ax.bar(ind + j * width, ratios, width, label=t)
    
    ax.set_ylabel('Contrast Ratio', fontweight='bold')
    ax.set_title('Lowest Contrast Pairs (Website-Specific, Including Colorblind Simulations)', fontweight='bold', fontsize=14)
    ax.set_xticks(ind + width * (len(types) / 2 - 0.5))
    labels = [f"{p['fg']} on {p['bg']}" for p in lowest]
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.axhline(4.5, color='red', linestyle='--', label='AA Threshold (4.5:1)')
    ax.axhline(7.0, color='green', linestyle='--', label='AAA Threshold (7:1)')
    ax.legend(loc='upper right')
    ax.set_ylim(0, max(7.5, max([p['ratio'] for p in lowest]) + 1))
    
    plt.tight_layout()
    
    if buf:
        buf_obj = BytesIO()
        plt.savefig(buf_obj, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        buf_obj.seek(0)
        return buf_obj
    else:
        return fig