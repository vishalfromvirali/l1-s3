import os
import re
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request
from serpapi import GoogleSearch



app = Flask(__name__)

# Cache to reduce API usage
cache = {
    "who is create you": {
        "summary": ["His name is Vishal."],
        "error": None,
        "urls_found": ["https://novix-chat-3.onrender.com"]
    }
}

# ---------------------- CLEAN TEXT ----------------------
def clean_text(text):
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ---------------------- SCRAPE WEBSITE ----------------------
def scrape_and_clean_text(url):
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        response.raise_for_status()
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}")
        return ""

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove useless tags
    for tag in soup(["script", "style", "header", "footer", "nav", "iframe"]):
        tag.decompose()

    main_content = soup.find("main") or soup.body
    if not main_content:
        return ""

    text_elements = main_content.find_all(string=True)
    visible_texts = [t.strip() for t in text_elements if t.strip()]

    full_text = clean_text(" ".join(visible_texts))

    return full_text if len(full_text) > 150 else ""

# ---------------------- SIMPLE SUMMARIZER (NO NLTK) ----------------------
def summarize_text(full_text):
    if not full_text:
        return []

    sentences = re.split(r'(?<=[.!?]) +', full_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 40]

    return sentences[:5] if sentences else ["Not enough content to summarize."]

# ---------------------- ROUTES ----------------------
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        topic = request.form.get('topic', '').strip()

        if not topic:
            return render_template("index.html", error="Please enter a topic.")

        # Cache check
        if topic in cache:
            return render_template(
                "index.html",
                topic=topic,
                summary=cache[topic]["summary"],
                urls_found=cache[topic]["urls_found"],
                error=cache[topic]["error"]
            )

        api_key = os.environ.get("SERPAPI_API_KEY")
        if not api_key:
            return render_template("index.html", error="SERPAPI_API_KEY is missing!")

        params = {
            "engine": "google",
            "q": topic,
            "api_key": api_key,
            "num": "5"
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            organic = results.get("organic_results", [])
            urls = [x["link"] for x in organic if "link" in x]
        except Exception as e:
            return render_template("index.html", error=f"API Error: {e}")

        if not urls:
            return render_template("index.html", error="No search results found.")

        all_text = ""
        found_urls = []

        for url in urls:
            page_text = scrape_and_clean_text(url)
            if page_text:
                all_text += page_text + "\n"
                found_urls.append(url)
            time.sleep(1)

        summary = summarize_text(all_text)

        cache[topic] = {
            "summary": summary,
            "urls_found": found_urls,
            "error": None
        }

        return render_template(
            "index.html",
            topic=topic,
            summary=summary,
            urls_found=found_urls,
            error=None
        )

    return render_template("index.html")

# ---------------------- RUN SERVER ----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
