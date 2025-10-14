"""
COMPLETE PDF REPORT GENERATOR - All Charts, No Extra Space
Save as: modules/pdf_report_complete.py
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from datetime import datetime

def generate_complete_pdf_report(analysis_data):
    """
    Generate complete PDF with ALL visualizations
    - No extra spaces
    - All charts included
    - Continuous flow
    """
    
    pdf_buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=0.35*inch,
        leftMargin=0.35*inch,
        topMargin=0.35*inch,
        bottomMargin=0.35*inch
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # ===== CUSTOM STYLES =====
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=0.08*inch,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=0.08*inch,
        spaceBefore=0.1*inch,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'SubHeading',
        parent=styles['Heading3'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=0.05*inch,
        spaceBefore=0.05*inch,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_LEFT,
        spaceAfter=0.05*inch
    )
    
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_LEFT,
        spaceAfter=0.03*inch
    )
    
    # ========== PAGE 1: TITLE & KEY METRICS ==========
    story.append(Paragraph("Vision Chroma pro - Complete Analysis Report", title_style))
    story.append(Spacer(1, 0.05*inch))
    
    # Metadata
    metadata = f"""
    <b>Website:</b> {analysis_data.get('url', 'N/A')}<br/>
    <b>Generated:</b> {analysis_data.get('timestamp', 'N/A')}<br/>
    <b>Report Type:</b> Comprehensive Accessibility & Readability Analysis
    """
    story.append(Paragraph(metadata, small_style))
    story.append(Spacer(1, 0.08*inch))
    
    # Key Metrics Table
    score = analysis_data.get('score', 0)
    issues_count = len(analysis_data.get('issues', []))
    flesch = analysis_data.get('readability', {}).get('flesch_ease', 'N/A')
    fk_grade = analysis_data.get('readability', {}).get('fk_grade', 'N/A')
    colors_list = analysis_data.get('colors', [])
    
    metrics_data = [
        ['Metric', 'Value', 'Status'],
        ['Overall Score', f"{score}/100", 'Good' if score >= 80 else 'Fair' if score >= 60 else 'Needs Work'],
        ['Contrast Issues', str(issues_count), 'Pass' if issues_count == 0 else 'Action Required'],
        ['Reading Ease', str(flesch), 'Easy' if flesch and flesch > 60 else 'Moderate'],
        ['Grade Level', str(fk_grade), 'Accessible' if fk_grade and fk_grade <= 8 else 'Complex'],
        ['Total Colors', str(len(colors_list)), 'Detected']
    ]
    
    metrics_table = Table(metrics_data, colWidths=[1.6*inch, 1.2*inch, 1.3*inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
    ]))
    
    story.append(metrics_table)
    story.append(Spacer(1, 0.1*inch))
    
    # ========== COLOR PALETTE ==========
    story.append(Paragraph("Detected Color Palette", heading_style))
    
    if 'palette_img' in analysis_data and analysis_data['palette_img'] is not None:
        try:
            palette_buffer = BytesIO()
            analysis_data['palette_img'].save(palette_buffer, format='PNG')
            palette_buffer.seek(0)
            img = Image(palette_buffer, width=7.0*inch, height=0.7*inch)
            story.append(img)
            story.append(Spacer(1, 0.05*inch))
        except:
            pass
    
    colors_display = ', '.join(colors_list[:12]) if colors_list else 'N/A'
    palette_info = f"<b>First 12 Colors:</b> {colors_display} | <b>Total:</b> {len(colors_list)}"
    story.append(Paragraph(palette_info, small_style))
    story.append(Spacer(1, 0.1*inch))
    
    # ========== CONTRAST ANALYSIS CHART ==========
    story.append(Paragraph("Contrast Analysis", heading_style))
    
    if 'contrast_chart' in analysis_data and analysis_data['contrast_chart'] is not None:
        try:
            analysis_data['contrast_chart'].seek(0)
            img = Image(analysis_data['contrast_chart'], width=7.0*inch, height=2.8*inch)
            story.append(img)
            story.append(Spacer(1, 0.05*inch))
        except:
            pass
    
    # Top 10 Issues Table
    issues = analysis_data.get('issues', [])[:10]
    if issues:
        story.append(Paragraph("Top 10 Contrast Issues", subheading_style))
        issues_data = [['#', 'Foreground', 'Background', 'Ratio', 'Status']]
        for i, issue in enumerate(issues, 1):
            ratio = issue.get('ratio', 0)
            status = 'Fail' if ratio < 3.0 else 'Warning' if ratio < 4.5 else 'Pass'
            issues_data.append([
                str(i),
                issue.get('fg', '')[:7],
                issue.get('bg', '')[:7],
                f"{ratio}:1",
                status
            ])
        
        issues_table = Table(issues_data, colWidths=[0.4*inch, 1.0*inch, 1.0*inch, 0.8*inch, 0.8*inch])
        issues_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')])
        ]))
        story.append(issues_table)
    
    story.append(Spacer(1, 0.1*inch))
    
    # ========== COLORBLIND SIMULATION ==========
    story.append(Paragraph("Color-blind Simulation (Protanopia)", heading_style))
    
    if 'palette_cb' in analysis_data and analysis_data['palette_cb'] is not None:
        try:
            cb_buffer = BytesIO()
            analysis_data['palette_cb'].save(cb_buffer, format='PNG')
            cb_buffer.seek(0)
            img = Image(cb_buffer, width=7.0*inch, height=0.7*inch)
            story.append(img)
            story.append(Spacer(1, 0.05*inch))
            story.append(Paragraph("<i>This shows how users with red-green color blindness perceive your palette</i>", small_style))
        except:
            pass
    
    story.append(Spacer(1, 0.08*inch))
    
    # ========== USER ATTENTION HEATMAP ==========
    story.append(Paragraph("User Attention Heatmap", heading_style))
    
    if 'heatmap' in analysis_data and analysis_data['heatmap'] is not None:
        try:
            analysis_data['heatmap'].seek(0)
            img = Image(analysis_data['heatmap'], width=6.5*inch, height=2.8*inch)
            story.append(img)
            story.append(Spacer(1, 0.03*inch))
            story.append(Paragraph("<i>Red zones = high user focus | Green zones = low focus</i>", small_style))
        except:
            pass
    
    story.append(Spacer(1, 0.08*inch))
    
    # ========== SCORE BREAKDOWN CHART (SMALLER) ==========
    story.append(Paragraph("Score Breakdown Analysis", heading_style))
    
    if 'score_breakdown_chart' in analysis_data and analysis_data['score_breakdown_chart'] is not None:
        try:
            analysis_data['score_breakdown_chart'].seek(0)
            img = Image(analysis_data['score_breakdown_chart'], width=5.0*inch, height=2.8*inch)
            story.append(img)
            story.append(Spacer(1, 0.03*inch))
            story.append(Paragraph("<i>Overall score weighted: 50% contrast + 30% readability + 20% content</i>", small_style))
        except:
            pass
    
    story.append(Spacer(1, 0.08*inch))
    
    # ========== AAA COMPLIANCE CHART ==========
    story.append(Paragraph("WCAG AAA Compliance Status", heading_style))
    
    if 'aaa_chart' in analysis_data and analysis_data['aaa_chart'] is not None:
        try:
            analysis_data['aaa_chart'].seek(0)
            img = Image(analysis_data['aaa_chart'], width=6.0*inch, height=2.2*inch)
            story.append(img)
            story.append(Spacer(1, 0.03*inch))
            story.append(Paragraph("<i>AAA standard requires 7:1 contrast ratio for enhanced accessibility</i>", small_style))
        except:
            pass
    
    story.append(Spacer(1, 0.08*inch))
    
    # ========== TYPOGRAPHY CHART ==========
    story.append(Paragraph("Typography Metrics", heading_style))
    
    if 'typography_chart' in analysis_data and analysis_data['typography_chart'] is not None:
        try:
            analysis_data['typography_chart'].seek(0)
            img = Image(analysis_data['typography_chart'], width=5.5*inch, height=2.2*inch)
            story.append(img)
            story.append(Spacer(1, 0.03*inch))
        except:
            pass
    
    story.append(Spacer(1, 0.08*inch))
    
    # ========== READABILITY DETAILS ==========
    story.append(Paragraph("Readability & Content Analysis", heading_style))
    
    readability = analysis_data.get('readability', {})
    
    readability_text = f"""
    <b>Flesch Reading Ease:</b> {readability.get('flesch_ease', 'N/A')} 
    (90-100=Very Easy | 60-70=Easy | 50-60=Moderate | Below 50=Difficult)<br/>
    <b>Flesch-Kincaid Grade:</b> {readability.get('fk_grade', 'N/A')}<br/>
    <br/>
    <b>Best Practices:</b><br/>
    • Keep sentences under 20 words average<br/>
    • Use minimum 16px font size for body text<br/>
    • Maintain line-height between 1.5-1.6x<br/>
    • Break paragraphs into smaller chunks<br/>
    • Use clear heading hierarchy (H1 → H6)
    """
    story.append(Paragraph(readability_text, small_style))
    story.append(Spacer(1, 0.1*inch))
    
    # ========== RECOMMENDATIONS ==========
    story.append(Paragraph("Actionable Recommendations", heading_style))
    
    recs = analysis_data.get('recommendations', [])
    recs_text = ""
    for i, rec in enumerate(recs[:30], 1):
        recs_text += f"<b>{i}.</b> {rec}<br/>"
    
    story.append(Paragraph(recs_text, small_style))
    story.append(Spacer(1, 0.1*inch))
    
    # ========== WCAG GUIDELINES ==========
    story.append(Paragraph("WCAG 2.1 Compliance Guidelines", heading_style))
    
    wcag_text = """
    <b>Four Core Principles (POUR):</b><br/>
    <b>1. Perceivable:</b> Information must be presentable to all users<br/>
    <b>2. Operable:</b> Interface must be operable by all users<br/>
    <b>3. Understandable:</b> Content and operations must be clear<br/>
    <b>4. Robust:</b> Compatible with assistive technologies<br/>
    <br/>
    <b>Contrast Standards:</b><br/>
    • Level A: 3:1 minimum<br/>
    • Level AA: 4.5:1 for normal text, 3:1 for large text<br/>
    • Level AAA: 7:1 for normal text, 4.5:1 for large text<br/>
    <br/>
    <b>Implementation Checklist:</b><br/>
    ✓ Add alt text to all images<br/>
    ✓ Use semantic HTML5 elements<br/>
    ✓ Ensure keyboard navigation works<br/>
    ✓ Provide focus indicators<br/>
    ✓ Test with screen readers (NVDA, JAWS)<br/>
    ✓ Maintain consistent navigation<br/>
    ✓ Use proper heading hierarchy
    """
    story.append(Paragraph(wcag_text, small_style))
    story.append(Spacer(1, 0.1*inch))
    
    # ========== IMPLEMENTATION PLAN ==========
    story.append(Paragraph("Priority Action Plan", heading_style))
    
    action_plan = f"""
    <b>Priority 1 - Critical (Fix Immediately):</b><br/>
    • Fix {issues_count} contrast issues to meet WCAG AA (4.5:1)<br/>
    • Test color combinations with color-blind simulators<br/>
    • Ensure all interactive elements are keyboard accessible<br/>
    <br/>
    <b>Priority 2 - Content Quality (Next Phase):</b><br/>
    • Readability: Flesch Ease {flesch} (Grade {fk_grade})<br/>
    • Simplify complex sentences, add subheadings<br/>
    • Increase whitespace between sections<br/>
    <br/>
    <b>Priority 3 - Comprehensive Audit (Extended):</b><br/>
    • Add missing alt text to images<br/>
    • Implement proper heading hierarchy<br/>
    • Associate form labels correctly<br/>
    • Test with multiple assistive technologies<br/>
    <br/>
    <b>Testing Tools:</b><br/>
    • WAVE (WebAIM): https://wave.webaim.org/<br/>
    • Axe DevTools: Browser extension<br/>
    • NVDA Screen Reader: Free download<br/>
    • Color Contrast Analyzer: Desktop app<br/>
    • Lighthouse: Built into Chrome DevTools
    """
    story.append(Paragraph(action_plan, small_style))
    story.append(Spacer(1, 0.1*inch))
    
    # ========== FOOTER & RESOURCES ==========
    story.append(Paragraph("Resources & Next Steps", heading_style))
    
    footer_text = f"""
    <b>Report Summary:</b><br/>
    Website: {analysis_data.get('url', 'N/A')}<br/>
    Date: {analysis_data.get('timestamp', 'N/A')}<br/>
    Overall Score: {score}/100 | Issues: {issues_count} | Grade Level: {fk_grade}<br/>
    <br/>
    <b>Recommended Next Steps:</b><br/>
    1. Fix all contrast issues (minimum 4.5:1 ratio)<br/>
    2. Improve content readability (aim for 60+ Flesch score)<br/>
    3. Test manually with keyboard navigation<br/>
    4. Use screen reader software (NVDA/JAWS)<br/>
    5. Re-run this analysis after fixes<br/>
    <br/>
    <b>Learn More:</b><br/>
    • WCAG 2.1: https://www.w3.org/WAI/WCAG21/<br/>
    • WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/<br/>
    • Accessible Colors: https://accessible-colors.com/<br/>
    • A11Y Project: https://www.a11yproject.com/<br/>
    <br/>
    <i>Report generated by Vision Chroma pro Professional Edition | © 2025 Vision Chroma pro</i>
    """
    
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_LEFT,
        textColor=colors.grey
    )))
    
    # Build PDF
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer