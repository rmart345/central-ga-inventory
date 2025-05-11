# Central Georgia Inventory Finder (AI-Powered Realtime with Logging and Fallback)
# Flask-based web app with dynamic AI-driven data retrieval for inventory across Central GA

from flask import Flask, render_template, request, jsonify
from datetime import datetime
import os
import json
import logging
import requests
from openai import OpenAI
from functools import lru_cache

app = Flask(__name__)

# Load API key from environment and initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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

@app.route("/classify_type", methods=["POST"])
def classify_type():
    try:
        data = request.get_json()
        user_input = data.get("text", "").strip()
        if not user_input:
            return jsonify({"error": "Missing input text."}), 400

        prompt = f"What kind of store typically sells this: '{user_input}'? Respond with just one or two words like 'pharmacy', 'grocery store', 'hardware store', or 'automotive'."
        logger.info(f"Classifying type for: {user_input}")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that classifies items by store type."},
                {"role": "user", "content": prompt}
            ]
        )
        result = response.choices[0].message.content.strip()
        return jsonify({"store_type": result})
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return jsonify({"error": "Unable to classify store type."}), 500

@app.route("/test_places_api")
def test_places_api():
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": "Walmart in Macon, Georgia",
        "key": api_key
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        return jsonify({
            "status": data.get("status"),
            "results_found": len(data.get("results", [])),
            "first_result": data.get("results", [])[0] if data.get("results") else None
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@lru_cache(maxsize=100)
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

def verify_store_exists(store_name, city):
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    query = f"{store_name} {city}, Georgia"
    params = {"query": query, "key": api_key}

    try:
        response = requests.get(base_url, params=params)
        logger.debug(f"Verifying store: {store_name} in {city}")
        logger.debug(f"Google Places API response: {response.json()}")
        results = response.json().get("results", [])
        for result in results:
            if result.get("business_status") in [None, "OPERATIONAL"]:
                return True
        return False
    except Exception as e:
        logger.warning(f"Store verification failed for {store_name}: {e}")
        return False

def get_live_inventory(city, category):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        prompt = (
            f"Return only a valid JSON array. List at least 10 stores in {city.title()}, Georgia that currently carry the item '{category.replace('-', ' ')}'. "
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
        start_idx = raw_content.find('[')
        end_idx = raw_content.rfind(']') + 1
        json_data = raw_content[start_idx:end_idx]
        parsed = json.loads(json_data)
        logger.debug(f"GPT returned stores: {json.dumps(parsed, indent=2)}")
        verified = []
        for store in parsed:
            if verify_store_exists(store["store"], city):
                store["last_checked"] = now
                verified.append(store)

        if not verified:
            raise Exception("No verified stores found.")

        quality_prompt = (
            "Given this list of stores, evaluate their quality of service based on names and notes. "
            "Assign a 'quality' label (Excellent, Good, Fair, Poor) to each store. Return a JSON array with an added 'quality' field per store.\n"
            f"Here is the data: {json.dumps(verified)}"
        )
        quality_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that evaluates customer service based on store info."},
                {"role": "user", "content": quality_prompt}
            ]
        )
        quality_data = quality_response.choices[0].message.content.strip()
        enriched = json.loads(quality_data)

        def extract_price(it):
            try:
                return float(str(it["price"]).replace("$", "").replace(",", ""))
            except:
                return float('inf')

        for item in enriched:
            if isinstance(item.get("price"), str) and item["price"].startswith("$"):
                try:
                    item["price"] = float(item["price"].replace("$", "").replace(",", ""))
                except:
                    item["price"] = "Unknown"

        enriched.sort(key=extract_price)
        return enriched

    except Exception as e:
        logger.error(f"Inventory fetch failed: {e}")
        return [
            {
                "store": "Example Supply Co.",
                "address": f"123 Main St, {city.title()}, GA",
                "price": "Unknown",
                "quantity": "Unknown",
                "last_checked": now,
                "notes": f"Example listing for {category}.",
                "quality": "Unknown"
            }
        ]

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
