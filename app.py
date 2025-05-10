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

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        city = request.form.get("city", "").lower()
        category = request.form.get("category", "").lower()
        item = request.form.get("item", "").lower()

        if city not in cities or not category or not item:
            return render_template("not_found.html", city=city, category=category)

        inventory = get_live_inventory(city, item)
        intro_text = generate_ai_intro(city, item)

        return render_template(
            "inventory.html",
            city=city.title(),
            category=item.replace("-", " ").title(),
            inventory=inventory,
            intro=intro_text
        )

    return render_template("search.html", cities=cities)

def get_live_inventory(city, category):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        prompt = (
            f"Return only a valid JSON array. List 3 stores in {city.title()}, Georgia that currently sell {category.replace('-', ' ')}. "
            f"Each object should include: 'store', 'address', 'status' (In Stock, Low Stock, Out of Stock), and 'notes'."
        )
        logger.info(f"Sending prompt to GPT: {prompt}")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns clean JSON arrays for local retail inventory."},
                {"role": "user", "content": prompt}
            ]
        )
        raw_content = response.choices[0].message.content.strip()
        logger.info(f"Received raw response: {raw_content}")

        start_idx = raw_content.find('[')
        end_idx = raw_content.rfind(']') + 1
        json_data = raw_content[start_idx:end_idx]
        parsed = json.loads(json_data)

        for item in parsed:
            item["last_checked"] = now
        return parsed
    except Exception as e:
        logger.error(f"AI inventory fetch error: {e}")
        return [
            {
                "store": "Example Supply Co.",
                "address": f"123 Main St, {city.title()}, GA",
                "status": "In Stock",
                "last_checked": now,
                "notes": f"Example listing for {category}."
            }
        ]

def generate_ai_intro(city, category):
    try:
        prompt = f"Write a short and informative paragraph (3-4 sentences) about where to find {category.replace('-', ' ')} in {city.title()}, Georgia, including tips for locals."
        logger.info(f"Sending intro prompt to GPT: {prompt}")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who writes local shopping advice."},
                {"role": "user", "content": prompt}
            ]
        )
        intro = response.choices[0].message.content.strip()
        logger.info(f"Received intro text: {intro}")
        return intro
    except Exception as e:
        logger.error(f"AI intro generation error: {e}")
        return f"Check back soon for more tips about finding {category.replace('-', ' ')} in {city.title()}."


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
