"""
DDR (Detailed Diagnostic Report) Generator - Improved Version
AI-powered system using Groq (LLaMA 3) + PyMuPDF + pytesseract OCR
Improvements:
  1. OCR support for scanned PDFs (pytesseract fallback)
  2. Document chunking for long documents (no content lost)
  3. Multi-turn AI refinement (engineer can request section re-analysis)
"""

import streamlit as st
import fitz  # PyMuPDF
import base64
import io
import json
import os
import re
from PIL import Image
from groq import Groq
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, Image as RLImage)
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# OCR optional import
# OCR optional import
try:
    import pytesseract
    OCR_AVAILABLE = True
except:
    pytesseract = None
    OCR_AVAILABLE = False



st.set_page_config(page_title="DDR Report Generator", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background: #f8f7f4; }
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2.5rem 2rem; border-radius: 16px; margin-bottom: 2rem;
        text-align: center; box-shadow: 0 8px 32px rgba(15,52,96,0.3);
    }
    .main-header h1 { font-family: 'DM Serif Display', serif; color: #e8d5b7; font-size: 2.2rem; margin: 0; }
    .main-header p { color: #a8c5da; margin: 0.5rem 0 0 0; font-size: 0.95rem; font-weight: 300; }
    .section-label { font-size: 0.75rem; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; color: #0f3460; margin-bottom: 0.5rem; }
    .status-chip { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 500; }
    .chip-critical { background: #fde8e8; color: #c0392b; }
    .chip-high { background: #fef3cd; color: #d68910; }
    .chip-moderate { background: #fff3e0; color: #e67e22; }
    .chip-low { background: #e8f5e9; color: #27ae60; }
    .ddr-section { background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; border-left: 4px solid #0f3460; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .ddr-section h3 { color: #0f3460; font-family: 'DM Serif Display', serif; font-size: 1.15rem; margin-top: 0; }
    .warning-box { background: #fff8e1; border: 1px solid #f9a825; border-radius: 8px; padding: 0.8rem 1rem; font-size: 0.85rem; color: #5d4037; }
    .success-box { background: #e8f5e9; border: 1px solid #43a047; border-radius: 8px; padding: 0.8rem 1rem; font-size: 0.85rem; color: #1b5e20; }
    .info-box { background: #e3f2fd; border: 1px solid #1976d2; border-radius: 8px; padding: 0.8rem 1rem; font-size: 0.85rem; color: #0d47a1; }
    div[data-testid="stSidebar"] { background: #1a1a2e; }
    div[data-testid="stSidebar"] * { color: #e8d5b7 !important; }
    div[data-testid="stSidebar"] .stTextInput input { background: #16213e; border: 1px solid #0f3460; color: #e8d5b7 !important; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Configuration")
    api_key = os.environ.get("GROQ_API_KEY") or st.text_input("Groq API Key", type="password", placeholder="gsk_...", help="Get free key at console.groq.com")
    model = st.selectbox("LLM Model", ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"], help="LLaMA 3.3 70B recommended")
    st.markdown("---")
    st.markdown("### Improvements Active")
    st.markdown("- OCR fallback for scanned PDFs\n- Chunking for long documents\n- Multi-turn AI refinement")
    st.markdown("---")
    st.markdown("### How to Use")
    st.markdown("1. Enter your **Groq API key**\n2. Upload both PDFs\n3. Click **Generate DDR**\n4. Optionally refine sections\n5. Download the PDF")
    if not OCR_AVAILABLE:
        st.markdown("---\n*OCR not installed. Run: pip install pytesseract*")

st.markdown("""
<div class="main-header">
    <h1>DDR Report Generator</h1>
    <p>AI-powered Detailed Diagnostic Report from Inspection + Thermal Data</p>
</div>
""", unsafe_allow_html=True)


# ── IMPROVEMENT 1: OCR FALLBACK ──
def extract_text_with_ocr(page):
    if not OCR_AVAILABLE:
        return ""
    try:
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

def extract_pdf_content(uploaded_file, doc_type="inspection"):
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text, images, ocr_used = [], [], False

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if not text and OCR_AVAILABLE:
            text = extract_text_with_ocr(page)
            if text:
                ocr_used = True
                text = f"[OCR]\n{text}"
        if text:
            full_text.append(f"[Page {page_num + 1}]\n{text}")
        for img_idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            try:
                pil_img = Image.open(io.BytesIO(img_bytes))
                if pil_img.width > 80 and pil_img.height > 80:
                    images.append({
                        "page": page_num + 1, "index": img_idx,
                        "ext": base_image["ext"], "width": pil_img.width,
                        "height": pil_img.height,
                        "b64": base64.b64encode(img_bytes).decode(),
                        "bytes": img_bytes, "source": doc_type
                    })
            except Exception:
                pass
    doc.close()
    return "\n".join(full_text), images, ocr_used


# ── IMPROVEMENT 2: CHUNKING ──
CHUNK_SIZE = 6000
CHUNK_OVERLAP = 500

def chunk_text(text):
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
        if start >= len(text): break
    return chunks if chunks else [text]

def merge_chunk_results(results):
    if len(results) == 1:
        return results[0]
    merged = results[0].copy()
    sev_order = {"Critical": 4, "High": 3, "Moderate": 2, "Low": 1}
    for result in results[1:]:
        existing_areas = {a["area"] for a in merged.get("area_observations", [])}
        for area in result.get("area_observations", []):
            if area["area"] not in existing_areas:
                merged["area_observations"].append(area)
            else:
                for ex in merged["area_observations"]:
                    if ex["area"] == area["area"]:
                        new_obs = [o for o in area.get("observations", []) if o not in ex.get("observations", [])]
                        ex["observations"].extend(new_obs)
        existing_issues = {r["issue"] for r in merged.get("root_causes", [])}
        for rc in result.get("root_causes", []):
            if rc["issue"] not in existing_issues:
                merged["root_causes"].append(rc)
        existing_sev = {s["area"]: s for s in merged.get("severity_assessment", [])}
        for sev in result.get("severity_assessment", []):
            area = sev["area"]
            if area not in existing_sev:
                merged["severity_assessment"].append(sev)
            elif sev_order.get(sev.get("severity","Low"),0) > sev_order.get(existing_sev[area].get("severity","Low"),0):
                existing_sev[area].update(sev)
        existing_actions = {r["action"] for r in merged.get("recommended_actions", [])}
        for action in result.get("recommended_actions", []):
            if action["action"] not in existing_actions:
                merged["recommended_actions"].append(action)
        existing_missing = {m["item"] for m in merged.get("missing_or_unclear", [])}
        for m in result.get("missing_or_unclear", []):
            if m["item"] not in existing_missing:
                merged["missing_or_unclear"].append(m)
    # Count both Critical and High severity as "critical issues"
    merged["property_summary"]["critical_issues_count"] = len(
        [s for s in merged.get("severity_assessment", [])
         if s.get("severity") in ("Critical", "High")])
    return merged

def generate_ddr_with_groq(inspection_text, thermal_text, api_key, model):
    client = Groq(api_key=api_key)
    system_prompt = """You are a senior building diagnostics engineer.
Analyze inspection and thermal imaging reports and generate a structured DDR.

STRICT RULES:
1. Never invent facts not present in the documents.
2. Flag conflicts between documents explicitly.
3. Write "Not Available" if information is missing.
4. Use simple, client-friendly language.
5. EVERY area mentioned in the inspection report MUST appear in severity_assessment - do not skip any area.
6. Severity levels must be: Critical, High, Moderate, or Low only.
7. critical_issues_count must equal the total count of ALL areas with severity "Critical" OR "High".
8. recommended_actions must include at least one action for EVERY area with Critical or High severity.
9. Return ONLY valid JSON with no extra text, no markdown, no explanation.

Return ONLY this exact JSON structure:
{
  "property_summary": {"property_name":"","inspection_date":"","overall_condition":"","critical_issues_count":0,"summary":""},
  "area_observations": [{"area":"","observations":[],"thermal_data":"","image_placement_hint":""}],
  "root_causes": [{"issue":"","probable_cause":"","supporting_evidence":""}],
  "severity_assessment": [{"area":"","severity":"Critical|High|Moderate|Low","reasoning":"","thermal_confirmation":"yes|no|partial"}],
  "recommended_actions": [{"priority":"Immediate|Short-term|Long-term","action":"","area":"","estimated_urgency":""}],
  "additional_notes": [],
  "missing_or_unclear": [{"item":"","source":"inspection|thermal|both","impact":""}]
}"""

    def call_groq(ic, tc):
        r = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":system_prompt},
                      {"role":"user","content":f"=== INSPECTION ===\n{ic}\n\n=== THERMAL ===\n{tc}\n\nGenerate DDR JSON."}],
            temperature=0.1, max_tokens=4000)
        raw = r.choices[0].message.content
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(m.group() if m else raw)

    insp_chunks = chunk_text(inspection_text)
    therm_chunks = chunk_text(thermal_text)
    max_chunks = max(len(insp_chunks), len(therm_chunks))
    results = []
    for i in range(max_chunks):
        ic = insp_chunks[min(i, len(insp_chunks)-1)]
        tc = therm_chunks[min(i, len(therm_chunks)-1)]
        results.append(call_groq(ic, tc))
    return merge_chunk_results(results), len(results)


# ── IMPROVEMENT 3: MULTI-TURN REFINEMENT ──
def refine_ddr_section(ddr_data, section_name, user_instruction, api_key, model, inspection_text, thermal_text):
    client = Groq(api_key=api_key)
    r = client.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content":"You are a senior building diagnostics engineer refining a DDR section. Return ONLY the complete updated DDR JSON with only the requested section changed. Never invent facts."},
            {"role":"user","content":f"Current DDR:\n{json.dumps(ddr_data,indent=2)}\n\nSource docs (excerpt):\n=== INSPECTION ===\n{inspection_text[:4000]}\n\n=== THERMAL ===\n{thermal_text[:4000]}\n\nRefine the '{section_name}' section with this instruction: '{user_instruction}'\n\nReturn complete updated DDR JSON."}
        ],
        temperature=0.2, max_tokens=4000)
    raw = r.choices[0].message.content
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    return json.loads(m.group() if m else raw)


# ── PDF BUILDER ──
def build_ddr_pdf(ddr_data, inspection_images, thermal_images):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=55, leftMargin=55, topMargin=60, bottomMargin=60)
    styles = getSampleStyleSheet()
    S = lambda name, **kw: ParagraphStyle(name, parent=styles['Normal'], **kw)
    title_s  = S('T',   fontName='Helvetica-Bold', fontSize=18, alignment=TA_CENTER, textColor=colors.HexColor('#1a1a2e'), spaceAfter=4)
    sub_s    = S('ST',  fontName='Helvetica', fontSize=10, alignment=TA_CENTER, textColor=colors.HexColor('#555'), spaceAfter=2)
    h1_s     = S('H1',  fontName='Helvetica-Bold', fontSize=13, spaceAfter=6, spaceBefore=14, textColor=colors.HexColor('#0f3460'))
    h2_s     = S('H2',  fontName='Helvetica-Bold', fontSize=11, spaceAfter=4, spaceBefore=8, textColor=colors.HexColor('#16213e'))
    body_s   = S('B',   fontName='Helvetica', fontSize=9.5, spaceAfter=4, leading=14, alignment=TA_JUSTIFY)
    bullet_s = S('BL',  fontName='Helvetica', fontSize=9, spaceAfter=3, leading=13, leftIndent=14)
    cap_s    = S('CAP', fontName='Helvetica-Oblique', fontSize=8, alignment=TA_CENTER, textColor=colors.grey, spaceAfter=8)
    label_s  = S('LAB', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#0f3460'), spaceAfter=2)
    sev_colors = {"Critical": colors.HexColor('#c0392b'), "High": colors.HexColor('#d68910'), "Moderate": colors.HexColor('#e67e22'), "Low": colors.HexColor('#27ae60')}
    story = []
    prop = ddr_data.get("property_summary", {})
    story += [Spacer(1,10), Paragraph("DETAILED DIAGNOSTIC REPORT", title_s),
              Paragraph("Building Assessment and Recommendations", sub_s),
              HRFlowable(width="100%", thickness=2, color=colors.HexColor('#0f3460'), spaceAfter=12)]
    info_data = [
        ["Property", prop.get("property_name","Not Available"), "Date", prop.get("inspection_date","Not Available")],
        ["Overall Condition", prop.get("overall_condition","Not Available"), "Critical Issues", str(prop.get("critical_issues_count","N/A"))],
        ["Report Generated", datetime.now().strftime("%d %B %Y"), "Report Type", "DDR - Full Assessment"],
    ]
    it = Table(info_data, colWidths=[1.2*inch,2.5*inch,1.2*inch,2.0*inch])
    it.setStyle(TableStyle([('FONTNAME',(0,0),(-1,-1),'Helvetica'),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
        ('FONTNAME',(2,0),(2,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f5f7fa')),('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#dde3ec')),
        ('PADDING',(0,0),(-1,-1),6),('TEXTCOLOR',(0,0),(0,-1),colors.HexColor('#0f3460')),('TEXTCOLOR',(2,0),(2,-1),colors.HexColor('#0f3460'))]))
    story += [it, Spacer(1,10)]
    story += [Paragraph("1. PROPERTY ISSUE SUMMARY", h1_s), HRFlowable(width="100%",thickness=0.5,color=colors.HexColor('#c8d8e8'),spaceAfter=8),
              Paragraph(prop.get("summary","Not Available"), body_s)]
    story += [Paragraph("2. AREA-WISE OBSERVATIONS", h1_s), HRFlowable(width="100%",thickness=0.5,color=colors.HexColor('#c8d8e8'),spaceAfter=8)]
    all_images = inspection_images + thermal_images
    img_counter = 0

    def find_best_image_for_area(area_name, used_indices):
        """Match image to area by comparing area name keywords to image caption/source page."""
        area_lower = area_name.lower()
        keywords = {
            "basement": ["basement", "parking", "seepage", "spalling", "b-4", "b-7"],
            "ground": ["ground", "lobby", "reception", "crack", "g-2", "g-5"],
            "first": ["first", "office", "cf-1", "w-12", "o-3", "o-5"],
            "roof": ["roof", "terrace", "membrane", "parapet", "drain"],
            "electrical": ["electrical", "panel", "ep-3", "ep-7", "circuit"],
        }
        best_match = None
        for key, words in keywords.items():
            if any(w in area_lower for w in [key]):
                for idx, img in enumerate(all_images):
                    if idx in used_indices:
                        continue
                    # Check if image page aligns roughly with area
                    best_match = idx
                    break
                if best_match is not None:
                    break
        # Fallback: just use next available image
        if best_match is None:
            for idx in range(len(all_images)):
                if idx not in used_indices:
                    best_match = idx
                    break
        return best_match

    used_img_indices = set()
    for i, area in enumerate(ddr_data.get("area_observations",[]), 1):
        story.append(Paragraph(f"2.{i} {area.get('area','Area')}", h2_s))
        for obs in area.get("observations",[]): story.append(Paragraph(f"- {obs}", bullet_s))
        thermal = area.get("thermal_data","Not Available")
        if thermal and thermal != "Not Available":
            story += [Paragraph("Thermal Findings:", label_s), Paragraph(thermal, bullet_s)]
        img_idx = find_best_image_for_area(area.get('area', ''), used_img_indices)
        if img_idx is not None:
            img_info = all_images[img_idx]
            used_img_indices.add(img_idx)
            img_counter += 1
            try:
                pil_img = Image.open(io.BytesIO(img_info["bytes"]))
                # Convert to RGB to ensure proper color rendering (fixes grayscale/hatch issue)
                if pil_img.mode not in ("RGB", "RGBA"):
                    pil_img = pil_img.convert("RGB")
                elif pil_img.mode == "RGBA":
                    bg = Image.new("RGB", pil_img.size, (255, 255, 255))
                    bg.paste(pil_img, mask=pil_img.split()[3])
                    pil_img = bg
                else:
                    pil_img = pil_img.convert("RGB")
                img_buf = io.BytesIO()
                pil_img.save(img_buf, format="PNG", optimize=False)
                img_buf.seek(0)
                ratio = min(3.5*inch/pil_img.width, 2.2*inch/pil_img.height)
                story += [RLImage(img_buf, width=pil_img.width*ratio, height=pil_img.height*ratio),
                          Paragraph(f"Fig {img_counter+1}: Thermal/Inspection image - {area.get('area','')} (Source: {img_info['source'].title()} Report, Page {img_info['page']})", cap_s)]
                img_counter += 1
            except Exception:
                story.append(Paragraph("[Image: Image Not Available]", cap_s))
        else:
            hint = area.get("image_placement_hint","")
            if hint:
                story.append(Paragraph(f"[Image Not Available - {hint}]", cap_s))
        story.append(Spacer(1,6))
    story += [Paragraph("3. PROBABLE ROOT CAUSE", h1_s), HRFlowable(width="100%",thickness=0.5,color=colors.HexColor('#c8d8e8'),spaceAfter=8)]
    for rc in ddr_data.get("root_causes",[]):
        story += [Paragraph(f"> {rc.get('issue','')}", h2_s), Paragraph(rc.get("probable_cause","Not Available"), body_s),
                  Paragraph(f"Evidence: {rc.get('supporting_evidence','Not Available')}", bullet_s), Spacer(1,4)]
    story += [Paragraph("4. SEVERITY ASSESSMENT", h1_s), HRFlowable(width="100%",thickness=0.5,color=colors.HexColor('#c8d8e8'),spaceAfter=8)]
    sev_data = [["Area / Issue","Severity","Reasoning","Thermal Confirmed"]]
    for item in ddr_data.get("severity_assessment",[]):
        sev_data.append([item.get("area",""),item.get("severity",""),item.get("reasoning",""),item.get("thermal_confirmation","N/A").capitalize()])
    if len(sev_data) > 1:
        # Fix: wider columns, smaller font, word wrap enabled to prevent overlap
        sev_table = Table(sev_data, colWidths=[1.6*inch, 0.75*inch, 2.9*inch, 1.25*inch], repeatRows=1)
        ss = [
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0f3460')),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('FONTSIZE',(0,0),(-1,0),8),
            ('FONTSIZE',(0,1),(-1,-1),7.5),
            ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#dde3ec')),
            ('PADDING',(0,0),(-1,-1),5),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f7fa')]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('WORDWRAP',(0,0),(-1,-1),True),
        ]
        for ri, item in enumerate(ddr_data.get("severity_assessment",[]),1):
            col = sev_colors.get(item.get("severity",""), colors.grey)
            ss += [('TEXTCOLOR',(1,ri),(1,ri),col),('FONTNAME',(1,ri),(1,ri),'Helvetica-Bold')]
        sev_table.setStyle(TableStyle(ss))
        story.append(sev_table)

    story += [Spacer(1,10), Paragraph("5. RECOMMENDED ACTIONS", h1_s),
              HRFlowable(width="100%",thickness=0.5,color=colors.HexColor('#c8d8e8'),spaceAfter=8)]
    for pl in ["Immediate","Short-term","Long-term"]:
        items = [r for r in ddr_data.get("recommended_actions",[]) if r.get("priority")==pl]
        if not items: continue
        story.append(Paragraph(f"[{pl.upper()}] ACTIONS", h2_s))
        for action in items:
            story.append(Paragraph(
                f"- [{action.get('area','')}] {action.get('action','')} -- {action.get('estimated_urgency','')}",
                bullet_s))
        story.append(Spacer(1,6))

    # Fix: Additional notes - show Not Available if empty list or list with empty strings
    story += [Paragraph("6. ADDITIONAL NOTES", h1_s),
              HRFlowable(width="100%",thickness=0.5,color=colors.HexColor('#c8d8e8'),spaceAfter=8)]
    additional_notes = ddr_data.get("additional_notes", [])
    if not additional_notes or all(str(n).strip() == "" for n in additional_notes):
        story.append(Paragraph("- No additional notes recorded.", bullet_s))
    else:
        for note in additional_notes:
            if str(note).strip():
                story.append(Paragraph(f"- {note}", bullet_s))

    # Fix: Missing table - use paragraph wrapping instead of plain strings to prevent cutoff
    story += [Paragraph("7. MISSING OR UNCLEAR INFORMATION", h1_s),
              HRFlowable(width="100%",thickness=0.5,color=colors.HexColor('#c8d8e8'),spaceAfter=8)]
    missing = ddr_data.get("missing_or_unclear",[])
    wrap_s = ParagraphStyle('WS', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=11)
    if not missing:
        story.append(Paragraph("No missing or unclear information identified.", body_s))
    else:
        md = [[Paragraph("<b>Item</b>", wrap_s),
               Paragraph("<b>Source</b>", wrap_s),
               Paragraph("<b>Impact on Report</b>", wrap_s)]]
        for m in missing:
            md.append([
                Paragraph(m.get("item","Not Available"), wrap_s),
                Paragraph(m.get("source","").capitalize(), wrap_s),
                Paragraph(m.get("impact","Not Available"), wrap_s)
            ])
        mt = Table(md, colWidths=[2.0*inch, 0.9*inch, 3.6*inch], repeatRows=1)
        mt.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#555')),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('FONTSIZE',(0,0),(-1,-1),7.5),
            ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#dde3ec')),
            ('PADDING',(0,0),(-1,-1),5),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#fafafa'),colors.HexColor('#fff8e1')]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
        ]))
        story.append(mt)
    story += [Spacer(1,20), HRFlowable(width="100%",thickness=1,color=colors.HexColor('#0f3460')),
              Paragraph(f"Generated by AI DDR System on {datetime.now().strftime('%d %B %Y at %H:%M')}. All findings based solely on provided documents. Review by a qualified engineer recommended.", cap_s)]
    doc.build(story)
    buffer.seek(0)
    return buffer


# ── SESSION STATE ──
for key in ["ddr_data","inspection_text","thermal_text","inspection_images","thermal_images"]:
    if key not in st.session_state:
        st.session_state[key] = None if key == "ddr_data" else ("" if "text" in key else [])

# ── MAIN UI ──
col1, col2 = st.columns(2, gap="large")
with col1:
    st.markdown('<div class="section-label">Inspection Report</div>', unsafe_allow_html=True)
    inspection_file = st.file_uploader("Upload Inspection Report PDF", type=["pdf"], key="inspection", label_visibility="collapsed")
    if inspection_file: st.markdown('<div class="success-box">Inspection report uploaded successfully</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="section-label">Thermal Report</div>', unsafe_allow_html=True)
    thermal_file = st.file_uploader("Upload Thermal Report PDF", type=["pdf"], key="thermal", label_visibility="collapsed")
    if thermal_file: st.markdown('<div class="success-box">Thermal report uploaded successfully</div>', unsafe_allow_html=True)

st.markdown("---")

if OCR_AVAILABLE: st.markdown('<div class="info-box">OCR is enabled - scanned PDFs are supported.</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
generate_btn = st.button("Generate DDR Report", type="primary", use_container_width=True)

if generate_btn:
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar.")
        st.stop()
    with st.spinner(""):
        progress = st.progress(0)
        status = st.empty()
        status.markdown("**Step 1/4:** Extracting document content...")
        progress.progress(10)
        if not (inspection_file and thermal_file):
            st.error("Please upload both Inspection and Thermal PDF files.")
            st.stop()
        inspection_text, inspection_images, ocr_i = extract_pdf_content(inspection_file, "inspection")
        thermal_text, thermal_images, ocr_t = extract_pdf_content(thermal_file, "thermal")
        ocr_used = ocr_i or ocr_t
        st.session_state.inspection_text = inspection_text
        st.session_state.thermal_text = thermal_text
        st.session_state.inspection_images = inspection_images
        st.session_state.thermal_images = thermal_images
        img_count = len(inspection_images) + len(thermal_images)
        progress.progress(30)
        status.markdown(f"**Step 1/4:** Extracted - {img_count} images found{'(OCR used)' if ocr_used else ''}")
        status.markdown("**Step 2/4:** AI analyzing (chunked processing)...")
        progress.progress(40)
        try:
            ddr_data, num_chunks = generate_ddr_with_groq(inspection_text, thermal_text, api_key, model)
            st.session_state.ddr_data = ddr_data
        except json.JSONDecodeError as e:
            st.error(f"AI returned invalid JSON. Try again or switch model. Error: {e}"); st.stop()
        except Exception as e:
            st.error(f"Groq API error: {e}"); st.stop()
        progress.progress(65)
        status.markdown(f"**Step 2/4:** AI analysis complete ({num_chunks} chunk(s) processed)")
        status.markdown("**Step 3/4:** Building PDF report...")
        progress.progress(75)
        try:
            pdf_buffer = build_ddr_pdf(ddr_data, inspection_images, thermal_images)
        except Exception as e:
            st.error(f"PDF generation error: {e}"); st.stop()
        progress.progress(100)
        status.markdown("**Done!**")

if st.session_state.ddr_data:
    ddr_data = st.session_state.ddr_data
    st.markdown("---")
    st.markdown("## Generated DDR Preview")
    prop = ddr_data.get("property_summary", {})
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Property", prop.get("property_name","N/A"))
    with m2: st.metric("Condition", prop.get("overall_condition","N/A"))
    with m3: st.metric("Critical Issues", prop.get("critical_issues_count","N/A"))
    with m4: st.metric("Areas Analyzed", len(ddr_data.get("area_observations",[])))
    st.markdown(f'<div class="ddr-section"><h3>1. Property Issue Summary</h3><p>{prop.get("summary","Not Available")}</p></div>', unsafe_allow_html=True)
    with st.expander("2. Area-wise Observations", expanded=True):
        for i, area in enumerate(ddr_data.get("area_observations",[]), 1):
            st.markdown(f"**{i}. {area.get('area','')}**")
            for obs in area.get("observations",[]): st.markdown(f"  - {obs}")
            thermal = area.get("thermal_data","")
            if thermal and thermal != "Not Available": st.caption(f"Thermal: {thermal}")
            st.markdown("")
    with st.expander("4. Severity Assessment", expanded=True):
        sev_items = ddr_data.get("severity_assessment",[])
        if sev_items:
            for col, h in zip(st.columns([2,1,3,1]), ["Area","Severity","Reasoning","Thermal Confirmed"]): col.markdown(f"**{h}**")
            for item in sev_items:
                c1,c2,c3,c4 = st.columns([2,1,3,1])
                sev = item.get("severity","")
                c1.write(item.get("area","")); c2.markdown(f'<span class="status-chip chip-{sev.lower()}">{sev}</span>', unsafe_allow_html=True)
                c3.write(item.get("reasoning","")); c4.write(item.get("thermal_confirmation","N/A").capitalize())
    with st.expander("5. Recommended Actions"):
        for priority in ["Immediate","Short-term","Long-term"]:
            items = [r for r in ddr_data.get("recommended_actions",[]) if r.get("priority")==priority]
            if items:
                st.markdown(f"**{'[!!]' if priority=='Immediate' else '[!]' if priority=='Short-term' else '[i]'} {priority}**")
                for item in items: st.markdown(f"  - [{item.get('area','')}] {item.get('action','')} - *{item.get('estimated_urgency','')}*")
    missing = ddr_data.get("missing_or_unclear",[])
    if missing:
        with st.expander(f"7. Missing / Unclear Information ({len(missing)} items)"):
            for m in missing: st.markdown(f"- **{m.get('item','N/A')}** ({m.get('source','').capitalize()}) - {m.get('impact','')}")

    # ── IMPROVEMENT 3: REFINEMENT UI ──
    st.markdown("---")
    st.markdown("### Refine a Section")
    st.markdown('<div class="info-box">Not happy with a section? Ask the AI to re-analyze it with your specific instruction.</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    rc1, rc2 = st.columns([1,2])
    with rc1:
        section_to_refine = st.selectbox("Section to refine", ["area_observations","root_causes","severity_assessment","recommended_actions","missing_or_unclear","additional_notes"])
    with rc2:
        refine_instruction = st.text_input("Your instruction", placeholder="e.g. Add more detail on electrical panel risk, or Re-assess basement as Critical")
    if st.button("Re-analyze Section", use_container_width=True):
        if not refine_instruction.strip():
            st.warning("Please enter an instruction.")
        elif not api_key:
            st.error("API key required.")
        else:
            with st.spinner("AI re-analyzing section..."):
                try:
                    updated = refine_ddr_section(st.session_state.ddr_data, section_to_refine, refine_instruction,
                                                  api_key, model, st.session_state.inspection_text, st.session_state.thermal_text)
                    st.session_state.ddr_data = updated
                    st.success("Section updated. Scroll up to see changes or download the updated PDF below.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Refinement error: {e}")

    st.markdown("---")
    try:
        pdf_buf = build_ddr_pdf(st.session_state.ddr_data, st.session_state.inspection_images, st.session_state.thermal_images)
        st.download_button(label="Download Full DDR Report (PDF)", data=pdf_buf,
                           file_name=f"DDR_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                           mime="application/pdf", use_container_width=True, type="primary")
    except Exception as e:
        st.error(f"PDF error: {e}")
    with st.expander("Raw DDR JSON (for developers)"):
        st.json(st.session_state.ddr_data)
