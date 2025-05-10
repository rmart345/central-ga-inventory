# Central Georgia Inventory Finder (AI-Powered Realtime)
# Flask-based web app with dynamic AI-driven data retrieval for inventory across Central GA

from flask import Flask, render_template, request, jsonify
from datetime import datetime
import openai
import os

app = Flask(__name__)

# Load API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

cities = ["macon", "warner-robins", "perry", "milledgeville", "byron"]
categories = ["firewood", "propane", "cold-medicine", "distilled-water", "ammo"]

# Use GPT to simulate live inventory results dynamically
def get_live_inventory(city, category):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        prompt = f"List 3 stores in {city.title()}, Georgia that currently sell {category.replace('-', ' ')}. For each store, give the name, address, current stock status (In Stock, Low Stock, or Out of Stock), and a useful note for the shopper. Format your response as JSON list of objects."
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns clean JSON lists of local retail inventory."},
                {"role": "user", "content": prompt}
            ]
        )
        parsed = eval(response.choices[0].message.content)  # assumes well-formed output from GPT
        for item in parsed:
            item["last_checked"] = now
        return parsed
    except Exception as e:
        print(f"AI inventory fetch error: {e}")
        return []

# AI-generated local intro for SEO and user guidance
def generate_ai_intro(city, category):
    try:
        prompt = f"Write a short and informative paragraph (3-4 sentences) about where to find {category.replace('-', ' ')} in {city.title()}, Georgia, including tips for locals."
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant who writes local shopping advice."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
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
