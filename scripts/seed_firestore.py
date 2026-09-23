import sys
from google.cloud import firestore

# Hardcoded project ID as required for Agent Platform compatibility
PROJECT_ID = "qwiklabs-gcp-01-415e839ac4f7"

SEED_DESTINATIONS = [
    {
        "id": "tokyo-japan",
        "name": "Tokyo, Japan",
        "category": "Culinary",
        "budget_tier": "Moderate",
        "avg_daily_cost_usd": 160.0,
        "description": "Vibrant metropolis blending futuristic neon skyscrapers with ancient temples and world-class street food.",
        "dietary_friendly": ["Vegetarian", "Gluten-Free Options", "Nut-Free Options"],
        "highlights": ["Senso-ji Temple", "Shibuya Crossing", "Tsukiji Outer Market", "Shinjuku Gyoen"]
    },
    {
        "id": "kyoto-japan",
        "name": "Kyoto, Japan",
        "category": "Historical",
        "budget_tier": "Moderate",
        "avg_daily_cost_usd": 130.0,
        "description": "Japan's cultural heart filled with classical Buddhist temples, gardens, imperial palaces, and traditional wooden houses.",
        "dietary_friendly": ["Vegetarian", "Vegan", "Gluten-Free Options"],
        "highlights": ["Fushimi Inari Shrine", "Kinkaku-ji (Golden Pavilion)", "Arashiyama Bamboo Grove"]
    },
    {
        "id": "paris-france",
        "name": "Paris, France",
        "category": "Historical",
        "budget_tier": "Luxury",
        "avg_daily_cost_usd": 220.0,
        "description": "Global center for art, fashion, gastronomy, and culture with iconic landmarks and romantic boulevards.",
        "dietary_friendly": ["Vegetarian", "Gluten-Free Options"],
        "highlights": ["Eiffel Tower", "Louvre Museum", "Montmartre", "Notre-Dame Cathedral"]
    },
    {
        "id": "cancun-mexico",
        "name": "Cancun, Mexico",
        "category": "Beach",
        "budget_tier": "Budget",
        "avg_daily_cost_usd": 95.0,
        "description": "Tropical paradise on the Yucatan Peninsula known for white sand beaches, turquoise waters, and Mayan ruins.",
        "dietary_friendly": ["Vegetarian", "Gluten-Free", "Nut-Free Options"],
        "highlights": ["Playa Delfines", "Chichen Itza Excursion", "Isla Mujeres", "Cenote Ik Kil"]
    },
    {
        "id": "rome-italy",
        "name": "Rome, Italy",
        "category": "Culinary",
        "budget_tier": "Moderate",
        "avg_daily_cost_usd": 150.0,
        "description": "The Eternal City, packed with almost 3,000 years of globally influential art, architecture, and mouth-watering cuisine.",
        "dietary_friendly": ["Vegetarian", "Gluten-Free Options"],
        "highlights": ["Colosseum", "Pantheon", "Trevi Fountain", "Vatican Museums"]
    }
]

def seed():
    print(f"Connecting to Firestore with project ID: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection("destinations")
    
    for item in SEED_DESTINATIONS:
        doc_id = item["id"]
        data = {k: v for k, v in item.items() if k != "id"}
        collection.document(doc_id).set(data)
        print(f"Seeded destination: {item['name']} ({doc_id})")
        
    print("Successfully seeded all destinations to Firestore!")

if __name__ == "__main__":
    seed()
