from flask import Flask, render_template, request, jsonify
import fitz  # PyMuPDF
import re
import requests
from collections import Counter

app = Flask(__name__)

STOP_WORDS = set("""
the a an and or but if then than this that these those is are was were be been being
to of in on for from with by as at into about over under after before between through
during without within can could should would may might will shall do does did have has had
it its they them their there here you your we our he she his her i me my mine what which
who whom where when why how not no yes very more most some any all each every both few
many much such also only own same so too just than
""".split())

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 30]

def keywords(text, limit=12):
    words = re.findall(r'\b[A-Za-z][A-Za-z-]{3,}\b', text.lower())
    counts = Counter(w for w in words if w not in STOP_WORDS)
    return [w.title() for w, _ in counts.most_common(limit)]

def main_points(text, limit=10):
    sents = sentences(text)
    if not sents:
        return ["No readable text was found in the PDF."]
    scored = []
    key = set(k.lower() for k in keywords(text, 20))
    for i, s in enumerate(sents):
        ws = re.findall(r'\b[A-Za-z][A-Za-z-]{3,}\b', s.lower())
        score = sum(1 for w in ws if w in key)
        score += min(len(s) / 180, 1)
        scored.append((score, i, s))
    selected = sorted(scored, reverse=True)[:limit]
    selected = sorted(selected, key=lambda x: x[1])
    return [x[2] for x in selected]

def make_summary(text):
    pts = main_points(text, 6)
    return " ".join(pts)

def make_mindmap(title, keys):
    return {
        "name": title,
        "children": [{"name": k, "children": []} for k in keys[:10]]
    }

def extract_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    return clean_text(text)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/analyze-pdf", methods=["POST"])
def analyze_pdf():
    if "pdf" not in request.files:
        return jsonify({"error": "Please upload a PDF."}), 400

    file = request.files["pdf"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported."}), 400

    try:
        text = extract_pdf(file)
        if not text:
            return jsonify({"error": "No readable text found. Scanned PDFs need OCR."}), 400

        title = file.filename.rsplit(".", 1)[0]
        keys = keywords(text, 10)
        points = main_points(text, 10)

        return jsonify({
            "title": title,
            "summary": make_summary(text),
            "keywords": keys,
            "points": points,
            "mindmap": make_mindmap(title, keys)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/new-topic", methods=["POST"])
def new_topic():
    data = request.get_json() or {}
    topic = data.get("topic", "").strip()

    if not topic:
        return jsonify({"error": "Enter a topic."}), 400

    # Fetch a public Wikipedia summary for a topic outside the PDF.
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(topic.replace(" ", "_"))
        r = requests.get(url, timeout=8, headers={"User-Agent": "PDFMindMapper/1.0"})
        if r.status_code == 200:
            info = r.json()
            text = info.get("extract", "")
            title = info.get("title", topic)
        else:
            text = ""
            title = topic
    except Exception:
        text = ""
        title = topic

    if not text:
        # Offline fallback so the project still works without internet.
        text = (
            f"{topic} is a topic that can be studied through its definition, "
            f"main concepts, applications, advantages, limitations, and examples. "
            f"Learning {topic} becomes easier by dividing it into smaller related concepts."
        )

    keys = keywords(text, 8)
    points = main_points(text, 8)

    return jsonify({
        "title": title,
        "summary": make_summary(text),
        "keywords": keys,
        "points": points,
        "mindmap": make_mindmap(title, keys),
        "source": "Wikipedia public summary" if len(text) > 150 else "Generated fallback"
    })

if __name__ == "__main__":
    app.run(debug=True)
