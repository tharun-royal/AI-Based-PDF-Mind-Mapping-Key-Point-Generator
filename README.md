# PDF Mind Mapper AI

An educational web application that:
- Uploads and reads PDF files
- Extracts important keywords
- Generates main points and a short summary
- Creates a visual mind map
- Accepts a completely new topic outside the PDF
- Gets a public Wikipedia summary for the new topic
- Allows notes to be downloaded

## 1. Install Python

Install Python 3.10+.

Check:

```bash
python --version
```

## 2. Open the project folder

```bash
cd pdf_mind_mapper
```

## 3. Create virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

## 4. Install packages

```bash
pip install -r requirements.txt
```

## 5. Run

```bash
python app.py
```

Open:

http://127.0.0.1:5000

## Project Structure

```text
pdf_mind_mapper/
│
├── app.py
├── requirements.txt
├── README.md
│
├── templates/
│   └── index.html
│
└── static/
    └── style.css
```

## Important

This starter version uses lightweight NLP keyword extraction rather than a paid LLM API.

For scanned/image-only PDFs, OCR should be added later.

For a stronger final-year/hackathon version, add:
- OpenAI/Gemini API
- OCR
- PDF question answering
- Login
- MySQL
- History
- Better hierarchical mind maps
- Export mind map as PNG/PDF
