# Central Georgia Inventory Finder (Live Version)
# Flask-based web app to display localized inventory across Central GA with real-time scraping

from flask import Flask, render_template, request, jsonify
from datetime import datetime
import openai
import os
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Load API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

cities = ["macon", "warner-robins", "perry", "milledgeville", "byron"]
categories = ["firewood", "propane", "cold-medicine", "distilled-water", "ammo"]

# Real-time scraping function (placeholder logic)
def get_live_inventory(city, category):
    listings = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Example: scrape from a simulated local store (replace with real URLs)
    if city == "macon" and category == "firewood":
        try:
            response = requests.get("https://example.com/stores/macon/firewood")  # Replace with real endpoint
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select(".inventory-item")
            for item in items:
                listings.append({
                    "store": item.select_one(".store-name").text,
                    "address": item.select_one(".store-address").text,
                    "status": item.select_one(".stock-status").text,
                    "last_checked": now,
                    "notes": item.select_one(".notes").text
                })
        except Exception as e:
            print(f"Scraping error: {e}")

    return listings

# AI-generated local intro for SEO

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
