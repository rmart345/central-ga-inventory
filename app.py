# Central Georgia Inventory Finder (AI-Powered Realtime with Logging and Fallback)
# Flask-based web app with dynamic AI-driven data retrieval for inventory across Central GA

from flask import Flask, render_template, request, jsonify
from datetime import datetime
import os
import json
import logging
from openai import OpenAI

app = Flask(__name__)

# Load API key from environment and initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cities = ["macon", "warner-robins", "perry", "milledgeville", "byron"]
categories = ["firewood", "propane", "cold-medicine", "distilled-water", "ammo"]

item_options = {
    "firewood": ["oak firewood", "hickory firewood", "bundled firewood"],
    "propane": ["20lb propane tank", "refill station", "camping propane"],
    "cold-medicine": ["DayQuil", "NyQuil", "Sudafed"],
    "distilled-water": ["gallon jug", "2.5 gallon", "bulk refill"],
    "ammo": ["9mm rounds", "12 gauge shells", ".223 Remington"]
}

@app.route("/")
def home():
    return render_template("search.html", cities=cities)

@app.route("/get_items", methods=["POST"])
def get_items():
    try:
        data = request.get_json()
        category = data.get("category", "").strip()

        if not category:
            return jsonify({"error": "Missing category input."}), 400

        prompt = (
            f"List 5 common item types or subcategories that belong to the category '{category}'. "
            f"Respond only with a clean JSON array of strings."
        )

        logger.info(f"Fetching items for category: {category}")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns only a clean JSON array."},
                {"role": "user", "content": prompt}
            ]
        )

        raw = response.choices[0].message.content.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        cleaned = raw[start:end]
        items = json.loads(cleaned)

        return jsonify({"items": items})

    except Exception as e:
        logger.error(f"Failed to fetch item list from AI: {e}")
        return jsonify({"error": "Unable to retrieve items for the given category."}), 500
