# 🏗️ DDR Report Generator — AI-Powered Building Diagnostic System

> **Assignment**: Applied AI Builder – DDR Report Generation  
> **Stack**: Python · Streamlit · Groq (LLaMA 3) · PyMuPDF · ReportLab  
> **Live Demo**: [Deploy to Hugging Face Spaces](#deployment)

---

## 📌 What This System Does

This AI system takes two raw site inspection documents as input and automatically generates a structured, client-ready **Detailed Diagnostic Report (DDR)**:

| Input | Output |
|---|---|
| 📋 Inspection Report PDF | 📄 Professional DDR PDF |
| 🌡️ Thermal Imaging Report PDF | 🔍 Area-wise Analysis |
| | ⚠️ Severity Assessment |
| | ✅ Recommended Actions |

---

## 🧠 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER UPLOADS                          │
│         Inspection PDF  +  Thermal PDF                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│               PDF EXTRACTION (PyMuPDF)                   │
│   • Extract full text from each page                     │
│   • Extract embedded images (filtered by size)           │
│   • Tag images by source document & page number          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│            AI ANALYSIS (Groq + LLaMA 3 70B)             │
│   • Merge inspection + thermal observations              │
│   • Identify conflicts between data sources              │
│   • Flag missing/unclear information                     │
│   • Assign severity levels with reasoning                │
│   • Generate structured DDR JSON                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           REPORT BUILDER (ReportLab)                     │
│   • Render professional A4 PDF                           │
│   • Place images under relevant sections                 │
│   • Color-coded severity tables                          │
│   • Actionable recommendations by priority               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
               📥 Downloadable DDR PDF
```

---

## 📋 DDR Output Structure

The generated report always contains:

1. **Property Issue Summary** — Executive overview
2. **Area-wise Observations** — Per-zone findings with thermal data merged
3. **Probable Root Cause** — AI-reasoned cause analysis
4. **Severity Assessment** — Critical / High / Moderate / Low with reasoning
5. **Recommended Actions** — Prioritized: Immediate → Short-term → Long-term
6. **Additional Notes** — Context from both documents
7. **Missing or Unclear Information** — Explicitly flagged as "Not Available"

---

## 🚀 Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/ddr-report-generator
cd ddr-report-generator
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Get a free Groq API key
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up for free
3. Create an API key (starts with `gsk_...`)

### 4. Run the app
```bash
streamlit run app.py
```

### 5. Use the app
- Enter your Groq API key in the sidebar
- Upload your Inspection Report PDF
- Upload your Thermal Report PDF
- Click **Generate DDR Report**
- Download the PDF

> **No documents?** Check the "Use sample data" box for a demo run.

---

## ☁️ Deployment (Hugging Face Spaces)

### Step 1: Create a new Space
- Go to [huggingface.co/new-space](https://huggingface.co/new-space)
- SDK: **Streamlit**
- Name: `ddr-report-generator`

### Step 2: Upload files
Upload these files:
```
app.py
sample_data.py
requirements.txt
```

### Step 3: Add secret
- Go to Space Settings → Secrets
- Add: `GROQ_API_KEY` = your Groq key (optional — users can also enter their own)

### Step 4: Your live demo is ready!
Hugging Face Spaces auto-builds and deploys. Share the URL in your submission.

---

## 🔑 Key Design Decisions

| Decision | Reason |
|---|---|
| **Groq + LLaMA 3 70B** | Free, fast, open-source, no GPU required |
| **JSON output from LLM** | Reliable structured parsing, not regex-dependent |
| **PyMuPDF for extraction** | Best-in-class PDF text + image extraction |
| **ReportLab for PDF output** | Full programmatic control over report layout |
| **Streamlit UI** | Fast to build, easy to demo, deploys free |
| **Sample data fallback** | Works without real documents — good for demo |

---

## ⚠️ Limitations

1. **Image extraction from PDFs** — only works if images are embedded in the PDF (not scanned/rasterized pages)
2. **Context window** — very long documents are truncated to 8,000 characters per document for the LLM call
3. **LLM accuracy** — LLaMA 3 may occasionally hallucinate; all outputs should be reviewed by a qualified engineer
4. **Groq rate limits** — free tier has token-per-minute limits; large documents may hit this
5. **No OCR** — scanned PDFs (image-based) won't have extractable text without OCR preprocessing

---

## 🔧 How to Improve

- **OCR support**: Add Tesseract/PaddleOCR for scanned documents
- **Chunking**: Split large documents into chunks with overlap for better LLM context
- **Multi-turn refinement**: Let the LLM iteratively refine the DDR
- **Template customization**: Allow users to configure DDR section requirements
- **Database logging**: Store past reports for audit trail
- **Email delivery**: Auto-send the PDF to clients

---

## 📁 Project Structure

```
ddr-report-generator/
├── app.py                  # Main Streamlit application
├── sample_data.py          # Sample inspection & thermal text (demo mode)
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## 📽️ Loom Video Outline (3–5 min)

Suggested structure for your submission video:

1. **(0:00–0:30)** Overview — what the system does and why
2. **(0:30–1:30)** Live demo — upload docs → generate → download DDR
3. **(1:30–2:30)** Code walkthrough — architecture & key decisions
4. **(2:30–3:30)** Output walkthrough — DDR sections, severity table, images
5. **(3:30–4:30)** Limitations & improvements

---

*Built with ❤️ using Groq · LLaMA 3 · Streamlit · PyMuPDF · ReportLab*
