from flask import Flask, render_template, request, jsonify
import fitz
import requests
import re
from collections import Counter

app = Flask(__name__)


# ============================================================
# STOP WORDS
# ============================================================

STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from",
    "are", "was", "were", "been", "have", "has", "had",
    "will", "would", "could", "should", "can", "may",
    "into", "about", "their", "there", "they", "them",
    "then", "than", "these", "those", "such", "also",
    "which", "when", "where", "what", "who", "how",
    "why", "your", "you", "our", "out", "not", "but",
    "all", "any", "its", "his", "her", "him", "she",
    "he", "it", "is", "in", "on", "at", "to", "of",
    "a", "an", "as", "or", "be", "by", "we", "i",
    "do", "does", "did", "if", "so", "because", "very",
    "more", "most", "other", "some", "each", "many",
    "only", "over", "under", "between", "through",
    "during", "before", "after", "while", "using",
    "used", "use"
}


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# GET WORDS
# ============================================================

def get_words(text):
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", text.lower())

    words = [
        word for word in words
        if word not in STOPWORDS
    ]

    return words


# ============================================================
# KEYWORDS
# ============================================================

def get_keywords(text, limit=10):

    words = get_words(text)

    counter = Counter(words)

    result = []

    for word, count in counter.most_common():

        if word not in result:
            result.append(word)

        if len(result) >= limit:
            break

    return result


# ============================================================
# SENTENCES
# ============================================================

def get_sentences(text):

    text = re.sub(r"\s+", " ", text)

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


# ============================================================
# MAIN POINTS
# ============================================================

def get_main_points(text, limit=8):

    sentences = get_sentences(text)

    if not sentences:
        return []


    keywords = get_keywords(
        text,
        limit=15
    )


    scored_sentences = []


    for sentence in sentences:

        words = set(
            get_words(sentence)
        )


        score = 0

        for keyword in keywords:

            if keyword in words:
                score += 1


        # Prefer reasonably sized sentences
        if 40 <= len(sentence) <= 250:
            score += 1


        scored_sentences.append(
            (score, sentence)
        )


    scored_sentences.sort(
        key=lambda x: x[0],
        reverse=True
    )


    points = []


    for score, sentence in scored_sentences:

        if sentence not in points:

            points.append(sentence)


        if len(points) >= limit:
            break


    return points


# ============================================================
# SUMMARY
# ============================================================

def make_summary(text):

    sentences = get_sentences(text)

    if not sentences:
        return "No readable text was found in this document."


    points = get_main_points(
        text,
        limit=3
    )


    if points:

        return " ".join(points)


    return " ".join(
        sentences[:3]
    )


# ============================================================
# FIND SENTENCE FOR KEYWORD
# ============================================================

def find_points_for_keyword(
    keyword,
    sentences,
    used_sentences,
    limit=2
):

    keyword = keyword.lower()

    matches = []


    for sentence in sentences:

        if sentence in used_sentences:
            continue


        words = set(
            get_words(sentence)
        )


        if keyword in words:

            matches.append(sentence)


        if len(matches) >= limit:
            break


    return matches


# ============================================================
# CREATE STRUCTURED MIND MAP
# ============================================================

def create_branches(
    title,
    text,
    keywords
):

    sentences = get_sentences(text)

    branches = []

    used_sentences = set()


    # --------------------------------------------------------
    # Create branches from keywords
    # --------------------------------------------------------

    for keyword in keywords[:8]:

        points = find_points_for_keyword(
            keyword,
            sentences,
            used_sentences,
            limit=2
        )


        cleaned_points = []


        for point in points:

            short_point = point.strip()


            # Keep point readable
            if len(short_point) > 150:

                short_point = (
                    short_point[:147] + "..."
                )


            cleaned_points.append(
                short_point
            )


            used_sentences.add(point)


        branches.append(
            {
                "name": keyword.title(),
                "points": cleaned_points
            }
        )


    # --------------------------------------------------------
    # If keyword branches don't have points,
    # distribute important points.
    # --------------------------------------------------------

    all_points = get_main_points(
        text,
        limit=10
    )


    for index, branch in enumerate(branches):

        if not branch["points"]:

            if index < len(all_points):

                point = all_points[index]

                if len(point) > 150:

                    point = (
                        point[:147] + "..."
                    )

                branch["points"].append(
                    point
                )


    # --------------------------------------------------------
    # Remove empty branches
    # --------------------------------------------------------

    branches = [
        branch
        for branch in branches
        if branch["name"]
    ]


    return branches


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_pdf_text(file):

    text = ""


    try:

        pdf = fitz.open(
            stream=file.read(),
            filetype="pdf"
        )


        for page in pdf:

            page_text = page.get_text()

            if page_text:

                text += "\n" + page_text


        pdf.close()


    except Exception as e:

        raise Exception(
            "Could not read the PDF: " + str(e)
        )


    return clean_text(text)


# ============================================================
# PDF ANALYSIS API
# ============================================================

@app.route(
    "/api/analyze-pdf",
    methods=["POST"]
)
def analyze_pdf():

    try:

        if "pdf" not in request.files:

            return jsonify(
                {
                    "error":
                    "No PDF file was uploaded."
                }
            ), 400


        file = request.files["pdf"]


        if file.filename == "":

            return jsonify(
                {
                    "error":
                    "Please select a PDF file."
                }
            ), 400


        if not file.filename.lower().endswith(".pdf"):

            return jsonify(
                {
                    "error":
                    "Only PDF files are allowed."
                }
            ), 400


        # ----------------------------------------------------
        # Extract PDF text
        # ----------------------------------------------------

        text = extract_pdf_text(file)


        if not text:

            return jsonify(
                {
                    "error":
                    "No readable text was found in the PDF. "
                    "If this is a scanned PDF, OCR is required."
                }
            ), 400


        # ----------------------------------------------------
        # Generate title
        # ----------------------------------------------------

        first_sentences = get_sentences(text)


        if first_sentences:

            title = first_sentences[0][:80]

        else:

            title = "PDF Document"


        # ----------------------------------------------------
        # Keywords
        # ----------------------------------------------------

        keywords = get_keywords(
            text,
            limit=10
        )


        # ----------------------------------------------------
        # Main points
        # ----------------------------------------------------

        points = get_main_points(
            text,
            limit=8
        )


        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        summary = make_summary(
            text
        )


        # ----------------------------------------------------
        # Structured mind map
        # ----------------------------------------------------

        branches = create_branches(
            title,
            text,
            keywords
        )


        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return jsonify(
            {
                "title": title,
                "summary": summary,
                "keywords": keywords,
                "points": points,
                "branches": branches,
                "source": "Uploaded PDF"
            }
        )


    except Exception as e:

        print(
            "PDF ERROR:",
            str(e)
        )


        return jsonify(
            {
                "error":
                "PDF analysis failed: " + str(e)
            }
        ), 500


# ============================================================
# WIKIPEDIA TOPIC SEARCH
# ============================================================

def get_wikipedia_topic(topic):

    url = (
        "https://en.wikipedia.org/api/rest_v1/"
        "page/summary/"
        + requests.utils.quote(topic)
    )


    try:

        response = requests.get(
            url,
            timeout=8,
            headers={
                "User-Agent":
                "PDF-Mind-Mapper-AI/1.0"
            }
        )


        if response.status_code == 200:

            data = response.json()


            extract = data.get(
                "extract",
                ""
            )


            if extract:

                return {
                    "title":
                    data.get(
                        "title",
                        topic
                    ),

                    "text":
                    extract,

                    "source":
                    "Wikipedia"
                }


    except Exception as e:

        print(
            "Wikipedia error:",
            str(e)
        )


    return None


# ============================================================
# FALLBACK TOPIC CONTENT
# ============================================================

def create_fallback_topic(topic):

    text = f"""
    {topic} is an important topic that can be studied
    through its basic concepts, applications, advantages,
    limitations, and real-world uses.

    The main concepts of {topic} help learners understand
    how the subject works and where it can be applied.

    Learning {topic} includes understanding its fundamentals,
    important terminology, practical applications, and
    related technologies.

    {topic} can be explored through examples, projects,
    experiments, and further study.
    """


    return clean_text(text)


# ============================================================
# NEW TOPIC API
# ============================================================

@app.route(
    "/api/new-topic",
    methods=["POST"]
)
def new_topic():

    try:

        data = request.get_json(
            silent=True
        )


        if not data:

            return jsonify(
                {
                    "error":
                    "Invalid request."
                }
            ), 400


        topic = str(
            data.get(
                "topic",
                ""
            )
        ).strip()


        if not topic:

            return jsonify(
                {
                    "error":
                    "Please enter a topic."
                }
            ), 400


        # ----------------------------------------------------
        # Try Wikipedia
        # ----------------------------------------------------

        wiki_data = get_wikipedia_topic(
            topic
        )


        if wiki_data:

            title = wiki_data["title"]

            text = wiki_data["text"]

            source = wiki_data["source"]

        else:

            title = topic

            text = create_fallback_topic(
                topic
            )

            source = "Generated topic content"


        # ----------------------------------------------------
        # Keywords
        # ----------------------------------------------------

        keywords = get_keywords(
            text,
            limit=10
        )


        # ----------------------------------------------------
        # Main points
        # ----------------------------------------------------

        points = get_main_points(
            text,
            limit=8
        )


        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        summary = make_summary(
            text
        )


        # ----------------------------------------------------
        # Mind map
        # ----------------------------------------------------

        branches = create_branches(
            title,
            text,
            keywords
        )


        # ----------------------------------------------------
        # Return result
        # ----------------------------------------------------

        return jsonify(
            {
                "title": title,
                "summary": summary,
                "keywords": keywords,
                "points": points,
                "branches": branches,
                "source": source
            }
        )


    except Exception as e:

        print(
            "TOPIC ERROR:",
            str(e)
        )


        return jsonify(
            {
                "error":
                "Topic generation failed: " +
                str(e)
            }
        ), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify(
        {
            "status": "ok",
            "message":
            "PDF Mind Mapper AI is running"
        }
    )


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
