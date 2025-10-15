"""
ColorSync Access - Professional Edition
FIXED: Now analyzes REAL website data (no hardcoded defaults)
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from io import BytesIO
from datetime import datetime
import base64
import traceback

# plotting and data
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# images & pdf
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from modules.pdf_report_complete import generate_complete_pdf_report
from modules.heatmap_generator import generate_simple_heatmap
from modules.features_extension import (
    plot_lowest_contrast_pairs
)
from modules.accessibility_enhancements import (
    compute_score_breakdown,
    suggest_aaa_compliant_colors,
    analyze_typography_details,
    export_analysis_json
)
from modules.heatmap_generator import generate_simple_heatmap, generate_heatmap_with_stats

import re  # Already present, just confirming
from itertools import combinations  # NEW: Add for generating color pairs
from modules.colorblind_simulator import MATRICES  # NEW: Add for colorblind matrices
# optional libs
try:
    import textstat
    HAS_TEXTSTAT = True
except:
    HAS_TEXTSTAT = False

try:
    import colorspacious
    HAS_COLORSPACIOUS = True
except:
    HAS_COLORSPACIOUS = False

try:
    import cssutils
    cssutils.log.setLevel(100)
    HAS_CSSUTILS = True
except:
    HAS_CSSUTILS = False

# ---------------------------
# Custom CSS for Professional Look
# ---------------------------
def inject_custom_css():
    st.markdown("""
    <style>
        /* Main container */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }
        
        /* Headers */
        h1, h2, h3 {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-weight: 700;
            letter-spacing: -0.02em;
        }
        
        /* Input field styling */
        .stTextInput > div > div > input {
            border: 2px solid #e0e7ff;
            border-radius: 12px;
            padding: 16px 20px;
            font-size: 16px;
            transition: all 0.3s ease;
            background: white;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        /* Button styling */
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 14px 32px;
            font-weight: 600;
            font-size: 16px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        /* Metric cards */
        [data-testid="stMetricValue"] {
            font-size: 32px;
            font-weight: 700;
            color: #667eea;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 14px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        /* Color swatches */
        .color-swatch {
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            font-weight: 700;
            font-size: 14px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease;
        }
        
        .color-swatch:hover {
            transform: scale(1.05);
        }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------
# Utility functions
# ---------------------------
def normalize_hex(h):
    h = str(h).strip()
    if not h:
        return None
    m = re.match(r'rgba?\(([^)]+)\)', h)
    if m:
        parts = m.group(1).split(',')
        try:
            r, g, b = [int(float(p.strip())) for p in parts[:3]]
            return '#{:02X}{:02X}{:02X}'.format(r, g, b)
        except:
            return None
    m2 = re.match(r'#([0-9A-Fa-f]{3,8})', h)
    if m2:
        hh = m2.group(1)
        if len(hh) == 3:
            hh = ''.join([c*2 for c in hh])
        return '#' + hh.upper()
    named = {
        'black':'#000000','white':'#FFFFFF','red':'#FF0000','blue':'#0000FF',
        'green':'#008000','gray':'#808080','grey':'#808080','yellow':'#FFFF00'
    }
    if h.lower() in named:
        return named[h.lower()]
    return None

def hex_to_rgb(hex_color):
    try:
        h = hex_color.lstrip('#')
        if len(h) == 3:
            h = ''.join([c*2 for c in h])
        r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
        return (r, g, b)
    except:
        return (0,0,0)

def srgb_to_linear_channel(c):
    c = c / 255.0
    if c <= 0.03928:
        return c / 12.92
    else:
        return ((c + 0.055) / 1.055) ** 2.4

def relative_luminance(rgb):
    r, g, b = rgb
    return 0.2126*srgb_to_linear_channel(r) + 0.7152*srgb_to_linear_channel(g) + 0.0722*srgb_to_linear_channel(b)

def contrast_ratio(hex1, hex2):
    try:
        L1 = relative_luminance(hex_to_rgb(hex1))
        L2 = relative_luminance(hex_to_rgb(hex2))
        lighter = max(L1, L2)
        darker = min(L1, L2)
        ratio = (lighter + 0.05) / (darker + 0.05)
        return round(ratio, 2)
    except Exception:
        return 1.0

def best_text_color(bg_hex):
    if not bg_hex:
        return '#000000'
    white = contrast_ratio(bg_hex, '#FFFFFF')
    black = contrast_ratio(bg_hex, '#000000')
    return '#FFFFFF' if white >= black else '#000000'

def suggest_accessible_fg(bg_hex, desired_ratio=4.5):
    if contrast_ratio(bg_hex, '#000000') >= desired_ratio:
        return '#000000'
    if contrast_ratio(bg_hex, '#FFFFFF') >= desired_ratio:
        return '#FFFFFF'
    return '#000000' if contrast_ratio(bg_hex, '#000000') > contrast_ratio(bg_hex, '#FFFFFF') else '#FFFFFF'

def validate_url(url):
    """Validate URL format and accessibility"""
    if not url:
        return False, "Please enter a URL"
    if not url.startswith(('http://', 'https://')):
        return False, "URL must start with http:// or https://"
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return False, "Invalid URL format"
        return True, "Valid"
    except:
        return False, "Invalid URL format"

# ---------------------------
# FIXED: Extract REAL colors (NO defaults unless absolutely empty)
# ---------------------------
def extract_colors_from_html_css(html, base_url=None):
    """Extract colors from actual website - NO HARDCODED DEFAULTS"""
    colors = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # inline styles
        for tag in soup.find_all(style=True):
            style = tag['style']
            for m in re.findall(r'(?:color|background-color|background)\s*:\s*([^;]+);?', style, flags=re.I):
                hx = normalize_hex(m)
                if hx and hx not in colors:
                    colors.append(hx)
        
        # style tags
        for st in soup.find_all('style'):
            txt = st.string or ''
            for m in re.findall(r'#[0-9A-Fa-f]{3,6}\b', txt):
                hx = normalize_hex(m)
                if hx and hx not in colors:
                    colors.append(hx)
            for m in re.findall(r'rgb[a]?\([^)]+\)', txt):
                hx = normalize_hex(m)
                if hx and hx not in colors:
                    colors.append(hx)
        
        # linked CSS
        for link in soup.find_all('link', rel=lambda x: x and 'stylesheet' in str(x).lower()):
            href = link.get('href')
            if not href:
                continue
            css_url = href if bool(urlparse(href).netloc) else urljoin(base_url or '', href)
            try:
                r = requests.get(css_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                if r.status_code == 200:
                    css_text = r.text
                    for m in re.findall(r'#[0-9A-Fa-f]{3,6}\b', css_text):
                        hx = normalize_hex(m)
                        if hx and hx not in colors:
                            colors.append(hx)
                    for m in re.findall(r'rgba?\([^)]+\)', css_text):
                        hx = normalize_hex(m)
                        if hx and hx not in colors:
                            colors.append(hx)
                    for m in re.findall(r'--[\w-]+\s*:\s*([^;]+);', css_text):
                        hx = normalize_hex(m.strip())
                        if hx and hx not in colors:
                            colors.append(hx)
            except Exception as e:
                print(f"CSS fetch failed for {css_url}: {e}")
                continue

        # Meta theme
        for meta in soup.find_all('meta', attrs={'name': 'theme-color'}):
            hx = normalize_hex(meta.get('content', ''))
            if hx and hx not in colors:
                colors.append(hx)
                
    except Exception as e:
        print(f"Error extracting colors: {e}")

    # ONLY add defaults if NO colors found at all
    if len(colors) == 0:
        st.warning("⚠️ No colors detected. Website may use external stylesheets or images.")
        colors = ['#FFFFFF', '#000000']  # Minimal fallback
    
    return colors[:24]  # Return unique colors

# ---------------------------
# FIXED: Extract REAL buttons and images
# ---------------------------
def extract_buttons_and_images(html, base_url=None):
    """Extract actual interactive elements and images from website"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract buttons (button tags + clickable links)
    buttons = []
    for btn in soup.find_all(['button', 'a', 'input']):
        if btn.name == 'input' and btn.get('type') not in ['button', 'submit']:
            continue
        text = btn.get_text(strip=True)
        if text:
            buttons.append(text[:50])  # Limit length
    
    # Extract images
    images = []
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src:
            full_url = src if bool(urlparse(src).netloc) else urljoin(base_url or '', src)
            images.append(full_url)
    
    print(f"✅ Extracted {len(buttons)} buttons and {len(images)} images")
    return buttons[:50], images[:50]  # Limit to reasonable numbers

def extract_text_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    for s in soup(['script','style','noscript']):
        s.decompose()
    texts = []
    for tag in soup.find_all(['article','main','section','p','h1','h2','h3','h4']):
        t = tag.get_text(separator=' ', strip=True)
        if t:
            texts.append(t)
    if not texts:
        body = soup.body
        if body:
            texts = [body.get_text(separator=' ', strip=True)]
    return '\n\n'.join(texts)[:20000]

def compute_readability(text):
    if not text or len(text.strip()) < 20:
        return {'flesch_ease': None, 'fk_grade': None}
    try:
        if HAS_TEXTSTAT:
            fe = round(textstat.flesch_reading_ease(text), 1)
            fk = round(textstat.flesch_kincaid_grade(text), 1)
        else:
            words = len(re.findall(r'\b\w+\b', text))
            sentences = max(1, len(re.findall(r'[.!?]+', text)))
            syllables = sum(max(1, len(re.findall(r'[aeiouy]+', w.lower()))) for w in re.findall(r'\b\w+\b', text))
            fe = max(0, min(100, round(206.835 - 1.015*(words/sentences) - 84.6*(syllables/words), 1)))
            fk = None
        return {'flesch_ease': fe, 'fk_grade': fk}
    except Exception:
        return {'flesch_ease': None, 'fk_grade': None}

# def evaluate_contrast_pairs(colors, threshold=4.5):
#     issues = []
#     pairs = []
#     for i, a in enumerate(colors):
#         for j, b in enumerate(colors):
#             if i == j:
#                 continue
#             ratio = contrast_ratio(a,b)
#             if ratio < threshold:
#                 issues.append({'fg':a, 'bg':b, 'ratio':ratio})
#             pairs.append({'fg':a,'bg':b,'ratio':ratio})
#     return issues, pairs

def colorblind_transform(rgb, mat):
    flat = np.array(rgb).astype(float) / 255.0
    transformed = flat @ mat.T
    return np.clip(transformed, 0, 1) * 255

def colorblind_contrast_ratio(fg_hex, bg_hex, cb_type):
    mat = MATRICES[cb_type]
    fg_rgb = hex_to_rgb(fg_hex)
    bg_rgb = hex_to_rgb(bg_hex)
    fg_cb = colorblind_transform(fg_rgb, mat)
    bg_cb = colorblind_transform(bg_rgb, mat)
    l1 = relative_luminance(fg_cb)
    l2 = relative_luminance(bg_cb)
    return round((max(l1, l2) + 0.05) / (min(l1, l2) + 0.05), 2)

# ---------------------------
# Charts with professional styling
# ---------------------------
def plot_contrast_issues(pairs):
    """Generate contrast chart from ACTUAL pairs"""
    if not pairs:
        # Create empty chart
        fig, ax = plt.subplots(figsize=(10,5), facecolor='white')
        ax.text(0.5, 0.5, 'No contrast data available', ha='center', va='center', fontsize=14)
        ax.axis('off')
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        buf.seek(0)
        return buf
    
    df = pd.DataFrame(pairs)
    df_sorted = df.sort_values('ratio')
    top = df_sorted.head(10)
    
    fig, ax = plt.subplots(figsize=(10,5), facecolor='white')
    bars = ax.barh(range(len(top)), top['ratio'], 
                   color=['#ef4444' if r < 3 else '#f59e0b' if r < 4.5 else '#10b981' 
                          for r in top['ratio']])
    
    ax.set_yticks(range(len(top)))
    labels = [f"{r['fg']} on {r['bg']}" for _, r in top.iterrows()]
    ax.set_yticklabels(labels, fontsize=10, fontfamily='monospace')
    ax.invert_yaxis()
    ax.set_xlabel('Contrast Ratio', fontsize=12, fontweight='bold')
    ax.set_title('Lowest Contrast Pairs', fontsize=14, fontweight='bold', pad=20)
    
    ax.axvline(x=4.5, color='#f59e0b', linestyle='--', linewidth=2, alpha=0.7, label='AA (4.5:1)')
    ax.axvline(x=7.0, color='#10b981', linestyle='--', linewidth=2, alpha=0.7, label='AAA (7:1)')
    ax.legend(loc='lower right')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', alpha=0.3, linestyle=':')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    buf.seek(0)
    return buf

def create_palette_swatches(colors, sw=100, h=80):
    """Create swatches from ACTUAL extracted colors"""
    if not colors:
        # Empty placeholder
        img = Image.new('RGB', (600, 80), (240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.text((250, 35), "No colors detected", fill=(100, 100, 100))
        return img
    
    width = sw * len(colors)
    img = Image.new('RGB', (width, h), (255,255,255))
    draw = ImageDraw.Draw(img)
    
    try:
        fnt = ImageFont.truetype("arial.ttf", 12)
    except:
        fnt = ImageFont.load_default()
    
    for i,c in enumerate(colors):
        try:
            draw.rectangle([i*sw, 0, (i+1)*sw, h], fill=hex_to_rgb(c))
            tc = best_text_color(c)
            text = c
            bbox = draw.textbbox((0, 0), text, font=fnt)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = i*sw + (sw - text_width) // 2
            y = (h - text_height) // 2
            draw.text((x, y), text, fill=hex_to_rgb(tc), font=fnt)
        except:
            pass
    return img

def simulate_palette_colorblind(img, mode='protanopia'):
    """Simulate colorblindness on ACTUAL palette"""
    try:
        arr = np.array(img).astype(float)/255.0
        if HAS_COLORSPACIOUS:
            from colorspacious import cspace_convert
            if mode == 'protanopia':
                cb = {"name":"sRGB1","cvd_type":"protanomaly","severity":100}
            elif mode == 'deuteranopia':
                cb = {"name":"sRGB1","cvd_type":"deuteranomaly","severity":100}
            else:
                cb = {"name":"sRGB1","cvd_type":"tritanomaly","severity":100}
            out = cspace_convert(arr, "sRGB1", cb)
            out = np.clip(out*255, 0, 255).astype('uint8')
            return Image.fromarray(out)
        else:
            flat = arr.reshape(-1,3)
            if mode == 'protanopia':
                matrix = np.array([[0.567, 0.433, 0.0],
                                   [0.558, 0.442, 0.0],
                                   [0.0, 0.242, 0.758]])
            elif mode == 'deuteranopia':
                matrix = np.array([[0.625,0.375,0.0],
                                   [0.7,0.3,0.0],
                                   [0.0,0.3,0.7]])
            else:
                matrix = np.array([[0.95,0.05,0.0],
                                   [0.0,0.433,0.567],
                                   [0.0,0.475,0.525]])
            res = np.clip(flat @ matrix.T, 0, 1).reshape(arr.shape)
            out = (res*255).astype('uint8')
            return Image.fromarray(out)
    except Exception:
        return img

def compute_overall_score(num_issues, total_pairs, flesch, fk_grade):
    s = 100
    s -= min(60, num_issues * 3)
    if flesch is not None:
        if flesch < 50:
            s -= 10
        elif flesch < 65:
            s -= 5
    return max(0, min(100, int(round(s))))

def generate_recommendations(issues, pairs, colors, readability):
    recs = []
    seen = set()
    for it in sorted(issues, key=lambda x: x['min_ratio'])[:15]:
        key = (it['fg'], it['bg'])
        if key in seen: continue
        seen.add(key)
        suggestion = suggest_accessible_fg(it['bg'], 7.0)  # Aim for AAA
        recs.append(f"Improve contrast: {it['fg']} on {it['bg']} (current: {it['ratio']}:1, colorblind min: {it['min_ratio']}:1) → Use {suggestion}")
        if it['is_colorblind_issue']:
            recs.append(f"Colorblind issue detected for {it['fg']} on {it['bg']} - test with colorblind simulation tools")
    
    recs.append("Ensure all images have descriptive alt text for screen readers")
    recs.append("Use semantic HTML5 elements (header, nav, main, footer) for better structure")
    
    if readability.get('flesch_ease') is not None:
        fe = readability['flesch_ease']
        if fe < 50:
            recs.append("Simplify text: Use shorter sentences and common words for better readability")
        elif fe < 65:
            recs.append("Break up long paragraphs and add clear subheadings")
    
    recs.append("Maintain minimum font size of 16px for body text")
    recs.append("Use line-height between 1.5-1.6 for optimal readability")
    recs.append("Ensure interactive elements have focus indicators for keyboard navigation")
    
    return recs
# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(
    page_title="ColorSync Access - Professional Edition",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_custom_css()

# Hero Header
st.markdown("""
    <div style="background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); 
                padding: 40px 30px; border-radius: 16px; box-shadow: 0 8px 24px rgba(102,126,234,0.3);">
        <h1 style="color:white; margin:0; font-size: 42px; font-weight: 800;">
            🌐 ColorSync Access
        </h1>
        <p style="color: rgba(255,255,255,0.95); margin:10px 0 0 0; font-size: 18px; font-weight: 500;">
            Professional Web Accessibility & Readability Analyzer
        </p>
    </div>
""", unsafe_allow_html=True)

st.write("")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    threshold = st.selectbox(
        "WCAG Contrast Standard",
        [("AA - Normal Text (4.5:1)", 4.5),
         ("AA - Large Text (3.0:1)", 3.0),
         ("AAA - Enhanced (7.0:1)", 7.0)],
        index=0,
        format_func=lambda x: x[0]
    )[1]
    
    st.markdown("---")
    st.markdown("### 📊 Analysis Features")
    st.markdown("""
    - ✅ WCAG contrast evaluation
    - ✅ Readability scoring
    - ✅ Color-blind simulation
    - ✅ Professional PDF reports
    """)
    
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.info("Enter any public website URL. Analysis typically takes 10-15 seconds depending on site size.")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🔍 Website Analysis")
    url = st.text_input(
        "Enter Website URL",
        placeholder="https://www.example.com",
        help="Enter the complete URL including http:// or https://"
    )
    
with col2:
    st.markdown("### ")
    st.write("")
    analyze_btn = st.button("🚀 Analyze Website")

# URL validation and analysis
if analyze_btn:
    is_valid, msg = validate_url(url)
    
    if not is_valid:
        st.error(f"❌ {msg}")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Fetch
            status_text.text("📥 Fetching website content...")
            progress_bar.progress(20)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(url, timeout=15, headers=headers)
            resp.raise_for_status()
            html = resp.text
            
            # Step 2: Extract colors (REAL, no defaults)
            status_text.text("🎨 Extracting color palette...")
            progress_bar.progress(35)
            colors = extract_colors_from_html_css(html, base_url=url)
            
            # Step 3: Extract buttons and images (NEW - REAL DATA)
            status_text.text("🔘 Analyzing interactive elements...")
            progress_bar.progress(50)
            buttons, images = extract_buttons_and_images(html, base_url=url)
            
            # Step 4: Text analysis
            status_text.text("📖 Analyzing text content...")
            progress_bar.progress(65)
            text = extract_text_content(html)
            readability = compute_readability(text)
            # Step 5: Contrast evaluation
            status_text.text("🔍 Evaluating accessibility...")
            progress_bar.progress(80)

            # Initialize data dictionary
            data = {}

            # Use colors from extract_colors_from_html_css
            cleaned_colors = []
            for color_val in colors:  # Changed from data['colors'] to colors
                if isinstance(color_val, str) and len(color_val.strip()) > 0:
                    clean_color = color_val.strip().strip('"').strip("'")
                    if re.match(r'^#?[0-9a-fA-F]{3,6}$', clean_color):
                        if clean_color.startswith('#'):
                            cleaned_colors.append(clean_color)
                        else:
                            cleaned_colors.append('#' + clean_color)
                    elif re.match(r'^rgb\(\s*\d+,\s*\d+,\s*\d+\s*\)$', clean_color):
                        # Convert RGB to hex if needed
                        try:
                            rgb = [int(x.strip()) for x in clean_color.strip('rgb()').split(',')]
                            cleaned_colors.append('#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2]).upper())
                        except:
                            continue

            # Limit to reasonable number to avoid too many combinations
            cleaned_colors = cleaned_colors[:20]

            # Generate all possible foreground/background pairs
            pairs = []
            for fg, bg in combinations(cleaned_colors, 2):
                pairs.append({'fg': fg, 'bg': bg})  # Fixed: Corrected from 'bg': fg to 'bg': bg
                pairs.append({'fg': bg, 'bg': fg})

            print(f"[ANALYSIS] Generated {len(pairs)} color pairs from {len(cleaned_colors)} unique colors")

            # Analyze each pair for contrast issues (normal + colorblind)
            issues = []
            for pair in pairs:
                try:
                    ratio = contrast_ratio(pair['fg'], pair['bg'])
                    cb_ratios = {}
                    is_issue = ratio < threshold  # Use user-selected threshold (4.5, 3.0, or 7.0)
                    for cb_type in MATRICES:
                        cb_ratio = colorblind_contrast_ratio(pair['fg'], pair['bg'], cb_type)
                        cb_ratios[cb_type] = cb_ratio
                        if cb_ratio < threshold:
                            is_issue = True
                    if is_issue:
                        issues.append({
                            'fg': pair['fg'],
                            'bg': pair['bg'],
                            'ratio': round(ratio, 2),
                            'cb_ratios': {
                                'protanopia': round(cb_ratios['protanopia'], 2),
                                'deuteranopia': round(cb_ratios['deuteranopia'], 2),
                                'tritanopia': round(cb_ratios['tritanopia'], 2)
                            },
                            'min_ratio': min([ratio] + list(cb_ratios.values())),
                            'is_colorblind_issue': any(r < threshold for r in cb_ratios.values())
                        })
                except Exception as e:
                    print(f"[WARNING] Error analyzing pair {pair['fg']} on {pair['bg']}: {e}")
                    continue

            # Sort by worst ratio and limit
            issues = sorted(issues, key=lambda x: x['min_ratio'])[:15]
            data['issues'] = issues
            data['pairs'] = pairs
            data['total_pairs'] = len(pairs)
            data['num_issues'] = len(issues)
            data['colors'] = cleaned_colors  # Store cleaned colors
            data['buttons'] = buttons
            data['images'] = images
            data['text'] = text
            data['readability'] = readability

            print(f"[ANALYSIS] Found {len(issues)} contrast issues out of {len(pairs)} pairs")

            # Analyze each pair for contrast issues (normal + colorblind)
            issues = []
            for pair in pairs:
                try:
                    ratio = contrast_ratio(pair['fg'], pair['bg'])
                    cb_ratios = {}
                    is_issue = ratio < threshold  # Use user-selected threshold (4.5, 3.0, or 7.0)
                    for cb_type in MATRICES:
                        cb_ratio = colorblind_contrast_ratio(pair['fg'], pair['bg'], cb_type)
                        cb_ratios[cb_type] = cb_ratio
                        if cb_ratio < threshold:
                            is_issue = True
                    if is_issue:
                        issues.append({
                            'fg': pair['fg'],
                            'bg': pair['bg'],
                            'ratio': round(ratio, 2),
                            'cb_ratios': {
                                'protanopia': round(cb_ratios['protanopia'], 2),
                                'deuteranopia': round(cb_ratios['deuteranopia'], 2),
                                'tritanopia': round(cb_ratios['tritanopia'], 2)
                            },
                            'min_ratio': min([ratio] + list(cb_ratios.values())),
                            'is_colorblind_issue': any(r < threshold for r in cb_ratios.values())
                        })
                except Exception as e:
                    print(f"[WARNING] Error analyzing pair {pair['fg']} on {pair['bg']}: {e}")
                    continue

            # Sort by worst ratio and limit
            issues = sorted(issues, key=lambda x: x['min_ratio'])[:15]
            data['issues'] = issues
            data['pairs'] = pairs
            data['total_pairs'] = len(pairs)
            data['num_issues'] = len(issues)

            print(f"[ANALYSIS] Found {len(issues)} contrast issues out of {len(pairs)} pairs")
            
            # Step 6: Generate visuals (BASED ON REAL DATA)
            status_text.text("📊 Generating reports...")
            progress_bar.progress(90)
            palette_img = create_palette_swatches(colors[:12])
            palette_cb = simulate_palette_colorblind(palette_img, mode='protanopia')
            try:
                contrast_chart = plot_lowest_contrast_pairs(data['issues'])
                data['contrast_chart'] = contrast_chart
            except Exception as e:
                st.warning(f"⚠️ Could not generate contrast chart: {str(e)}")
                data['contrast_chart'] = None

            score = compute_overall_score(len(issues), len(pairs), 
                                        readability.get('flesch_ease'), 
                                        readability.get('fk_grade'))
            recs = generate_recommendations(issues, pairs, colors, readability)

            progress_bar.progress(100)
            status_text.text("✅ Analysis complete!")

            # Store results (WITH REAL BUTTONS/IMAGES)
            st.session_state.analysis = {
                'url': url,
                'colors': colors,
                'readability': readability,
                'issues': issues,
                'pairs': pairs,
                'score': score,
                'palette_img': palette_img,
                'palette_cb': palette_cb,
                'contrast_chart': contrast_chart,
                'recommendations': recs,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'text': text,
                'buttons': buttons,  # REAL DATA
                'images': images,     # REAL DATA
                'heatmap': None,
                'score_breakdown_chart': None
            }
            
            st.balloons()
            st.success("🎉 Analysis completed successfully!")
            
        except requests.exceptions.Timeout:
            st.error("⏱️ Request timed out. The website took too long to respond.")
        except requests.exceptions.ConnectionError:
            st.error("🔌 Connection error. Please check your internet connection.")
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ HTTP Error: {e.response.status_code}. The website may be unavailable.")
        except Exception as e:
            st.error(f"❌ An unexpected error occurred: {str(e)}")
            with st.expander("🔍 View error details"):
                st.code(traceback.format_exc())
        finally:
            progress_bar.empty()
            status_text.empty()

# Display results
st.write("")
st.markdown("---")

data = st.session_state.get('analysis')

if not data:
    # Empty state
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); 
                border-radius: 16px; border: 2px dashed #cbd5e1;">
        <h2 style="color: #475569; margin-bottom: 16px;">👆 Ready to Analyze</h2>
        <p style="color: #64748b; font-size: 16px; max-width: 600px; margin: 0 auto;">
            Enter a website URL above and click "Analyze Website" to generate a comprehensive 
            accessibility and readability report with actionable recommendations.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature highlights
    st.write("")
    st.markdown("### ✨ What You'll Get")
    
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown("""
        <div style="padding: 24px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <h3 style="color: #667eea; margin-bottom: 12px;">🎨 Color Analysis</h3>
            <p style="color: #64748b; font-size: 14px;">Extract and evaluate color palettes with WCAG compliance checks</p>
        </div>
        """, unsafe_allow_html=True)
    
    with c2:
        st.markdown("""
        <div style="padding: 24px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <h3 style="color: #10b981; margin-bottom: 12px;">♿ Accessibility</h3>
            <p style="color: #64748b; font-size: 14px;">Detailed contrast ratio analysis and accessibility scoring</p>
        </div>
        """, unsafe_allow_html=True)
    
    with c3:
        st.markdown("""
        <div style="padding: 24px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <h3 style="color: #f59e0b; margin-bottom: 12px;">📖 Readability</h3>
            <p style="color: #64748b; font-size: 14px;">Flesch Reading Ease and grade level assessment</p>
        </div>
        """, unsafe_allow_html=True)
    
    with c4:
        st.markdown("""
        <div style="padding: 24px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <h3 style="color: #ef4444; margin-bottom: 12px;">👁️ Color-blind</h3>
            <p style="color: #64748b; font-size: 14px;">Simulate how users with CVD see your palette</p>
        </div>
        """, unsafe_allow_html=True)

else:
    # Results display
    st.markdown("## 📊 Analysis Results")
    st.caption(f"Analyzed: {data['url']} | Generated: {data.get('timestamp', 'N/A')}")
    
    st.write("")
    
    # Key metrics
    m1, m2, m3, m4 = st.columns(4)
    
    score = data['score']
    score_color = "#10b981" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"
    
    with m1:
        st.markdown(f"""
        <div style="padding: 20px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;">
            <p style="color: #64748b; font-size: 12px; font-weight: 600; margin: 0; text-transform: uppercase;">Accessibility Score</p>
            <h2 style="color: {score_color}; font-size: 40px; margin: 8px 0; font-weight: 800;">{score}</h2>
            <p style="color: #94a3b8; font-size: 14px; margin: 0;">/100</p>
        </div>
        """, unsafe_allow_html=True)
    
    with m2:
        issues_count = len(data['issues'])
        issues_color = "#10b981" if issues_count == 0 else "#f59e0b" if issues_count < 10 else "#ef4444"
        st.markdown(f"""
        <div style="padding: 20px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;">
            <p style="color: #64748b; font-size: 12px; font-weight: 600; margin: 0; text-transform: uppercase;">Contrast Issues</p>
            <h2 style="color: {issues_color}; font-size: 40px; margin: 8px 0; font-weight: 800;">{issues_count}</h2>
            <p style="color: #94a3b8; font-size: 14px; margin: 0;">pairs below threshold</p>
        </div>
        """, unsafe_allow_html=True)
    
    with m3:
        fe = data['readability'].get('flesch_ease')
        if fe is not None:
            fe_display = f"{fe}"
            fe_label = "Very Easy" if fe > 80 else "Easy" if fe > 60 else "Moderate" if fe > 50 else "Difficult"
            fe_color = "#10b981" if fe > 60 else "#f59e0b" if fe > 50 else "#ef4444"
        else:
            fe_display = "N/A"
            fe_label = "Not calculated"
            fe_color = "#94a3b8"
        
        st.markdown(f"""
        <div style="padding: 20px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;">
            <p style="color: #64748b; font-size: 12px; font-weight: 600; margin: 0; text-transform: uppercase;">Reading Ease</p>
            <h2 style="color: {fe_color}; font-size: 40px; margin: 8px 0; font-weight: 800;">{fe_display}</h2>
            <p style="color: #94a3b8; font-size: 14px; margin: 0;">{fe_label}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with m4:
        fk = data['readability'].get('fk_grade')
        fk_display = f"{fk}" if fk is not None else "N/A"
        st.markdown(f"""
        <div style="padding: 20px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;">
            <p style="color: #64748b; font-size: 12px; font-weight: 600; margin: 0; text-transform: uppercase;">Grade Level</p>
            <h2 style="color: #667eea; font-size: 40px; margin: 8px 0; font-weight: 800;">{fk_display}</h2>
            <p style="color: #94a3b8; font-size: 14px; margin: 0;">F-K Grade</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    st.markdown("---")
    
    # Color palette
    st.markdown("### 🎨 Detected Color Palette")
    st.caption("Colors extracted from CSS, inline styles, and HTML")
    
    cols = st.columns(6)
    for i, color in enumerate(data['colors'][:12]):
        col_idx = i % 6
        tc = best_text_color(color)
        cols[col_idx].markdown(
            f"""<div class="color-swatch" style="background:{color}; color:{tc};">
                {color}
            </div>""",
            unsafe_allow_html=True
        )
    
    st.write("")
    st.markdown("---")

    # USER ATTENTION HEATMAP SECTION (NOW USES REAL DATA)
    st.markdown("### 📊 User Attention Heatmap")
    st.caption("Estimated focus areas based on buttons, images, and content distribution")
    
    try:
        # Use REAL buttons and images from extracted data
        buttons = data.get('buttons', [])
        images = data.get('images', [])
        
        st.info(f"📌 Detected: {len(buttons)} interactive elements, {len(images)} images")
        
        # Generate heatmap with REAL data
        heatmap_buf = generate_simple_heatmap(  
            buttons=data.get('buttons', []),
            images=data.get('images', []),
            text_length=len(data.get('text', '').split()),  
            headings=data.get('typography', {}).get('headings', {}),  
            colors_count=len(data.get('colors', [])),  
            readability_score=data.get('readability', {}).get('flesch_ease', 50)  
        )
        
        # Display it
        st.image(heatmap_buf, use_column_width=True)
        
        # Add explanation
        with st.expander("📖 How to read this heatmap"):
            st.markdown("""
            **Understanding the Heatmap Colors:**
            
            - **Red/Dark Areas**: High user attention zones
              - Navigation bars, headers, main content areas
              - Places where users focus their eyes first
            
            - **Yellow/Orange Areas**: Medium attention zones
              - Secondary content, sidebars, interactive elements
            
            - **Green/Light Areas**: Low attention zones
              - Footers, less critical information
              - Areas users typically scan last
            
            **The Numbers** (0.0 to 1.0) show attention intensity:
            - 1.0 = Maximum focus
            - 0.5 = Medium focus
            - 0.0 = Minimal focus
            
            **Grid Layout:**
            - Horizontal: 12 sections (left to right across page)
            - Vertical: 6 sections (top to bottom of page)
            """)
        
    except Exception as e:
        st.warning(f"Could not generate heatmap: {str(e)}")
    
    st.write("")
    st.markdown("---")
    
    # Color-blind simulation
    st.markdown("### 👁️ Color-blind Simulation (Protanopia)")
    st.caption("How users with red-green color blindness might perceive your palette")
    st.image(data['palette_cb'])
    
    st.write("")
    st.markdown("---")
    
    # Contrast analysis
    st.markdown("### 📊 Contrast Analysis")
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.markdown("#### Lowest Contrast Pairs")
        st.image(data['contrast_chart'])
    
    with col_b:
        st.markdown("#### WCAG Standards")
        st.markdown("""
        <div style="padding: 16px; background: #f8fafc; border-radius: 8px; border-left: 4px solid #667eea;">
            <p style="margin: 0; font-size: 14px;"><strong>AA (Normal Text)</strong>: 4.5:1</p>
            <p style="margin: 8px 0 0 0; font-size: 14px;"><strong>AA (Large Text)</strong>: 3.0:1</p>
            <p style="margin: 8px 0 0 0; font-size: 14px;"><strong>AAA (Enhanced)</strong>: 7.0:1</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        
        if data['issues']:
            st.warning(f"⚠️ {len(data['issues'])} pairs need attention")
        else:
            st.success("✅ All pairs meet threshold")
    
    st.write("")
    st.markdown("---")
    
    # Issues detail
    if data['issues']:
        st.markdown("### ⚠️ Accessibility Issues Detected")
        st.caption("Color pairs that don't meet the selected WCAG threshold")
        
        with st.expander("📋 View all issues", expanded=False):
            for i, issue in enumerate(sorted(data['issues'], key=lambda x: x['ratio'])[:30], 1):
                fg = issue['fg']
                bg = issue['bg']
                ratio = issue['ratio']
                
                fg_tc = best_text_color(fg)
                bg_tc = best_text_color(bg)
                
                status = "🔴 Fail" if ratio < 3.0 else "🟡 Warning"
                
                st.markdown(f"""
                <div style="padding: 12px; background: white; border-radius: 8px; margin: 8px 0; 
                            border: 1px solid #e2e8f0; display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-weight: 600; color: #64748b;">#{i}</span>
                        <span style="background:{fg}; color:{fg_tc}; padding: 6px 14px; border-radius: 6px; font-family: monospace; font-size: 13px;">{fg}</span>
                        <span style="color: #94a3b8;">on</span>
                        <span style="background:{bg}; color:{bg_tc}; padding: 6px 14px; border-radius: 6px; font-family: monospace; font-size: 13px;">{bg}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <span style="font-weight: 700; color: #667eea;">{ratio}:1</span>
                        <span>{status}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    st.write("")
    st.markdown("---")
    
    # Recommendations
    st.markdown("### 💡 Actionable Recommendations")
    st.caption("Steps to improve your website's accessibility and readability")
    
    tabs = st.tabs(["🎯 Priority", "📋 All Recommendations"])
    
    with tabs[0]:
        for i, rec in enumerate(data['recommendations'][:5], 1):
            st.markdown(f"""
            <div style="padding: 16px; background: white; border-radius: 8px; margin: 12px 0; 
                        border-left: 4px solid #667eea; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
                <p style="margin: 0; font-size: 15px; color: #334155;">
                    <strong style="color: #667eea;">#{i}</strong> {rec}
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    with tabs[1]:
        for i, rec in enumerate(data['recommendations'], 1):
            st.markdown(f"**{i}.** {rec}")
    
    st.write("")
    st.markdown("---")
    
    # NEW TABS SECTION
    tabs = st.tabs(["📊 Score Breakdown", "🎯 AAA Compliance", "📝 Typography Audit", "📤 Export JSON"])
    
    # TAB 1: Score Breakdown
    with tabs[0]:
        st.markdown("### Detailed Score Analysis")
        
        breakdown_data = compute_score_breakdown(
            len(data['issues']),
            len(data['pairs']),
            data['readability'],
            len(data.get('text', ''))
        )
        
        scores_dict = breakdown_data['breakdown']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🎨 Contrast Score", f"{scores_dict['contrast']:.0f}/100")
        with col2:
            st.metric("📖 Readability Score", f"{scores_dict['readability']:.0f}/100")
        with col3:
            st.metric("📄 Content Quality", f"{scores_dict['content_quality']:.0f}/100")
        
        # Pie chart
        fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
        sizes = list(scores_dict.values())
        labels = list(scores_dict.keys())
        colors_pie = ['#667eea', '#10b981', '#f59e0b']
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors_pie)
        ax.set_title('Score Contributors', fontsize=14, fontweight='bold', pad=20)
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        buf.seek(0)
        
        st.image(buf)
        
        st.info(f"**Weighted Score**: {breakdown_data['weighted_score']}/100 (50% contrast, 30% readability, 20% content)")
    
    # TAB 2: AAA Compliance
    with tabs[1]:
        st.markdown("### WCAG AAA Compliance Report")
        
        aaa_data = suggest_aaa_compliant_colors(data['issues'], data['pairs'], data['colors'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("AAA Compliant Pairs", aaa_data['aaa_compliant'], f"of {aaa_data['total_pairs']}")
        with col2:
            st.metric("AAA Coverage", f"{aaa_data['percentage']}%")
        
        if aaa_data['percentage'] >= 80:
            st.success("✅ Excellent! Most pairs meet AAA (7:1) standard")
        elif aaa_data['percentage'] >= 50:
            st.warning("⚠️ Some pairs meet AAA. Others need refinement.")
        else:
            st.warning("⚠️ Improvement Required: Few pairs meet AAA standards.")
        
        if aaa_data['needs_work']:
            st.markdown("#### Pairs needing AAA adjustment:")
            for item in aaa_data['needs_work'][:5]:
                fg = item['current']['fg']
                bg = item['current']['bg']
                ratio = item['current']['ratio']
                tc = best_text_color(fg)
                
                st.markdown(f"""
                <div style="padding: 12px; background: white; border-radius: 8px; margin: 8px 0; border-left: 4px solid #f59e0b;">
                    <span style="background:{fg}; color:{tc}; padding: 4px 10px; border-radius: 4px; font-family: monospace; font-size: 12px;">{fg}</span>
                    <span style="color: #94a3b8; margin: 0 8px;">on</span>
                    <span style="background:{bg}; color:{best_text_color(bg)}; padding: 4px 10px; border-radius: 4px; font-family: monospace; font-size: 12px;">{bg}</span>
                    <span style="color: #667eea; font-weight: 600; margin-left: 12px;">{ratio}:1</span> → <span style="color: #f59e0b;">needs 7:1</span>
                </div>
                """, unsafe_allow_html=True)
    
    # TAB 3: Typography Audit
    with tabs[2]:
        st.markdown("### Typography & Content Analysis")
        
        typo_data = analyze_typography_details(
            data.get('text', ''),
            data['readability']
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 Total Words", typo_data['word_count'])
        with col2:
            st.metric("📝 Sentences", typo_data['sentence_count'])
        with col3:
            st.metric("📌 Avg Words/Sentence", typo_data['avg_words_per_sentence'])
        
        st.markdown("#### Readability Guidelines")
        st.markdown("""
        - **Sentence Length**: Keep under 20 words average
        - **Font Size**: Minimum 16px for body text
        - **Line Height**: 1.5-1.6x font size
        - **Flesch Score**: 60-70 = general audience
        """)
        
        if typo_data['recommendations']:
            st.warning("**Recommendations:**")
            for rec in typo_data['recommendations']:
                st.markdown(f"- {rec}")
    
    # TAB 4: Export JSON
    with tabs[3]:
        st.markdown("### Export for Developers")
        st.caption("Machine-readable format for CI/CD integration and automation")
        
        json_export = export_analysis_json(data)
        
        st.code(json_export, language='json')
        
        st.download_button(
            label="📥 Download JSON Report",
            data=json_export,
            file_name=f"colorsync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
        
        st.info("Use this JSON with your build pipeline to track accessibility metrics over time.")

st.write("")
st.write("")
st.markdown("---")

st.markdown("""
<div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 16px; box-shadow: 0 8px 24px rgba(102,126,234,0.3); margin-bottom: 30px;">
    <h2 style="color: white; margin: 0 0 10px 0;">📥 Download Complete Analysis Report</h2>
    <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 16px;">
        Full PDF with all graphs, charts, heatmap, and recommendations
    </p>
</div>
""", unsafe_allow_html=True)

if data:
    col_pdf_1, col_pdf_2, col_pdf_3 = st.columns([1, 2, 1])
    
    with col_pdf_2:
        if st.button("📄 Generate Complete PDF Report", key="pdf_full_btn", use_container_width=True):
            with st.spinner("📄 Generating comprehensive PDF report..."):
                try:
                    # Generate heatmap if not exists
                    if not data.get('heatmap'):
                        try:
                            buttons = data.get('buttons', [])
                            images = data.get('images', [])
                            heatmap_buf = generate_simple_heatmap(buttons, images)
                            data['heatmap'] = heatmap_buf
                        except Exception as e:
                            st.warning(f"⚠️ Could not generate heatmap: {str(e)}")
                            data['heatmap'] = None
                    
                    # Generate score breakdown chart
                    if not data.get('score_breakdown_chart'):
                        try:
                            breakdown = compute_score_breakdown(
                                len(data['issues']),
                                len(data['pairs']),
                                data['readability'],
                                len(data.get('text', ''))
                            )
                            
                            fig, ax = plt.subplots(figsize=(6, 4), facecolor='white')
                            sizes = list(breakdown['breakdown'].values())
                            labels = ['Contrast\n' + f"{breakdown['breakdown']['contrast']:.0f}%",
                                    'Readability\n' + f"{breakdown['breakdown']['readability']:.0f}%",
                                    'Content\n' + f"{breakdown['breakdown']['content_quality']:.0f}%"]
                            colors_pie = ['#667eea', '#10b981', '#f59e0b']
                            
                            wedges, texts, autotexts = ax.pie(
                                sizes, 
                                labels=labels, 
                                autopct='%1.1f%%',
                                startangle=90, 
                                colors=colors_pie,
                                textprops={'fontsize': 9, 'fontweight': 'bold'}
                            )
                            
                            ax.set_title('Score Breakdown Analysis', fontsize=12, fontweight='bold', pad=12)
                            
                            breakdown_buf = BytesIO()
                            plt.savefig(breakdown_buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
                            plt.close()
                            breakdown_buf.seek(0)
                            
                            data['score_breakdown_chart'] = breakdown_buf
                            
                        except Exception as e:
                            st.warning(f"⚠️ Could not generate score breakdown: {str(e)}")
                            data['score_breakdown_chart'] = None
                    
                    # Generate AAA compliance chart
                    try:
                        aaa_data = suggest_aaa_compliant_colors(data['issues'], data['pairs'], data['colors'])
                        
                        fig, ax = plt.subplots(figsize=(8, 4), facecolor='white')
                        
                        categories = ['AAA Compliant', 'Needs Work']
                        values = [aaa_data['aaa_compliant'], len(aaa_data['needs_work'])]
                        colors_bar = ['#10b981', '#f59e0b']
                        
                        bars = ax.bar(categories, values, color=colors_bar, width=0.5)
                        
                        ax.set_ylabel('Number of Pairs', fontweight='bold', fontsize=10)
                        ax.set_title('WCAG AAA Compliance Status', fontweight='bold', fontsize=12, pad=15)
                        ax.spines['top'].set_visible(False)
                        ax.spines['right'].set_visible(False)
                        
                        for bar in bars:
                            height = bar.get_height()
                            ax.text(bar.get_x() + bar.get_width()/2., height,
                                   f'{int(height)}',
                                   ha='center', va='bottom', fontweight='bold', fontsize=11)
                        
                        aaa_buf = BytesIO()
                        plt.savefig(aaa_buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
                        plt.close()
                        aaa_buf.seek(0)
                        
                        data['aaa_chart'] = aaa_buf
                        
                    except Exception as e:
                        st.warning(f"⚠️ Could not generate AAA chart: {str(e)}")
                        data['aaa_chart'] = None
                    
                    # Generate typography chart
                    try:
                        typo_data = analyze_typography_details(
                            data.get('text', ''),
                            data['readability']
                        )
                        
                        fig, ax = plt.subplots(figsize=(7, 4), facecolor='white')
                        
                        metrics = ['Words', 'Sentences', 'Avg Words/Sentence']
                        values = [
                            typo_data['word_count'],
                            typo_data['sentence_count'],
                            typo_data['avg_words_per_sentence']
                        ]
                        
                        normalized = [v / max(values) * 100 for v in values]
                        
                        bars = ax.barh(metrics, normalized, color=['#667eea', '#10b981', '#f59e0b'])
                        
                        ax.set_xlabel('Normalized Score', fontweight='bold', fontsize=10)
                        ax.set_title('Typography Metrics', fontweight='bold', fontsize=12, pad=15)
                        ax.spines['top'].set_visible(False)
                        ax.spines['right'].set_visible(False)
                        
                        for i, (bar, val) in enumerate(zip(bars, values)):
                            ax.text(bar.get_width() + 2, i, f'{val:.0f}',
                                   va='center', fontweight='bold', fontsize=10)
                        
                        typo_buf = BytesIO()
                        plt.savefig(typo_buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
                        plt.close()
                        typo_buf.seek(0)
                        
                        data['typography_chart'] = typo_buf
                        
                    except Exception as e:
                        st.warning(f"⚠️ Could not generate typography chart: {str(e)}")
                        data['typography_chart'] = None
                    
                    # Generate PDF
                    pdf_data = {
                        'url': data['url'],
                        'timestamp': data.get('timestamp', 'N/A'),
                        'score': data['score'],
                        'issues': data.get('issues', []),
                        'colors': data.get('colors', []),
                        'readability': data.get('readability', {}),
                        'recommendations': data.get('recommendations', []),
                        'palette_img': data.get('palette_img'),
                        'palette_cb': data.get('palette_cb'),
                        'contrast_chart': data.get('contrast_chart'),
                        'heatmap': data.get('heatmap'),
                        'score_breakdown_chart': data.get('score_breakdown_chart'),
                        'aaa_chart': data.get('aaa_chart'),
                        'typography_chart': data.get('typography_chart')
                    }
                    
                    pdf_buffer = generate_complete_pdf_report(pdf_data)
                    
                    filename = f"ColorSync_Complete_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    
                    st.download_button(
                        label="✅ Click to Download Complete PDF",
                        data=pdf_buffer,
                        file_name=filename,
                        mime="application/pdf",
                        key="download_complete_pdf"
                    )
                    
                    st.success("✅ PDF Generated Successfully!")
                    
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {str(e)}")
                    with st.expander("🔍 Show error details"):
                        st.code(traceback.format_exc())
else:
    st.info("👆 First analyze a website, then download the complete PDF report with all visualizations")