# Central Georgia Inventory Finder (AI-Powered Realtime with Logging)
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

# Use GPT to simulate live inventory results dynamically
def get_live_inventory(city, category):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        prompt = (
            f"Return only a valid JSON array. List 3 stores in {city.title()}, Georgia that currently sell {category.replace('-', ' ')}. "
            f"Each object should include: 'store', 'address', 'status' (In Stock, Low Stock, Out of Stock), and 'notes'."
        )
        logger.info(f"Sending prompt to GPT: {prompt}")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns clean JSON arrays for local retail inventory."},
                {"role": "user", "content": prompt}
            ]
        )
        raw_content = response.choices[0].message.content.strip()
        logger.info(f"Received raw response: {raw_content}")

        # Parse JSON safely
        start_idx = raw_content.find('[')
        end_idx = raw_content.rfind(']') + 1
        json_data = raw_content[start_idx:end_idx]
        parsed = json.loads(json_data)

        for item in parsed:
            item["last_checked"] = now
        return parsed
    except Exception as e:
        logger.error(f"AI inventory fetch error: {e}")
        return []

# AI-generated local intro for SEO and user guidance
def generate_ai_intro(city, category):
    try:
        prompt = f"Write a short and informative paragraph (3-4 sentences) about where to find {category.replace('-', ' ')} in {city.title()}, Georgia, including tips for locals."
        logger.info(f"Sending intro prompt to GPT: {prompt}")
        response = client.chat.completions.create(
            model="gpt-4",
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

@app.route("/<city>/<category>")
def show_inventory(city, category):
    city = city.lower()
    category = category.lower()

    if city not in cities or category not in categories:
        return render_template("not_found.html", city=city, category=category)

    inventory = get_live_inventory(city, category)
    intro_text = generate_ai_intro(city, category)
    return render_template(
        "inventory.html",
        city=city.title(),
        category=category.replace("-", " ").title(),
        inventory=inventory,
        intro=intro_text
    )

@app.route("/")
def home():
    return render_template("home.html", cities=cities, categories=categories)

if __name__ == "__main__":
    app.run(debug=True)
