from flask import Flask, render_template, request, jsonify
import fitz
import requests
import re
from collections import Counter

app = Flask(__name__)


# --------------------------------------------------
# STOP WORDS
# --------------------------------------------------

STOP_WORDS = {
    "the", "is", "are", "was", "were", "and", "or", "of",
    "to", "in", "on", "for", "with", "a", "an", "as",
    "by", "at", "from", "that", "this", "these", "those",
    "it", "its", "be", "been", "being", "has", "have",
    "had", "do", "does", "did", "will", "would", "can",
    "could", "should", "may", "might", "must", "than",
    "then", "also", "such", "into", "about", "over",
    "under", "between", "through", "during", "after",
    "before", "more", "most", "other", "some", "any",
    "each", "every", "both", "many", "much", "very",
    "their", "there", "they", "them", "he", "she", "his",
    "her", "you", "your", "we", "our", "i", "me", "my",
    "which", "who", "what", "when", "where", "why", "how"
}


# --------------------------------------------------
# CLEAN TEXT
# --------------------------------------------------

def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s.,;:!?()\-]", " ", text)
    return text.strip()


# --------------------------------------------------
# GET WORDS
# --------------------------------------------------

def get_words(text):
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())

    words = [
        word for word in words
        if word not in STOP_WORDS
    ]

    return words


# --------------------------------------------------
# GET KEYWORDS
# --------------------------------------------------

def get_keywords(text, limit=8):

    words = get_words(text)

    counter = Counter(words)

    keywords = [
        word.capitalize()
        for word, count in counter.most_common(limit)
    ]

    return keywords


# --------------------------------------------------
# GET SENTENCES
# --------------------------------------------------

def get_sentences(text):

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    sentences = [
        sentence.strip()
        for sentence in sentences
        if len(sentence.strip()) > 30
    ]

    return sentences


# --------------------------------------------------
# GET MAIN POINTS
# --------------------------------------------------

def get_main_points(text, limit=8):

    sentences = get_sentences(text)

    if not sentences:
        return [
            "No clear main points could be extracted."
        ]

    keywords = get_words(text)

    keyword_frequency = Counter(keywords)

    scored_sentences = []

    for index, sentence in enumerate(sentences):

        words = re.findall(
            r"\b[a-zA-Z]{4,}\b",
            sentence.lower()
        )

        score = sum(
            keyword_frequency.get(word, 0)
            for word in words
        )

        scored_sentences.append(
            (score, index, sentence)
        )

    scored_sentences.sort(
        key=lambda x: x[0],
        reverse=True
    )

    selected = scored_sentences[:limit]

    # Keep original document order
    selected.sort(key=lambda x: x[1])

    return [
        sentence
        for score, index, sentence in selected
    ]


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

def make_summary(text, limit=5):

    sentences = get_sentences(text)

    if not sentences:
        return "No summary could be generated."

    keywords = get_words(text)
    frequency = Counter(keywords)

    scored = []

    for index, sentence in enumerate(sentences):

        words = re.findall(
            r"\b[a-zA-Z]{4,}\b",
            sentence.lower()
        )

        score = sum(
            frequency.get(word, 0)
            for word in words
        )

        scored.append(
            (score, index, sentence)
        )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    selected = scored[:limit]

    selected.sort(key=lambda x: x[1])

    return " ".join(
        sentence
        for score, index, sentence in selected
    )


# --------------------------------------------------
# FIND POINTS FOR KEYWORD
# --------------------------------------------------

def find_points_for_keyword(
    keyword,
    sentences,
    limit=3
):

    keyword_lower = keyword.lower()

    matched = []

    for sentence in sentences:

        if keyword_lower in sentence.lower():

            matched.append(sentence)

    if not matched:
        return sentences[:limit]

    return matched[:limit]


# --------------------------------------------------
# CREATE MIND MAP BRANCHES
# --------------------------------------------------

def create_branches(
    title,
    text,
    keywords
):

    sentences = get_sentences(text)

    branches = []

    for keyword in keywords:

        points = find_points_for_keyword(
            keyword,
            sentences,
            3
        )

        branches.append({
            "name": keyword,
            "points": points
        })

    return branches


# --------------------------------------------------
# PDF TEXT EXTRACTION
# --------------------------------------------------

def extract_pdf_text(file):

    document = fitz.open(
        stream=file.read(),
        filetype="pdf"
    )

    text = ""

    for page in document:

        text += page.get_text()

    document.close()

    return clean_text(text)


# --------------------------------------------------
# PDF ANALYSIS API
# --------------------------------------------------

@app.route("/api/analyze-pdf", methods=["POST"])
def analyze_pdf():

    try:

        if "pdf" not in request.files:

            return jsonify({
                "success": False,
                "error": "Please upload a PDF file."
            }), 400

        file = request.files["pdf"]

        if file.filename == "":

            return jsonify({
                "success": False,
                "error": "No PDF file selected."
            }), 400

        if not file.filename.lower().endswith(".pdf"):

            return jsonify({
                "success": False,
                "error": "Only PDF files are supported."
            }), 400

        text = extract_pdf_text(file)

        if not text:

            return jsonify({
                "success": False,
                "error": "Could not extract text from this PDF."
            }), 400

        title = file.filename

        keywords = get_keywords(
            text,
            8
        )

        points = get_main_points(
            text,
            8
        )

        summary = make_summary(
            text,
            5
        )

        branches = create_branches(
            title,
            text,
            keywords
        )

        return jsonify({

            "success": True,

            "title": title,

            "source": "Uploaded PDF",

            "summary": summary,

            "keywords": keywords,

            "points": points,

            "branches": branches,

            "content": text

        })

    except Exception as e:

        print("PDF ERROR:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# --------------------------------------------------
# WIKIPEDIA TOPIC
# --------------------------------------------------

def get_wikipedia_topic(topic):

    url = (
        "https://en.wikipedia.org/api/rest_v1/"
        "page/summary/"
        + requests.utils.quote(topic)
    )

    response = requests.get(
        url,
        timeout=10,
        headers={
            "User-Agent": "PDF-Mind-Mapper/1.0"
        }
    )

    if response.status_code != 200:

        return None

    data = response.json()

    extract = data.get(
        "extract",
        ""
    )

    if not extract:

        return None

    return extract


# --------------------------------------------------
# FALLBACK TOPIC
# --------------------------------------------------

def create_fallback_topic(topic):

    return f"""
    {topic} is an important topic that can be studied
    through its basic concepts, characteristics,
    applications, advantages, limitations and examples.

    Understanding {topic} helps learners understand
    how the concept works and where it can be applied.

    The topic can be divided into different areas
    for easier learning and revision.
    """


# --------------------------------------------------
# NEW TOPIC API
# --------------------------------------------------

@app.route("/api/new-topic", methods=["POST"])
def new_topic():

    try:

        data = request.get_json()

        topic = data.get(
            "topic",
            ""
        ).strip()

        if not topic:

            return jsonify({
                "success": False,
                "error": "Please enter a topic."
            }), 400

        text = get_wikipedia_topic(
            topic
        )

        source = "Wikipedia"

        if not text:

            text = create_fallback_topic(
                topic
            )

            source = "Generated Topic"

        text = clean_text(text)

        keywords = get_keywords(
            text,
            8
        )

        points = get_main_points(
            text,
            8
        )

        summary = make_summary(
            text,
            5
        )

        branches = create_branches(
            topic,
            text,
            keywords
        )

        return jsonify({

            "success": True,

            "title": topic,

            "source": source,

            "summary": summary,

            "keywords": keywords,

            "points": points,

            "branches": branches,

            "content": text

        })

    except Exception as e:

        print("TOPIC ERROR:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.route("/health")
def health():

    return jsonify({
        "status": "ok"
    })


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# --------------------------------------------------
# RUN
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
