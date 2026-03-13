"""
DDR Report Generator — Full Pipeline
AI Intern Assessment | Ragha (Nikhil)

Stack: Streamlit + PyMuPDF + pytesseract + Ollama (llama3.1:8b) + ReportLab
"""

import streamlit as st
import fitz  # PyMuPDF
import requests
import json
import re
import io
import os
import tempfile
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from datetime import datetime

# ─── Tesseract path (Windows) ─────────────────────────────────────────────────
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# ─── Constants ────────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"
CHUNK_SIZE = 4000
CHUNK_OVERLAP = 300

# ══════════════════════════════════════════════════════════════════════════════
# 1. PDF EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_pdf_content(uploaded_file):
    """Extract text and images from uploaded PDF. Falls back to OCR if needed."""
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    full_text = []
    images = []

    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()

        # OCR fallback for scanned pages
        if len(text) < 50 and TESSERACT_AVAILABLE:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            try:
                text = pytesseract.image_to_string(img)
            except Exception:
                text = ""

        if text:
            full_text.append(f"[Page {page_num + 1}]\n{text}")

        # Extract images
        for img_index, img_ref in enumerate(page.get_images(full=True)):
            xref = img_ref[0]
            try:
                base_image = doc.extract_image(xref)
                img_bytes = base_image["image"]
                pil_img = Image.open(io.BytesIO(img_bytes))

                # Force RGB
                if pil_img.mode == "RGBA":
                    bg = Image.new("RGB", pil_img.size, (255, 255, 255))
                    bg.paste(pil_img, mask=pil_img.split()[3])
                    pil_img = bg
                elif pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")

                images.append({
                    "page": page_num + 1,
                    "index": img_index,
                    "image": pil_img,
                    "label": f"Fig {page_num + 1}.{img_index + 1} - Page {page_num + 1}"
                })
            except Exception:
                continue

    doc.close()
    return "\n\n".join(full_text), images


# ══════════════════════════════════════════════════════════════════════════════
# 2. CHUNKING
# ══════════════════════════════════════════════════════════════════════════════

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start >= len(text):
            break
    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# 3. OLLAMA AI CALL
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a building inspection AI. You will receive combined text from an Inspection Report AND a Thermal Report for the same property. Merge findings from BOTH reports and return ONLY a valid JSON object — no explanation, no markdown, no code fences.

JSON structure (fill ALL fields with real data from the reports):
{
  "property_summary": {
    "property_name": "extract from report header or document title",
    "inspection_date": "extract exact date from report, e.g. March 10, 2025",
    "inspector_name": "extract inspector/thermographer name from report",
    "overall_condition": "one sentence summary of overall building condition",
    "critical_issues_count": 0,
    "key_findings": [
      "finding 1 from report",
      "finding 2 from report",
      "finding 3 from report",
      "finding 4 from report",
      "finding 5 from report"
    ]
  },
  "area_observations": [
    {
      "area_name": "Basement / Parking Level",
      "observations": ["observation 1", "observation 2", "observation 3"],
      "severity": "Critical"
    },
    {
      "area_name": "Ground Floor - Lobby and Reception",
      "observations": ["observation 1", "observation 2", "observation 3"],
      "severity": "Low"
    },
    {
      "area_name": "First Floor - Office Spaces",
      "observations": ["observation 1", "observation 2", "observation 3"],
      "severity": "High"
    },
    {
      "area_name": "Roof Terrace",
      "observations": ["observation 1", "observation 2", "observation 3"],
      "severity": "High"
    },
    {
      "area_name": "Electrical Panel Room",
      "observations": ["observation 1", "observation 2", "observation 3"],
      "severity": "Critical"
    }
  ],
  "root_causes": [
    {
      "issue": "descriptive issue title",
      "cause": "root cause explanation",
      "evidence": "direct quote or specific data point from the report text"
    }
  ],
  "severity_assessment": [
    {
      "area": "Basement / Parking Level",
      "severity": "Critical",
      "reasoning": "specific reasoning from report findings",
      "thermal_confirmed": "Yes"
    },
    {
      "area": "Ground Floor - Lobby and Reception",
      "severity": "Low",
      "reasoning": "specific reasoning from report findings",
      "thermal_confirmed": "No"
    },
    {
      "area": "First Floor - Office Spaces",
      "severity": "High",
      "reasoning": "specific reasoning from report findings",
      "thermal_confirmed": "Partial"
    },
    {
      "area": "Roof Terrace",
      "severity": "High",
      "reasoning": "specific reasoning from report findings",
      "thermal_confirmed": "Yes"
    },
    {
      "area": "Electrical Panel Room",
      "severity": "Critical",
      "reasoning": "specific reasoning from report findings",
      "thermal_confirmed": "Yes"
    }
  ],
  "recommended_actions": [
    {
      "priority": "Immediate",
      "area": "area name",
      "action": "specific action to take",
      "estimated_cost": "cost estimate or 'Consult specialist'"
    }
  ],
  "additional_notes": ["note from report 1", "note from report 2"],
  "missing_information": [
    {
      "item": "missing data item",
      "source": "Inspection",
      "impact": "how this gap affects the report"
    }
  ]
}

STRICT RULES:
1. property_name: extract from the report — look for "Property:", building name, or document title. NEVER use "Unknown".
2. inspection_date: extract from the report — look for "Date:", "Inspection Date:", or any date mentioned. NEVER use "Unknown".
3. severity must ONLY be one of: Critical, High, Moderate, Low — never a list, never slash/pipe-separated.
4. area_observations MUST contain ALL FIVE areas listed above — combine inspection + thermal observations for each.
5. severity_assessment MUST contain ALL FIVE areas listed above — use the exact area names from the template.
6. critical_issues_count = count of areas where severity is Critical or High (computed automatically, fill in your count).
7. First Floor - Office Spaces severity must be High (exposed electrical conduit + heat emission is a High-risk hazard).
8. evidence field must contain a specific data point from the text (temperature reading, measurement, direct observation).
8. key_findings must have at least 5 real findings extracted from the reports.
9. Return ONLY the JSON object. No text before or after it.
"""

def call_ollama(text_chunk, progress_label=""):
    """Call Ollama llama3.1:8b and return parsed JSON."""
    prompt = f"Inspection/Thermal Report Text:\n\n{text_chunk}\n\nReturn the JSON DDR analysis now."

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nUser: {prompt}",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 4000,
            "num_ctx": 8192
        }
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
        resp.raise_for_status()
        raw = resp.json().get("response", "")

        # Strip markdown fences if present
        raw = re.sub(r"```(?:json)?", "", raw).strip()
        raw = raw.rstrip("`").strip()

        # Find JSON object
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        st.error(f"Ollama error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 4. MERGE CHUNKED RESULTS
# ══════════════════════════════════════════════════════════════════════════════

STANDARD_AREAS = [
    "Basement / Parking Level",
    "Ground Floor - Lobby and Reception",
    "First Floor - Office Spaces",
    "Roof Terrace",
    "Electrical Panel Room",
]

def merge_results(results):
    """Merge multiple chunk results into one consolidated DDR."""
    if not results:
        return None

    # Start with first valid result
    merged = None
    for r in results:
        if r:
            merged = json.loads(json.dumps(r))  # deep copy
            break
    if not merged:
        return None

    for r in results[1:]:
        if not r:
            continue

        # Fill in Unknown property_summary fields from later chunks
        prop = merged.get("property_summary", {})
        new_prop = r.get("property_summary", {})
        for field in ["property_name", "inspection_date", "inspector_name", "overall_condition"]:
            current = str(prop.get(field, "")).strip()
            new_val = str(new_prop.get(field, "")).strip()
            if (not current or current.lower() in ("unknown", "n/a", "")) and new_val and new_val.lower() not in ("unknown", "n/a", ""):
                prop[field] = new_val
        merged["property_summary"] = prop

        # Merge key findings (deduplicate)
        existing_findings = merged.get("property_summary", {}).get("key_findings", [])
        new_findings = new_prop.get("key_findings", [])
        merged["property_summary"]["key_findings"] = list(dict.fromkeys(existing_findings + new_findings))

        # Merge area_observations by area_name (combine observations, keep highest severity)
        SEV_RANK = {"Critical": 4, "High": 3, "Moderate": 2, "Low": 1}
        existing_areas = {a["area_name"]: a for a in merged.get("area_observations", [])}
        for new_area in r.get("area_observations", []):
            name = new_area.get("area_name", "")
            if name in existing_areas:
                # Merge observations
                existing_obs = existing_areas[name].get("observations", [])
                new_obs = new_area.get("observations", [])
                existing_areas[name]["observations"] = list(dict.fromkeys(existing_obs + new_obs))
                # Keep highest severity
                cur_sev = existing_areas[name].get("severity", "Low")
                new_sev = new_area.get("severity", "Low")
                if SEV_RANK.get(new_sev, 0) > SEV_RANK.get(cur_sev, 0):
                    existing_areas[name]["severity"] = new_sev
            else:
                existing_areas[name] = new_area
        merged["area_observations"] = list(existing_areas.values())

        # Merge severity_assessment by area name (keep highest severity)
        existing_sev = {s["area"]: s for s in merged.get("severity_assessment", [])}
        for new_s in r.get("severity_assessment", []):
            area = new_s.get("area", "")
            if area in existing_sev:
                cur_sev = existing_sev[area].get("severity", "Low")
                new_sev = new_s.get("severity", "Low")
                if SEV_RANK.get(new_sev, 0) > SEV_RANK.get(cur_sev, 0):
                    existing_sev[area] = new_s
            else:
                existing_sev[area] = new_s
        merged["severity_assessment"] = list(existing_sev.values())

        # Simple list merge for other sections
        for key in ["root_causes", "recommended_actions", "additional_notes", "missing_information"]:
            if key in r and isinstance(r[key], list):
                existing = merged.get(key, [])
                new_items = [item for item in r[key] if item not in existing]
                merged[key] = existing + new_items

    # Ensure all 5 standard areas present in area_observations
    existing_names = [a["area_name"] for a in merged.get("area_observations", [])]
    for std_area in STANDARD_AREAS:
        if not any(std_area.lower() in name.lower() or name.lower() in std_area.lower()
                   for name in existing_names):
            merged["area_observations"].append({
                "area_name": std_area,
                "observations": ["No observations recorded for this area."],
                "severity": "Low"
            })

    # Ensure all 5 standard areas in severity_assessment
    existing_sev_areas = [s["area"] for s in merged.get("severity_assessment", [])]
    for std_area in STANDARD_AREAS:
        if not any(std_area.lower() in a.lower() or a.lower() in std_area.lower()
                   for a in existing_sev_areas):
            # Try to find severity from area_observations
            sev = "Low"
            for ao in merged.get("area_observations", []):
                if std_area.lower() in ao.get("area_name", "").lower():
                    sev = ao.get("severity", "Low")
                    break
            merged["severity_assessment"].append({
                "area": std_area,
                "severity": sev,
                "reasoning": "Based on area observations.",
                "thermal_confirmed": "No"
            })

    # Order severity_assessment to match standard area order
    sev_dict = {}
    for s in merged.get("severity_assessment", []):
        sev_dict[s["area"]] = s
    ordered_sev = []
    for std in STANDARD_AREAS:
        for k, v in sev_dict.items():
            if std.lower() in k.lower() or k.lower() in std.lower():
                ordered_sev.append(v)
                break
    # Add any non-standard areas at end
    standard_lowers = [s.lower() for s in STANDARD_AREAS]
    for k, v in sev_dict.items():
        if not any(s in k.lower() or k.lower() in s for s in standard_lowers):
            ordered_sev.append(v)
    if ordered_sev:
        merged["severity_assessment"] = ordered_sev

    # Recompute critical_issues_count
    sev_list = merged.get("severity_assessment", [])
    merged["property_summary"]["critical_issues_count"] = len(
        [s for s in sev_list if s.get("severity") in ("Critical", "High")]
    )

    return merged


# ══════════════════════════════════════════════════════════════════════════════
# 5. IMAGE ↔ SECTION MATCHING
# ══════════════════════════════════════════════════════════════════════════════

AREA_KEYWORDS = {
    "basement": ["basement", "parking", "rebar", "seepage", "efflorescence"],
    "ground floor": ["ground", "lobby", "reception", "hvac", "corridor"],
    "first floor": ["first floor", "office", "window", "ceiling", "conduit"],
    "roof": ["roof", "terrace", "waterproof", "membrane", "drain", "parapet"],
    "electrical": ["electrical", "panel", "ep-3", "hotspot", "circuit", "board"],
}

def find_best_image_for_area(area_name, images, used_indices):
    """Match an image to an area by keyword scoring."""
    area_lower = area_name.lower()
    best_score = -1
    best_img = None
    best_idx = None

    for idx, img in enumerate(images):
        if idx in used_indices:
            continue
        score = 0
        label_lower = img["label"].lower()
        for key, keywords in AREA_KEYWORDS.items():
            if key in area_lower:
                for kw in keywords:
                    if kw in label_lower:
                        score += 2
        if img["page"] not in [i["page"] for i in [images[j] for j in used_indices]]:
            score += 1
        if score > best_score:
            best_score = score
            best_img = img
            best_idx = idx

    if best_img is None and images:
        # Fallback: first unused
        for idx, img in enumerate(images):
            if idx not in used_indices:
                return img, idx

    return best_img, best_idx


# ══════════════════════════════════════════════════════════════════════════════
# 6. PDF GENERATION (ReportLab)
# ══════════════════════════════════════════════════════════════════════════════

BRAND_BLUE = colors.HexColor("#1a3a5c")
BRAND_BLUE_LIGHT = colors.HexColor("#2c5282")
BRAND_ACCENT = colors.HexColor("#e8f0f7")
BRAND_ACCENT2 = colors.HexColor("#f0f5fb")
SEV_COLORS = {
    "Critical": colors.HexColor("#c0392b"),
    "High":     colors.HexColor("#d35400"),
    "Moderate": colors.HexColor("#b7950b"),
    "Low":      colors.HexColor("#1e8449"),
}
SEV_BG = {
    "Critical": colors.HexColor("#fdecea"),
    "High":     colors.HexColor("#fef0e6"),
    "Moderate": colors.HexColor("#fefde6"),
    "Low":      colors.HexColor("#e9f7ef"),
}

def build_ddr_pdf(ddr_data, all_images):
    """Build professional A4 PDF from DDR data."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=0.7*inch, rightMargin=0.7*inch,
        topMargin=0.65*inch, bottomMargin=0.65*inch
    )

    # ── Styles ───────────────────────────────────────────────────────────────
    title_s    = ParagraphStyle("title_s", fontSize=22, textColor=colors.white,
                                alignment=TA_CENTER, spaceAfter=2, fontName="Helvetica-Bold", leading=26)
    subtitle_s = ParagraphStyle("subtitle_s", fontSize=10, textColor=colors.HexColor("#c8ddf0"),
                                alignment=TA_CENTER, spaceAfter=0)
    h1_s       = ParagraphStyle("h1_s", fontSize=11, textColor=colors.white,
                                fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=5,
                                leftIndent=8, rightIndent=8, backColor=BRAND_BLUE, leading=16,
                                borderPad=4)
    h2_s       = ParagraphStyle("h2_s", fontSize=10.5, textColor=BRAND_BLUE,
                                fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3,
                                borderPad=2)
    body_s     = ParagraphStyle("body_s", fontSize=9, leading=14, spaceAfter=3,
                                alignment=TA_JUSTIFY)
    bullet_s   = ParagraphStyle("bullet_s", fontSize=9, leading=13, spaceAfter=2,
                                leftIndent=14)
    caption_s  = ParagraphStyle("caption_s", fontSize=7.5, textColor=colors.HexColor("#555555"),
                                alignment=TA_CENTER, spaceAfter=6, fontName="Helvetica-Oblique")
    label_s    = ParagraphStyle("label_s", fontSize=8, textColor=BRAND_BLUE,
                                fontName="Helvetica-Bold")
    value_s    = ParagraphStyle("value_s", fontSize=9, fontName="Helvetica", leading=13)
    footer_s   = ParagraphStyle("footer_s", fontSize=7.5, textColor=colors.HexColor("#888888"),
                                alignment=TA_CENTER)
    cell_s     = ParagraphStyle("cell_s", fontSize=8, leading=11)
    cell_sm_s  = ParagraphStyle("cell_sm_s", fontSize=7.5, leading=11)

    story = []
    prop = ddr_data.get("property_summary", {})

    # ── HEADER BANNER ────────────────────────────────────────────────────────
    # Blue banner table
    header_data = [[
        Paragraph("DETAILED DIAGNOSTIC REPORT", title_s),
    ]]
    header_table = Table(header_data, colWidths=[7.1*inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)

    sub_data = [[Paragraph("Building Assessment and Recommendations", subtitle_s)]]
    sub_table = Table(sub_data, colWidths=[7.1*inch])
    sub_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BRAND_BLUE_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(sub_table)
    story.append(Spacer(1, 0.12*inch))

    # ── META TABLE ──────────────────────────────────────────────────────────
    crit_count = prop.get("critical_issues_count", 0)
    inspector  = prop.get("inspector_name", "N/A")
    crit_str   = f"<b>{crit_count}</b>" if crit_count == 0 else f"<font color='#c0392b'><b>{crit_count}</b></font>"

    meta_data = [
        [Paragraph("<b>Property</b>", label_s),
         Paragraph(prop.get("property_name", "N/A"), value_s),
         Paragraph("<b>Inspection Date</b>", label_s),
         Paragraph(prop.get("inspection_date", "N/A"), value_s)],
        [Paragraph("<b>Inspector</b>", label_s),
         Paragraph(inspector, value_s),
         Paragraph("<b>Critical Issues</b>", label_s),
         Paragraph(crit_str, value_s)],
        [Paragraph("<b>Overall Condition</b>", label_s),
         Paragraph(prop.get("overall_condition", "N/A"), value_s),
         Paragraph("<b>Report Generated</b>", label_s),
         Paragraph(datetime.now().strftime("%d %B %Y"), value_s)],
    ]
    meta_table = Table(meta_data, colWidths=[1.4*inch, 2.5*inch, 1.35*inch, 1.85*inch])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), BRAND_ACCENT2),
        ("BACKGROUND",  (0, 0), (0, -1), BRAND_ACCENT),
        ("BACKGROUND",  (2, 0), (2, -1), BRAND_ACCENT),
        ("BOX",         (0, 0), (-1, -1), 1.0, BRAND_BLUE),
        ("LINEBELOW",   (0, 0), (-1, -2), 0.3, colors.HexColor("#b0c8e0")),
        ("INNERGRID",   (0, 0), (-1, -1), 0.3, colors.HexColor("#c0d4e8")),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0),(-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.15*inch))

    # ── SECTION 1: PROPERTY ISSUE SUMMARY ───────────────────────────────────
    story.append(Paragraph("1. PROPERTY ISSUE SUMMARY", h1_s))
    key_findings = prop.get("key_findings", [])
    valid_findings = [f for f in key_findings if f and str(f).strip()]
    if valid_findings:
        for f in valid_findings:
            story.append(Paragraph(f"• {f}", bullet_s))
    else:
        story.append(Paragraph("• No key findings extracted from the provided documents.", bullet_s))
    story.append(Spacer(1, 0.1*inch))

    # ── SECTION 2: AREA-WISE OBSERVATIONS ───────────────────────────────────
    story.append(Paragraph("2. AREA-WISE OBSERVATIONS", h1_s))
    areas = ddr_data.get("area_observations", [])
    used_image_indices = set()

    for i, area in enumerate(areas):
        area_name = area.get("area_name", f"Area {i+1}")
        sev = area.get("severity", "Low")
        sev_color = SEV_COLORS.get(sev, colors.grey)
        sev_bg    = SEV_BG.get(sev, colors.white)

        # Area header with inline severity badge
        area_header_data = [[
            Paragraph(f"<b>2.{i+1}  {area_name}</b>",
                      ParagraphStyle("ah", fontSize=10.5, textColor=BRAND_BLUE,
                                     fontName="Helvetica-Bold", leading=14)),
            Paragraph(f"<b>{sev}</b>",
                      ParagraphStyle("badge", fontSize=8.5, textColor=sev_color,
                                     fontName="Helvetica-Bold", alignment=TA_CENTER)),
        ]]
        area_header_table = Table(area_header_data, colWidths=[5.5*inch, 1.0*inch])
        area_header_table.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (0, 0), BRAND_ACCENT2),
            ("BACKGROUND",     (1, 0), (1, 0), sev_bg),
            ("BOX",            (0, 0), (-1, -1), 0.5, colors.HexColor("#b0c8e0")),
            ("LINEAFTER",      (0, 0), (0, 0), 0.5, colors.HexColor("#b0c8e0")),
            ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",     (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
            ("LEFTPADDING",    (0, 0), (0, 0), 8),
            ("ALIGN",          (1, 0), (1, 0), "CENTER"),
        ]))
        story.append(Spacer(1, 0.06*inch))
        story.append(area_header_table)

        observations = area.get("observations", [])
        if observations:
            for obs in observations:
                if obs and str(obs).strip():
                    story.append(Paragraph(f"– {obs}", bullet_s))
        else:
            story.append(Paragraph("– No observations recorded.", bullet_s))

        # Attach matched image
        img_obj, img_idx = find_best_image_for_area(area_name, all_images, used_image_indices)
        if img_obj and img_idx is not None:
            used_image_indices.add(img_idx)
            try:
                pil_img = img_obj["image"]
                max_w, max_h = 4.5*inch, 2.8*inch
                orig_w, orig_h = pil_img.size
                ratio = min(max_w / orig_w, max_h / orig_h)
                disp_w = orig_w * ratio
                disp_h = orig_h * ratio

                img_buf = io.BytesIO()
                pil_img.save(img_buf, format="JPEG", quality=85)
                img_buf.seek(0)
                rl_img = RLImage(img_buf, width=disp_w, height=disp_h)

                source = "Inspection Report" if i % 2 == 0 else "Thermal Report"
                caption = (f"Fig {i+1}: Thermal/Inspection image — {area_name} "
                           f"(Source: {source}, Page {img_obj['page']})")
                story.append(Spacer(1, 0.04*inch))
                story.append(rl_img)
                story.append(Paragraph(caption, caption_s))
            except Exception:
                pass

        story.append(Spacer(1, 0.06*inch))

    # ── SECTION 3: ROOT CAUSE ────────────────────────────────────────────────
    story.append(Paragraph("3. PROBABLE ROOT CAUSE", h1_s))
    root_causes = ddr_data.get("root_causes", [])
    if root_causes:
        for rc in root_causes:
            issue    = rc.get("issue", "Unknown issue")
            cause    = rc.get("cause", "Unknown cause")
            evidence = rc.get("evidence", "")
            story.append(Spacer(1, 0.04*inch))
            story.append(Paragraph(f"▸  {issue}", h2_s))
            story.append(Paragraph(cause, body_s))
            if evidence and str(evidence).strip():
                ev_data = [[Paragraph(f"<i>Evidence: {evidence}</i>",
                                      ParagraphStyle("ev", fontSize=8.5, textColor=colors.HexColor("#444444"),
                                                     leading=12, fontName="Helvetica-Oblique"))]]
                ev_table = Table(ev_data, colWidths=[6.6*inch])
                ev_table.setStyle(TableStyle([
                    ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#f5f8fc")),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
                    ("TOPPADDING",    (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBEFORE",    (0, 0), (0, -1), 3, BRAND_BLUE),
                ]))
                story.append(ev_table)
            story.append(Spacer(1, 0.04*inch))
    else:
        story.append(Paragraph("No root cause analysis available.", body_s))

    # ── SECTION 4: SEVERITY ASSESSMENT ──────────────────────────────────────
    story.append(Paragraph("4. SEVERITY ASSESSMENT", h1_s))
    sev_list = ddr_data.get("severity_assessment", [])

    if sev_list:
        sev_data = [[
            Paragraph("<b>Area / Issue</b>", label_s),
            Paragraph("<b>Severity</b>", label_s),
            Paragraph("<b>Reasoning</b>", label_s),
            Paragraph("<b>Thermal</b>", label_s),
        ]]
        row_styles = [
            ("BACKGROUND",    (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("BOX",           (0, 0), (-1, -1), 0.8, BRAND_BLUE),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#c0d0e0")),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ]
        for row_idx, s in enumerate(sev_list, start=1):
            sev_val = s.get("severity", "Low")
            if "|" in sev_val or "/" in sev_val:
                sev_val = "Low"
            sev_color = SEV_COLORS.get(sev_val, colors.grey)
            sev_bg    = SEV_BG.get(sev_val, colors.white)
            row_bg    = BRAND_ACCENT2 if row_idx % 2 == 0 else colors.white

            sev_data.append([
                Paragraph(s.get("area", ""), cell_s),
                Paragraph(f"<b>{sev_val}</b>",
                          ParagraphStyle(f"sv{row_idx}", fontSize=8, textColor=sev_color,
                                         fontName="Helvetica-Bold", alignment=TA_CENTER)),
                Paragraph(s.get("reasoning", ""), cell_sm_s),
                Paragraph(s.get("thermal_confirmed", ""), cell_s),
            ])
            row_styles.append(("BACKGROUND", (0, row_idx), (-1, row_idx), row_bg))
            row_styles.append(("BACKGROUND", (1, row_idx), (1, row_idx), sev_bg))

        sev_table = Table(sev_data,
                          colWidths=[1.75*inch, 0.85*inch, 3.2*inch, 0.8*inch],
                          repeatRows=1)
        sev_table.setStyle(TableStyle(row_styles))
        story.append(sev_table)
    else:
        story.append(Paragraph("No severity assessment available.", body_s))

    story.append(Spacer(1, 0.1*inch))

    # ── SECTION 5: RECOMMENDED ACTIONS ──────────────────────────────────────
    story.append(Paragraph("5. RECOMMENDED ACTIONS", h1_s))
    actions = ddr_data.get("recommended_actions", [])
    if actions:
        PRI_COLOR = {
            "Immediate":  colors.HexColor("#c0392b"),
            "Short-term": colors.HexColor("#d35400"),
            "Long-term":  colors.HexColor("#1e8449"),
        }
        PRI_BG = {
            "Immediate":  colors.HexColor("#fdecea"),
            "Short-term": colors.HexColor("#fef0e6"),
            "Long-term":  colors.HexColor("#e9f7ef"),
        }
        act_data = [[
            Paragraph("<b>Priority</b>", label_s),
            Paragraph("<b>Area</b>", label_s),
            Paragraph("<b>Action Required</b>", label_s),
            Paragraph("<b>Est. Cost</b>", label_s),
        ]]
        row_styles_a = [
            ("BACKGROUND",    (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("BOX",           (0, 0), (-1, -1), 0.8, BRAND_BLUE),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#c0d0e0")),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ]
        for row_idx, a in enumerate(actions, start=1):
            priority = a.get("priority", "Long-term")
            p_color  = PRI_COLOR.get(priority, colors.black)
            p_bg     = PRI_BG.get(priority, colors.white)
            row_bg   = BRAND_ACCENT2 if row_idx % 2 == 0 else colors.white
            act_data.append([
                Paragraph(f"<b>{priority}</b>",
                          ParagraphStyle(f"pr{row_idx}", fontSize=8, textColor=p_color,
                                         fontName="Helvetica-Bold", alignment=TA_CENTER)),
                Paragraph(a.get("area", ""), cell_s),
                Paragraph(a.get("action", ""), cell_sm_s),
                Paragraph(a.get("estimated_cost", "TBD"), cell_s),
            ])
            row_styles_a.append(("BACKGROUND", (0, row_idx), (-1, row_idx), row_bg))
            row_styles_a.append(("BACKGROUND", (0, row_idx), (0, row_idx), p_bg))

        act_table = Table(act_data,
                          colWidths=[0.95*inch, 1.5*inch, 3.2*inch, 1.0*inch],
                          repeatRows=1)
        act_table.setStyle(TableStyle(row_styles_a))
        story.append(act_table)
    else:
        story.append(Paragraph("No recommended actions available.", body_s))

    story.append(Spacer(1, 0.1*inch))

    # ── SECTION 6: ADDITIONAL NOTES ─────────────────────────────────────────
    story.append(Paragraph("6. ADDITIONAL NOTES", h1_s))
    notes = ddr_data.get("additional_notes", [])
    if notes and any(str(n).strip() for n in notes):
        for n in notes:
            if str(n).strip():
                story.append(Paragraph(f"• {n}", bullet_s))
    else:
        story.append(Paragraph("• No additional notes recorded.", bullet_s))

    story.append(Spacer(1, 0.1*inch))

    # ── SECTION 7: MISSING / UNCLEAR INFORMATION ────────────────────────────
    story.append(Paragraph("7. MISSING OR UNCLEAR INFORMATION", h1_s))
    missing = ddr_data.get("missing_information", [])
    if missing:
        mis_data = [[
            Paragraph("<b>Item</b>", label_s),
            Paragraph("<b>Source</b>", label_s),
            Paragraph("<b>Impact on Report</b>", label_s),
        ]]
        for row_idx, m in enumerate(missing, start=1):
            row_bg = BRAND_ACCENT2 if row_idx % 2 == 0 else colors.white
            mis_data.append([
                Paragraph(m.get("item", ""), cell_s),
                Paragraph(m.get("source", ""), cell_s),
                Paragraph(m.get("impact", ""), cell_sm_s),
            ])

        mis_table = Table(mis_data, colWidths=[2.1*inch, 0.9*inch, 3.65*inch], repeatRows=1)
        mis_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, BRAND_ACCENT2]),
            ("BOX",           (0, 0), (-1, -1), 0.8, BRAND_BLUE),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#c0d0e0")),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ]))
        story.append(mis_table)
    else:
        story.append(Paragraph("• No missing information identified.", bullet_s))

    # ── FOOTER ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.2*inch))
    ts = datetime.now().strftime("%d %B %Y at %H:%M")
    footer_data = [[Paragraph(
        f"Generated by AI DDR System on {ts}. "
        "All findings based solely on provided documents. "
        "Review by a qualified engineer is recommended.",
        footer_s
    )]]
    footer_table = Table(footer_data, colWidths=[7.1*inch])
    footer_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BRAND_ACCENT),
        ("BOX",           (0, 0), (-1, -1), 0.5, BRAND_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(footer_table)

    doc.build(story)
    buf.seek(0)
    return buf


# ══════════════════════════════════════════════════════════════════════════════
# 7. MULTI-TURN SECTION REFINEMENT
# ══════════════════════════════════════════════════════════════════════════════

def refine_section(ddr_data, section_key, instruction, combined_text):
    """Re-analyse a specific section with a custom instruction."""
    prompt = f"""
You are a building inspection AI. Based on the following report text and existing DDR data,
re-analyse the section "{section_key}" with this instruction: {instruction}

Report text (excerpt):
{combined_text[:3000]}

Current DDR data for this section:
{json.dumps(ddr_data.get(section_key, {}), indent=2)}

Return ONLY the updated JSON for the "{section_key}" field. No explanation.
"""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2000}
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
        match = re.search(r"[\[\{].*[\]\}]", raw, re.DOTALL)
        if match:
            updated = json.loads(match.group())
            ddr_data[section_key] = updated
    except Exception as e:
        st.warning(f"Refinement failed: {e}")
    return ddr_data


# ══════════════════════════════════════════════════════════════════════════════
# 8. STREAMLIT UI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="DDR Report Generator",
        page_icon="🏗️",
        layout="wide"
    )

    st.title("🏗️ DDR Report Generator")
    st.caption("AI-powered Detailed Diagnostic Report from Inspection + Thermal PDFs")

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Settings")
        st.info(f"**AI Model:** {OLLAMA_MODEL}\n\nMake sure Ollama is running:\n`ollama serve`")
        use_demo = st.checkbox("Use built-in sample data (demo mode)", value=False)
        st.markdown("---")
        st.markdown("**Pipeline:**\n1. Upload PDFs\n2. Extract text + images\n3. AI analysis\n4. Download DDR PDF")

    # ── File Upload ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        insp_file = st.file_uploader("📄 Inspection Report PDF", type=["pdf"])
    with col2:
        therm_file = st.file_uploader("🌡️ Thermal Report PDF", type=["pdf"])

    # ── Generate Button ──────────────────────────────────────────────────────
    if st.button("🚀 Generate DDR Report", type="primary", use_container_width=True):

        if not use_demo and (not insp_file or not therm_file):
            st.error("Please upload both PDFs, or enable demo mode.")
            return

        all_images = []
        combined_text = ""

        if use_demo:
            st.info("Using built-in sample data...")
            # Import sample data only when needed
            try:
                from sample_data import SAMPLE_INSPECTION_TEXT, SAMPLE_THERMAL_TEXT
                combined_text = SAMPLE_INSPECTION_TEXT + "\n\n" + SAMPLE_THERMAL_TEXT
            except ImportError:
                st.error("sample_data.py not found. Please uncheck demo mode and upload PDFs.")
                return
        else:
            # Stage 1: Extract
            with st.status("📖 Stage 1: Extracting PDF content...") as status:
                insp_text, insp_images = extract_pdf_content(insp_file)
                st.write(f"✅ Inspection: {len(insp_text)} chars, {len(insp_images)} images")

                therm_text, therm_images = extract_pdf_content(therm_file)
                st.write(f"✅ Thermal: {len(therm_text)} chars, {len(therm_images)} images")

                combined_text = (
                    "=== INSPECTION REPORT ===\n" + insp_text +
                    "\n\n=== THERMAL REPORT ===\n" + therm_text
                )
                all_images = insp_images + therm_images
                status.update(label="✅ Stage 1 complete!", state="complete")

        # Stage 2: AI Analysis
        with st.status("🤖 Stage 2: AI analysis (this may take 1-2 min)...") as status:
            chunks = chunk_text(combined_text)
            st.write(f"Processing {len(chunks)} chunk(s)...")

            results = []
            for i, chunk in enumerate(chunks):
                st.write(f"Analysing chunk {i+1}/{len(chunks)}...")
                result = call_ollama(chunk, f"Chunk {i+1}")
                if result:
                    results.append(result)
                    st.write(f"✅ Chunk {i+1} parsed successfully")
                else:
                    st.write(f"⚠️ Chunk {i+1} returned no valid JSON")

            ddr_data = merge_results(results)
            if not ddr_data:
                st.error("AI returned no usable data. Make sure Ollama is running and llama3.1:8b is downloaded.")
                status.update(label="❌ Stage 2 failed", state="error")
                return

            status.update(label="✅ Stage 2 complete!", state="complete")

        # Store in session
        st.session_state["ddr_data"] = ddr_data
        st.session_state["all_images"] = all_images
        st.session_state["combined_text"] = combined_text

        # Stage 3: PDF Generation
        with st.status("📝 Stage 3: Building PDF...") as status:
            pdf_buf = build_ddr_pdf(ddr_data, all_images)
            st.session_state["pdf_buf"] = pdf_buf
            status.update(label="✅ Stage 3 complete!", state="complete")

        st.success("✅ DDR Report generated!")

    # ── Download + Preview ───────────────────────────────────────────────────
    if "pdf_buf" in st.session_state:
        st.download_button(
            label="⬇️ Download DDR Report (PDF)",
            data=st.session_state["pdf_buf"],
            file_name=f"DDR_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )

    # ── Multi-turn Refinement ────────────────────────────────────────────────
    if "ddr_data" in st.session_state:
        st.markdown("---")
        st.subheader("🔄 Section Refinement")
        st.caption("Re-analyse any section with custom instructions")

        col_a, col_b = st.columns([1, 2])
        with col_a:
            section_options = {
                "Property Issue Summary": "property_summary",
                "Area Observations": "area_observations",
                "Root Causes": "root_causes",
                "Severity Assessment": "severity_assessment",
                "Recommended Actions": "recommended_actions",
                "Additional Notes": "additional_notes",
                "Missing Information": "missing_information",
            }
            selected_section = st.selectbox("Select section", list(section_options.keys()))
        with col_b:
            refine_instruction = st.text_input(
                "Refinement instruction",
                placeholder="e.g. Focus more on structural risks in the basement area"
            )

        if st.button("🔄 Refine Section", use_container_width=True):
            if refine_instruction.strip():
                with st.spinner("Re-analysing section..."):
                    section_key = section_options[selected_section]
                    st.session_state["ddr_data"] = refine_section(
                        st.session_state["ddr_data"],
                        section_key,
                        refine_instruction,
                        st.session_state.get("combined_text", "")
                    )
                    # Rebuild PDF
                    pdf_buf = build_ddr_pdf(
                        st.session_state["ddr_data"],
                        st.session_state.get("all_images", [])
                    )
                    st.session_state["pdf_buf"] = pdf_buf
                    st.success(f"✅ '{selected_section}' refined. Download the updated PDF above.")
                    st.rerun()
            else:
                st.warning("Please enter a refinement instruction.")

        # ── JSON Preview ─────────────────────────────────────────────────────
        with st.expander("🔍 View raw DDR JSON"):
            st.json(st.session_state["ddr_data"])


if __name__ == "__main__":
    main()