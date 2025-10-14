from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
import os

def generate_pdf_report(output_path, site_url, access_report, read_report, heatmap_path, color_images):
    c = canvas.Canvas(output_path, pagesize=A4)
    W, H = A4
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#0047AB"))
    c.drawString(30, H-50, "Vision Chroma pro — Accessibility Report")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(30, H-70, f"Website: {site_url}")
    y = H-110
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, "Accessibility Summary")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Score: {access_report.get('score')}/100")
    y -= 12
    c.drawString(40, y, f"Avg contrast: {access_report.get('avg_contrast')}")
    y -= 12
    c.drawString(40, y, f"Missing alt images: {len(access_report['features'].get('missing_alt',[]))}")
    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, "Readability")
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Flesch-Kincaid Grade: {read_report.get('fk_grade')}")
    y -= 30
    if heatmap_path and os.path.exists(heatmap_path):
        try:
            c.drawImage(heatmap_path, 30, y-180, width=220, height=120)
            c.drawString(260, y-50, "Estimated Heatmap")
            y -= 140
        except:
            pass
    x = 30
    if color_images:
        for name, path in color_images.items():
            if os.path.exists(path):
                try:
                    c.drawImage(path, x, y-80, width=60, height=30)
                    c.drawString(x, y-90, name)
                    x += 70
                except:
                    pass
    y -= 100
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, "Recommendations")
    y -= 16
    c.setFont("Helvetica", 10)
    recs = access_report.get('recommendations', []) + ["Improve content clarity where FK grade is high."]
    for r in recs:
        c.drawString(40, y, "- " + r)
        y -= 12
        if y < 80:
            c.showPage()
            y = H-80
    c.showPage()
    c.save()
    return output_path
