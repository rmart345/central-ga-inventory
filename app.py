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
    return render_template("search.html", cities=cities, year=datetime.now().year)

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        city = request.form.get("city", "").lower()
        category = request.form.get("category", "").lower()
        item = request.form.get("item", "").lower()

        if city not in cities or not category or not item:
            return render_template("not_found.html", city=city, category=category, year=datetime.now().year)

        inventory = get_live_inventory(city, item)
        intro_text = generate_ai_intro(city, item)

        return render_template(
        "inventory.html",
        year=datetime.now().year,
            city=city.title(),
            category=item.replace("-", " ").title(),
            inventory=inventory,
            intro=intro_text
        )

    return render_template("search.html", cities=cities)

def get_live_inventory(city, category):
    # Future enhancement: Use Google Places or Yelp API here to collect real store data with ratings and review summaries.
    """
    This function should be extended to use a real store location or product API (e.g., Google Places, Walmart API).
    GPT will only be used to sort, evaluate, and generate quality analysis based on fetched data.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        prompt = (
        f"Return only a valid JSON array. List at least 15 real stores in {city.title()}, Georgia that currently carry the item '{category.replace('-', ' ')}'. "
        f"Each object should include: 'store', 'address', 'price', 'quantity', and 'notes'."
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

        # 🔍 Optionally analyze quality of service using GPT
        try:
            quality_prompt = (
                "Given this list of stores with price and quantity, evaluate their quality of service based on names and notes. "
                "Assign a 'quality' label (Excellent, Good, Fair, Poor) to each store. Return a JSON array with an added 'quality' field per store.\n"
                f"Here is the data: {json.dumps(parsed)}"
            )
            quality_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an assistant that evaluates customer service based on store info."},
                    {"role": "user", "content": quality_prompt}
                ]
            )
            quality_data = quality_response.choices[0].message.content.strip()
            parsed = json.loads(quality_data)
        except Exception as qerr:
            logger.warning(f"Could not enrich with quality labels: {qerr}")
            for item in parsed:
                item.setdefault("quality", "Unknown")

        for item in parsed:
            item["last_checked"] = now
            if "price" not in item or not item["price"]:
                item["price"] = "Unknown"
            if "quantity" not in item or not item["quantity"]:
                item["quantity"] = "Unknown"

        # Optional: sort by price if possible
        def extract_price(it):
            try:
                return float(str(it["price"]).replace("$", "").replace(",", ""))
            except:
                return float('inf')

        parsed.sort(key=extract_price)

        return parsed
    except Exception as e:
        logger.error(f"AI inventory fetch error: {e}")
        return [
            {
                "store": "Example Supply Co.",
                "address": f"123 Main St, {city.title()}, GA",
                "price": "Unknown",
                "quantity": "Unknown",
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
