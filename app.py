import os
import re
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request

# ✅ Correct import for serpapi v0.1.5
from serpapi import serp_api_client

from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer

app = Flask(__name__)

cache = {}

# -------------------------------
# Helpers
# -------------------------------
def clean_text(text):
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def scrape_and_clean_text(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
    except Exception:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = clean_text(text)

    if len(text) < 150:
        return ""

    return text

def summarize_text(text):
    if len(text) < 100:
        return []

    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, 4)

    return [str(sentence) for sentence in summary]

# -------------------------------
# Routes
# -------------------------------
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        topic = request.form.get("topic")

        if not topic:
            return render_template("index.html", error="Please type a topic.")

        if topic in cache:
            return render_template("index.html", summary=cache[topic])

        API_KEY = os.environ.get("SERPAPI_API_KEY")
        if not API_KEY:
            return render_template("index.html", error="SERPAPI_API_KEY not set")

        # ✅ SerpApi client (correct usage)
        client = serp_api_client.Client(api_key=API_KEY)

        results = client.search({
            "engine": "google",
            "q": topic,
            "num": 5
        })

        urls = []
        organic = results.get("organic_results", [])
        for r in organic:
            if "link" in r:
                urls.append(r["link"])

        all_text = ""

        for url in urls:
            text = scrape_and_clean_text(url)
            if text:
                all_text += text + "\n"
            time.sleep(1)

        summary = summarize_text(all_text)

        cache[topic] = summary

        return render_template("index.html", summary=summary)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
