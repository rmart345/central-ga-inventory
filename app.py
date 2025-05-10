# Central Georgia Inventory Finder (MVP Scaffold)
# Flask-based web app to display localized inventory across Central GA

from flask import Flask, render_template, request, jsonify
from datetime import datetime
import openai  # Add OpenAI for content generation
import os

app = Flask(__name__, template_folder="templates")

# Load API key from environment or config
openai.api_key = os.getenv("OPENAI_API_KEY")

# Sample city/category database (could be expanded to a real DB later)
cities = ["macon", "warner-robins", "perry", "milledgeville", "byron"]
categories = ["firewood", "propane", "cold-medicine", "distilled-water", "ammo"]

# Sample static inventory data (to be replaced by AI-powered scraper)
inventory_data = {
    ("macon", "firewood"): [
        {
            "store": "Tractor Supply Co.",
            "address": "123 Gray Hwy, Macon, GA",
            "status": "In Stock",
            "last_checked": "2025-05-10 14:00",
            "notes": "Pickup only"
        },
        {
            "store": "Ace Hardware",
            "address": "456 Vineville Ave, Macon, GA",
            "status": "Low Stock",
            "last_checked": "2025-05-10 13:30",
            "notes": "Delivery available"
        }
    ],
    ("warner-robins", "propane"): [
        {
            "store": "U-Haul Neighborhood Dealer",
            "address": "789 Watson Blvd, Warner Robins, GA",
            "status": "In Stock",
            "last_checked": "2025-05-10 11:15",
            "notes": "Tank exchange only"
        }
    ]
}

# AI content generation for SEO and user context
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

    inventory = inventory_data.get((city, category), [])
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
