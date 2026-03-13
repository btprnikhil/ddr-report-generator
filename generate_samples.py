"""
Generate sample inspection and thermal report PDFs with embedded images.
Images are programmatically generated to simulate real thermal camera output
and site inspection photographs.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, Image as RLImage)
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from PIL import Image, ImageDraw
import io


def make_thermal_image(title, width=400, height=280, mode="hot"):
    """Generate a realistic-looking FLIR thermal camera image using gradient bands."""
    img = Image.new("RGB", (width, height), (20, 0, 30))
    draw = ImageDraw.Draw(img)

    if mode == "hot":
        # Dark purple/blue background (cool areas)
        draw.rectangle([0, 0, width, height], fill=(18, 0, 35))
        # Warm zones - orange/red gradient bands radiating from hotspot
        cx, cy = int(width * 0.65), int(height * 0.4)
        # Draw concentric filled ellipses from outside in (cool to hot)
        for r, col in [
            (160, (80, 0, 80)),   # purple
            (130, (140, 0, 60)),  # dark red
            (100, (200, 20, 0)),  # red
            (75,  (230, 80, 0)),  # orange-red
            (50,  (255, 140, 0)), # orange
            (30,  (255, 220, 0)), # yellow
            (15,  (255, 255, 180)), # near white
        ]:
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=col)
        # Cooler surrounding areas
        draw.rectangle([0, 0, int(width*0.2), height], fill=(25, 0, 55))
        draw.rectangle([0, int(height*0.7), width, height], fill=(30, 0, 50))

    elif mode == "moisture":
        # Warm background (wall ambient temperature - greenish)
        draw.rectangle([0, 0, width, height], fill=(60, 90, 50))
        # Moisture cold spots - blue/purple patches
        draw.rectangle([0, 0, width, height], fill=(55, 85, 48))
        # Cold moisture patches
        for cx, cy, rx, ry, col in [
            (int(width*0.25), int(height*0.5), 70, 55, (30, 40, 160)),   # main cold patch
            (int(width*0.7),  int(height*0.35), 55, 45, (40, 50, 150)),  # second patch
            (int(width*0.15), int(height*0.75), 40, 30, (35, 45, 155)),  # floor cold
        ]:
            draw.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=col)
            # Inner colder core
            draw.ellipse([cx-rx//2, cy-ry//2, cx+rx//2, cy+ry//2], fill=(20, 25, 180))
        # Transition zones
        draw.rectangle([0, int(height*0.6), int(width*0.45), height], fill=(45, 65, 100))

    elif mode == "roof":
        # Hot roof background - orange/red (sun heated surface)
        draw.rectangle([0, 0, width, height], fill=(180, 80, 10))
        # Hottest areas at membrane bubbles
        for cx, cy, rx, ry in [
            (int(width*0.3),  int(height*0.4), 80, 60),
            (int(width*0.7),  int(height*0.6), 65, 50),
        ]:
            draw.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=(220, 130, 0))
            draw.ellipse([cx-rx//2, cy-ry//2, cx+rx//2, cy+ry//2], fill=(255, 180, 20))
            draw.ellipse([cx-rx//4, cy-ry//4, cx+rx//4, cy+ry//4], fill=(255, 230, 80))
        # Cooler drain area
        draw.ellipse([int(width*0.75), int(height*0.15), int(width*0.9), int(height*0.38)],
                     fill=(100, 60, 120))
        # Missing joint - very hot strip
        draw.rectangle([0, int(height*0.45), int(width*0.12), int(height*0.65)],
                       fill=(255, 200, 30))

    else:  # general - first floor insulation
        # Neutral green background (ambient room temp)
        draw.rectangle([0, 0, width, height], fill=(50, 110, 60))
        # Cold infiltration at window seals (blue patches)
        draw.rectangle([int(width*0.05), int(height*0.2), int(width*0.22), int(height*0.8)],
                       fill=(40, 50, 160))
        draw.rectangle([int(width*0.55), int(height*0.25), int(width*0.72), int(height*0.75)],
                       fill=(45, 55, 155))
        # Warm conduit (orange strip)
        draw.rectangle([int(width*0.3), int(height*0.4), int(width*0.85), int(height*0.55)],
                       fill=(200, 120, 30))
        # AC unit warm patch
        draw.ellipse([int(width*0.35), int(height*0.05), int(width*0.6), int(height*0.3)],
                     fill=(180, 100, 20))

    draw = ImageDraw.Draw(img)

    # Draw color scale bar on right side
    bar_x = width - 22
    for i in range(height - 40):
        t = i / (height - 40)
        if t < 0.25:
            sr, sg, sb = int(t * 4 * 120), 0, int(150 - t * 4 * 150)
        elif t < 0.5:
            tt = (t - 0.25) * 4
            sr, sg, sb = int(120 + tt * 135), 0, 0
        elif t < 0.75:
            tt = (t - 0.5) * 4
            sr, sg, sb = 255, int(tt * 200), 0
        else:
            tt = (t - 0.75) * 4
            sr, sg, sb = 255, int(200 + tt * 55), int(tt * 255)
        draw.rectangle([bar_x, 20 + i, bar_x + 12, 21 + i],
                        fill=(max(0,min(255,sr)), max(0,min(255,sg)), max(0,min(255,sb))))

    # FLIR-style header/footer bars
    draw.rectangle([0, 0, width-1, height-1], outline=(60, 60, 60), width=2)
    draw.rectangle([0, 0, width-1, 18], fill=(20, 20, 20))
    draw.rectangle([0, height-18, width-1, height-1], fill=(20, 20, 20))
    draw.text((6, 3), f"FLIR E86  |  {title[:38]}", fill=(200, 200, 200))
    draw.text((6, height - 14), "Emissivity: 0.95  |  Greenfield Complex  |  10-Mar-2025", fill=(150, 150, 150))

    # Annotations per mode
    if mode == "hot":
        draw.ellipse([int(width*0.55), int(height*0.28), int(width*0.78), int(height*0.52)],
                     outline=(255, 255, 100), width=2)
        draw.text((int(width*0.52), int(height*0.17)), "MAX: 52.3 C", fill=(255, 255, 100))
        draw.text((int(width*0.05), int(height*0.85)), "MIN: 27.5 C", fill=(100, 180, 255))
    elif mode == "moisture":
        draw.ellipse([int(width*0.1), int(height*0.3), int(width*0.42), int(height*0.7)],
                     outline=(100, 200, 255), width=2)
        draw.text((int(width*0.08), int(height*0.2)), "COLD: 21.2 C", fill=(100, 200, 255))
        draw.text((int(width*0.5), int(height*0.8)), "AMB: 25.8 C", fill=(200, 200, 100))
    elif mode == "roof":
        draw.ellipse([int(width*0.17), int(height*0.22), int(width*0.45), int(height*0.58)],
                     outline=(255, 180, 50), width=2)
        draw.text((int(width*0.17), int(height*0.12)), "HOT: 41.5 C", fill=(255, 200, 50))
        draw.text((int(width*0.5), int(height*0.8)), "REF: 31.0 C", fill=(200, 200, 100))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def make_inspection_photo(title, issue_type="crack", width=400, height=280):
    """Generate a realistic-looking site inspection photograph simulation."""

    if issue_type == "crack":
        # Solid concrete gray wall background
        img = Image.new("RGB", (width, height), (162, 157, 152))
        draw = ImageDraw.Draw(img)
        # Slightly darker lower section for depth
        draw.rectangle([0, height//2, width, height], fill=(148, 143, 138))
        # Mortar joint lines (horizontal)
        for hy in range(40, height - 20, 35):
            draw.line([(0, hy), (width, hy)], fill=(130, 125, 120), width=1)
        # Mortar joint lines (vertical, offset per row)
        for row, hy in enumerate(range(40, height - 20, 35)):
            offset = 60 if row % 2 == 0 else 0
            for hx in range(offset, width, 80):
                draw.line([(hx, hy), (hx, hy + 35)], fill=(130, 125, 120), width=1)
        # Main crack - dark jagged line
        pts = [(80, 40), (95, 80), (88, 120), (102, 160), (115, 200), (108, 240)]
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i+1]], fill=(55, 50, 45), width=3)
        # Secondary crack
        pts2 = [(200, 60), (212, 100), (225, 145), (218, 185)]
        for i in range(len(pts2) - 1):
            draw.line([pts2[i], pts2[i+1]], fill=(65, 60, 55), width=2)
        # Third crack
        pts3 = [(300, 100), (308, 140), (295, 180)]
        for i in range(len(pts3) - 1):
            draw.line([pts3[i], pts3[i+1]], fill=(60, 55, 50), width=1)

    elif issue_type == "seepage":
        # Solid wall - upper dry section, lower wet/damp section
        img = Image.new("RGB", (width, height), (158, 155, 150))
        draw = ImageDraw.Draw(img)
        # Wet lower wall - darker and slightly blue-green tint
        draw.rectangle([0, int(height * 0.38), width, height], fill=(118, 128, 122))
        # Waterline boundary
        draw.line([(0, int(height * 0.38)), (width, int(height * 0.38))], fill=(95, 108, 100), width=2)
        # Efflorescence (white mineral deposits)
        for px, py, pr in [(120, 155, 28), (200, 188, 20), (278, 168, 24), (158, 222, 16), (240, 235, 12), (330, 195, 10)]:
            draw.ellipse([px-pr, py-pr, px+pr, py+pr], fill=(218, 215, 205), outline=(188, 185, 175))
        # Water streak marks
        for sx in [95, 155, 225, 285, 340]:
            draw.line([(sx, int(height*0.3)), (sx + 8, int(height*0.85))], fill=(85, 105, 128), width=2)
        # Standing water at bottom
        draw.rectangle([0, int(height * 0.88), width, height - 20], fill=(100, 118, 135))

    elif issue_type == "spalling":
        # Solid concrete background
        img = Image.new("RGB", (width, height), (155, 148, 142))
        draw = ImageDraw.Draw(img)
        # Wall grid lines
        for hy in range(30, height, 40):
            draw.line([(0, hy), (width, hy)], fill=(138, 132, 126), width=1)
        # Spalled area - dark irregular patch where concrete has fallen off
        draw.polygon([(145, 88), (262, 82), (275, 185), (138, 198)], fill=(88, 82, 75))
        # Exposed rebar - orange/rust colored bars
        draw.line([(150, 125), (268, 123)], fill=(165, 82, 35), width=6)
        draw.line([(155, 150), (262, 153)], fill=(152, 75, 30), width=4)
        draw.line([(152, 172), (255, 175)], fill=(142, 68, 28), width=3)
        # Rebar rust stains
        for rx in [160, 190, 220, 250]:
            draw.rectangle([rx, 178, rx+8, 200], fill=(140, 90, 60))
        # Crack lines radiating from spall
        draw.line([(145, 88), (110, 55)], fill=(70, 65, 60), width=2)
        draw.line([(262, 82), (295, 50)], fill=(70, 65, 60), width=2)
        draw.line([(275, 185), (300, 210)], fill=(70, 65, 60), width=1)

    elif issue_type == "membrane":
        # Roof surface - dark gray/charcoal flat roof
        img = Image.new("RGB", (width, height), (82, 78, 72))
        draw = ImageDraw.Draw(img)
        # Roof texture - slightly varied areas
        draw.rectangle([0, 0, width//2, height//2], fill=(78, 74, 68))
        draw.rectangle([width//2, height//2, width, height], fill=(86, 82, 76))
        # Membrane bubbles - raised dome shapes with shadow
        for bx, by, br in [(118, 98, 42), (228, 128, 32), (298, 88, 27), (168, 178, 37), (258, 198, 22), (340, 150, 18)]:
            # Shadow
            draw.ellipse([bx-br+4, by-br+4, bx+br+4, by+br+4], fill=(55, 52, 48))
            # Bubble body
            draw.ellipse([bx-br, by-br, bx+br, by+br], fill=(115, 108, 95), outline=(145, 138, 118), width=2)
            # Highlight on bubble top
            draw.ellipse([bx-br//3, by-br//2, bx+br//3, by], fill=(135, 128, 112))
        # Crack lines in membrane
        draw.line([(50, 60), (150, 55), (180, 80)], fill=(50, 47, 43), width=2)
        draw.line([(300, 200), (380, 210), (395, 250)], fill=(50, 47, 43), width=2)
        # Drain area - circular
        draw.ellipse([320, 30, 370, 70], fill=(55, 52, 48), outline=(100, 95, 88), width=2)
        draw.text((325, 43), "DRAIN", fill=(150, 145, 135))

    elif issue_type == "panel":
        # Dark room background
        img = Image.new("RGB", (width, height), (38, 38, 40))
        draw = ImageDraw.Draw(img)
        # Panel enclosure box
        draw.rectangle([55, 38, 342, 242], fill=(78, 78, 83), outline=(118, 118, 123), width=2)
        # Circuit breakers - EP3 and EP4 are red/hot
        breaker_colors = [(98,98,103), (98,98,103), (178,58,38), (158,53,33), (128,98,98), (98,98,103)]
        for i, (bx, col) in enumerate(zip([88, 128, 168, 208, 248, 288], breaker_colors)):
            draw.rectangle([bx, 68, bx+28, 212], fill=col, outline=(58,58,63), width=1)
            # Breaker switch
            draw.rectangle([bx+6, 85, bx+22, 105], fill=(60,60,65))
            draw.text((bx+3, 215), f"EP-{i+1}", fill=(178,178,178))
        # Heat discoloration glow around EP3/EP4
        draw.ellipse([152, 52, 242, 235], outline=(198, 118, 38), width=3)
        draw.ellipse([158, 58, 236, 228], outline=(180, 100, 30), width=1)
        draw.text((155, 30), "HOTSPOT", fill=(255, 200, 50))

    # Recreate draw object to ensure it's bound to final img state
    draw = ImageDraw.Draw(img)

    # Photo border and labels
    draw.rectangle([0, 0, width-1, height-1], outline=(38, 38, 38), width=3)
    draw.rectangle([0, 0, width-1, 18], fill=(18, 18, 18))
    draw.rectangle([0, height-18, width-1, height-1], fill=(18, 18, 18))
    draw.text((6, 3), title[:48], fill=(248, 248, 248))
    draw.text((6, height - 14), "Greenfield Commercial Complex  |  Insp: 10-Mar-2025  |  CI-4892", fill=(155, 155, 155))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def create_inspection_report():
    doc = SimpleDocTemplate("sample_inspection_report.pdf", pagesize=A4,
                            rightMargin=55, leftMargin=55, topMargin=60, bottomMargin=60)
    styles = getSampleStyleSheet()

    title_s  = ParagraphStyle('TS', parent=styles['Heading1'], fontSize=16, spaceAfter=6, alignment=TA_CENTER, textColor=colors.HexColor('#1a1a2e'))
    h2       = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13, spaceAfter=4, textColor=colors.HexColor('#16213e'))
    h3       = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=11, spaceAfter=4, textColor=colors.HexColor('#0f3460'))
    body     = ParagraphStyle('BD', parent=styles['Normal'], fontSize=10, spaceAfter=5, leading=14)
    caption  = ParagraphStyle('CP', parent=styles['Normal'], fontSize=8, spaceAfter=8, textColor=colors.grey, alignment=TA_CENTER)

    story = [
        Paragraph("SITE INSPECTION REPORT", title_s),
        Paragraph("Property: Greenfield Commercial Complex, Block B", body),
        Paragraph("Inspection Date: March 10, 2025", body),
        Paragraph("Inspector: Rajesh Kumar, B.Tech Civil | Reg. No. CI-4892", body),
        HRFlowable(width="100%", thickness=1, color=colors.grey),
        Spacer(1, 10),
        Paragraph("1. EXECUTIVE SUMMARY", h2),
        Paragraph(
            "A comprehensive site inspection was conducted at Greenfield Commercial Complex, Block B. "
            "Multiple structural and non-structural deficiencies were observed across different zones. "
            "The building is approximately 8 years old and shows signs of deferred maintenance. "
            "Immediate attention is recommended for water ingress issues in the basement and roof terrace. "
            "The electrical panel room shows signs of critical heat buildup requiring urgent action. "
            "Overall structural integrity appears adequate but requires close monitoring.", body),
        Spacer(1, 8),
        Paragraph("2. AREA-WISE OBSERVATIONS", h2),
    ]

    sections = [
        {
            "title": "2.1 Basement / Parking Level",
            "points": [
                "Active water seepage observed along the north and east retaining walls.",
                "Efflorescence deposits visible at multiple locations indicating chronic moisture infiltration.",
                "Floor drainage channels partially blocked with debris; standing water observed in NE corner.",
                "Concrete spalling detected near column B-4 and B-7 with exposed rebar (approx. 15cm).",
                "Damp patches approximately 2m x 1.5m on the north wall - surface treatment has failed.",
                "Cracks in floor slab: hairline cracks (0.1-0.2mm width) across 30% of floor area.",
                "Musty odor present - indicative of long-term moisture retention.",
            ],
            "images": [
                ("seepage", "Fig 1.1 - Active water seepage and efflorescence, North Retaining Wall, Basement"),
                ("spalling", "Fig 1.2 - Concrete spalling with exposed rebar at Column B-4, Basement"),
            ]
        },
        {
            "title": "2.2 Ground Floor - Lobby and Reception",
            "points": [
                "Ceiling tiles showing water stains at zones G-2 and G-5.",
                "Paint peeling on east corridor walls over approximately 15 sq. meters.",
                "Minor settlement cracks (diagonal) at window jambs - assessed as non-structural.",
                "HVAC duct condensation dripping onto flooring near reception counter.",
                "Flooring tiles cracked at 3 locations near main entrance - trip hazard noted.",
                "No immediate structural concern on this floor.",
            ],
            "images": [
                ("crack", "Fig 2.1 - Settlement crack at window jamb, Ground Floor Lobby"),
            ]
        },
        {
            "title": "2.3 First Floor - Office Spaces",
            "points": [
                "Partition wall joints showing gaps of 3-5mm - possible thermal movement or settlement.",
                "False ceiling panels sagging in conference room CF-1 (approximately 4 panels).",
                "Air conditioning unit near window W-12 leaking condensate onto wall - staining visible.",
                "Electrical conduit exposed and improperly secured along east corridor (2.4m unsupported).",
                "Window seals deteriorated in offices O-3, O-5, O-7 - potential water ingress risk.",
                "Minor water stain on south wall of office O-9 - source unclear.",
            ],
            "images": []
        },
        {
            "title": "2.4 Roof Terrace",
            "points": [
                "Waterproofing membrane bubbling and cracked across approximately 40% of terrace area.",
                "Parapet wall coping stones displaced at two locations on south side - safety concern.",
                "Drain outlets blocked with leaves and debris - ponding water evidence on east section.",
                "Solar panel mounting brackets showing surface rust - likely due to inadequate coating.",
                "One expansion joint filler completely missing on the west terrace section.",
                "Overall waterproofing system appears to have exceeded its service life.",
            ],
            "images": [
                ("membrane", "Fig 4.1 - Waterproofing membrane bubbling, Roof Terrace Zone R2"),
            ]
        },
        {
            "title": "2.5 Electrical Panel Room (Ground Floor)",
            "points": [
                "Unusually high ambient temperature noted inside panel room (approx. 38 deg C vs expected 28 deg C).",
                "Main distribution board showing heat discoloration on outer casing.",
                "Cable insulation on circuits EP-3 and EP-7 shows early signs of heat degradation.",
                "Ventilation louvers blocked - airflow severely restricted.",
                "No fire suppression system installed in panel room - compliance concern.",
                "Panel room door seal inadequate - dust ingress observed.",
            ],
            "images": [
                ("panel", "Fig 5.1 - Electrical panel showing heat discoloration, circuits EP-3 and EP-7"),
            ]
        },
    ]

    for section in sections:
        story.append(Paragraph(section["title"], h3))
        for point in section["points"]:
            story.append(Paragraph(f"- {point}", body))
        story.append(Spacer(1, 6))
        for img_type, img_caption in section["images"]:
            img_buf = make_inspection_photo(img_caption, issue_type=img_type)
            story.append(RLImage(img_buf, width=3.8*inch, height=2.6*inch))
            story.append(Paragraph(img_caption, caption))
            story.append(Spacer(1, 6))

    story.append(Paragraph("3. GENERAL NOTES", h2))
    for note in [
        "Inspection conducted during daylight hours (09:00-15:00); some areas had limited artificial lighting.",
        "Roof access was partially restricted due to ongoing solar panel maintenance work.",
        "Maintenance records were not made available at the time of inspection.",
        "Age of waterproofing treatment on roof terrace: unknown (records unavailable).",
        "Last electrical audit date: not confirmed by facility management.",
        "Building occupancy during inspection: approximately 60% - some areas inaccessible.",
    ]:
        story.append(Paragraph(f"- {note}", body))

    doc.build(story)
    print("sample_inspection_report.pdf created with 5 inspection images")


def create_thermal_report():
    doc = SimpleDocTemplate("sample_thermal_report.pdf", pagesize=A4,
                            rightMargin=55, leftMargin=55, topMargin=60, bottomMargin=60)
    styles = getSampleStyleSheet()

    title_s  = ParagraphStyle('TS', parent=styles['Heading1'], fontSize=16, spaceAfter=6, alignment=TA_CENTER, textColor=colors.HexColor('#1a1a2e'))
    h2       = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13, spaceAfter=4, textColor=colors.HexColor('#16213e'))
    h3       = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=11, spaceAfter=4, textColor=colors.HexColor('#0f3460'))
    body     = ParagraphStyle('BD', parent=styles['Normal'], fontSize=10, spaceAfter=5, leading=14)
    caption  = ParagraphStyle('CP', parent=styles['Normal'], fontSize=8, spaceAfter=8, textColor=colors.grey, alignment=TA_CENTER)

    story = [
        Paragraph("THERMAL IMAGING INSPECTION REPORT", title_s),
        Paragraph("Property: Greenfield Commercial Complex, Block B", body),
        Paragraph("Thermal Scan Date: March 10, 2025", body),
        Paragraph("Thermographer: Anita Sharma | ASNT Level II Thermographer", body),
        Paragraph("Equipment: FLIR E86 Thermal Camera | Emissivity: 0.95", body),
        HRFlowable(width="100%", thickness=1, color=colors.grey),
        Spacer(1, 10),
        Paragraph("1. THERMAL SCAN SUMMARY", h2),
        Paragraph(
            "Thermal imaging was conducted simultaneously with the visual inspection. "
            "The scan identified significant heat anomalies in the electrical panel room, "
            "moisture-related thermal signatures in the basement and roof terrace, "
            "and insulation deficiencies in first-floor office areas. "
            "All temperature readings are in degrees Celsius. Ambient temperature during scan: 27 deg C.", body),
        Spacer(1, 8),
        Paragraph("2. THERMAL FINDINGS BY AREA", h2),
    ]

    findings = [
        {
            "area": "2.1 Electrical Panel Room - Critical Anomalies",
            "mode": "hot",
            "caption": "Thermal Image T1.1 - Electrical Panel Room: Critical hotspot at EP-3 (52.3 deg C)",
            "table": [
                ["Component", "Min Temp (C)", "Max Temp (C)", "Delta T vs Ambient", "Risk Level"],
                ["Main Distribution Board", "31.2", "47.8", "+20.8 C", "CRITICAL"],
                ["Circuit EP-3 Breaker", "29.5", "52.3", "+25.3 C", "CRITICAL"],
                ["Circuit EP-7 Busbar", "28.8", "44.1", "+17.1 C", "HIGH"],
                ["Cable Tray - South Wall", "27.9", "36.4", "+9.4 C", "MODERATE"],
                ["Neutral Bus Bar", "27.5", "31.2", "+4.2 C", "LOW"],
            ],
            "notes": [
                "Circuit EP-3 shows highest anomaly (Delta T = +25.3 C) - immediate shutdown recommended.",
                "Main board outer casing at 47.8 C confirms internal connection failure or overload.",
                "Thermal pattern consistent with loose connections or undersized conductors.",
                "Hotspot on EP-3 aligns with visual observation of insulation degradation.",
            ]
        },
        {
            "area": "2.2 Basement - Moisture Thermal Signatures",
            "mode": "moisture",
            "caption": "Thermal Image T2.1 - Basement North Wall: Cold patches confirming active moisture infiltration",
            "table": [
                ["Location", "Surface Temp (C)", "Surrounding Temp (C)", "Delta T", "Interpretation"],
                ["North Wall - NW Corner", "22.1", "25.8", "-3.7 C", "Active moisture"],
                ["East Retaining Wall - Mid", "23.4", "26.1", "-2.7 C", "Moisture ingress"],
                ["Column B-4 Base", "21.8", "25.5", "-3.7 C", "Saturated concrete"],
                ["Column B-7 Base", "22.6", "25.7", "-3.1 C", "Moisture present"],
                ["Floor - NE Corner", "21.2", "25.3", "-4.1 C", "Standing water / wet slab"],
            ],
            "notes": [
                "Cool thermal signatures (negative Delta T) confirm active water infiltration at multiple points.",
                "NE corner floor shows lowest temperature - consistent with visual standing water observation.",
                "Columns B-4 and B-7 base saturation increases spalling and structural degradation risk.",
            ]
        },
        {
            "area": "2.3 Roof Terrace - Waterproofing Assessment",
            "mode": "roof",
            "caption": "Thermal Image T3.1 - Roof Terrace: Elevated temps at membrane bubble zones (41.5 deg C)",
            "table": [
                ["Zone", "Temp Range (C)", "Reference Temp (C)", "Observation"],
                ["West Terrace - Missing Joint", "38.2-41.5", "31.0", "Heat accumulation / no insulation"],
                ["Bubbled Membrane - Zone R2", "36.8-39.3", "31.0", "Air/moisture trapped under membrane"],
                ["Drain Outlet Area", "28.1-30.4", "31.0", "Possible moisture retention"],
                ["South Parapet - Displaced Coping", "32.5-34.8", "31.0", "Minor thermal bridge"],
            ],
            "notes": [
                "Bubbled membrane areas show elevated temperatures due to trapped air/moisture voids.",
                "Missing expansion joint (west side) creates direct thermal bridge.",
                "Drain area slightly cooler - consistent with visual ponding water observation.",
            ]
        },
        {
            "area": "2.4 First Floor - Insulation and HVAC",
            "mode": "general",
            "caption": "Thermal Image T4.1 - First Floor: Cold infiltration detected at window seals O-3 and O-5",
            "table": [
                ["Location", "Observed Temp (C)", "Expected Temp (C)", "Delta T", "Issue"],
                ["Window W-12 - AC Unit", "29.8", "27.0", "+2.8 C", "Condensate heat leak"],
                ["Conference Room CF-1 Ceiling", "28.4", "27.0", "+1.4 C", "Mild insulation gap"],
                ["Office O-3 Window Seal", "24.1", "27.0", "-2.9 C", "Cold infiltration / seal failure"],
                ["Office O-5 Window Seal", "23.8", "27.0", "-3.2 C", "Cold infiltration / seal failure"],
                ["East Corridor - Exposed Conduit", "30.2", "27.0", "+3.2 C", "Electrical heat emission"],
            ],
            "notes": [
                "Window seals in O-3 and O-5 show cold infiltration - confirms visual seal deterioration.",
                "Exposed conduit in east corridor emitting above-ambient heat - warrants urgent inspection.",
                "CF-1 ceiling insulation gap is minor but progressively worsening.",
            ]
        },
    ]

    for finding in findings:
        story.append(Paragraph(finding["area"], h3))
        thermal_buf = make_thermal_image(finding["caption"][:38], mode=finding["mode"])
        story.append(RLImage(thermal_buf, width=4.0*inch, height=2.8*inch))
        story.append(Paragraph(finding["caption"], caption))
        story.append(Spacer(1, 6))
        tbl = Table(finding["table"], repeatRows=1)
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f3460')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('FONTSIZE', (0,1), (-1,-1), 7.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('PADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 6))
        for note in finding["notes"]:
            story.append(Paragraph(f"- {note}", body))
        story.append(Spacer(1, 10))

    story.append(Paragraph("3. THERMAL SCAN NOTES", h2))
    for note in [
        "Scan conducted between 10:00-14:00 hours for optimal thermal contrast.",
        "Electrical panel room scan done with panel covers ON - internal anomalies inferred from surface readings.",
        "Roof terrace scan during peak solar hours - absolute temperatures elevated; Delta T comparisons used.",
        "Basement scan: no forced ventilation active during measurement.",
        "Ground floor lobby scan not completed - access temporarily restricted.",
        "Thermal images available in full-resolution FLIR format on request.",
        "Office O-7 window seal: scan inconclusive due to external glare - data not available.",
    ]:
        story.append(Paragraph(f"- {note}", body))

    doc.build(story)
    print("sample_thermal_report.pdf created with 4 thermal images")


if __name__ == "__main__":
    create_inspection_report()
    create_thermal_report()
    print("\nBoth sample documents ready with embedded images.")
    print("Inspection report: 5 images (seepage, spalling, crack, membrane, panel)")
    print("Thermal report: 4 thermal camera images (hot, moisture, roof, general)")