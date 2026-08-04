import json

paris_facts = [
    {
        "city": "Paris",
        "category": "landmarks",
        "content": "The Eiffel Tower is best visited at dusk for dramatic lighting. Book timed tickets online to skip the queues. The Trocadéro gardens offer the best free view.",
        "tags": ["culture", "iconic", "view"],
        "budget_tiers": ["medium", "high"],
        "lat": 48.8584,
        "lon": 2.2945
    },
    {
        "city": "Paris",
        "category": "landmarks",
        "content": "The Louvre holds the world's largest art collection — prioritize the Denon Wing for the Mona Lisa and Winged Victory.",
        "tags": ["culture", "art"],
        "budget_tiers": ["medium", "high"],
        "lat": 48.8606,
        "lon": 2.3376
    },
    {
        "city": "Paris",
        "category": "landmarks",
        "content": "The Musée d'Orsay, housed in a former railway station, is ideal for Impressionist art lovers.",
        "tags": ["culture", "art"],
        "budget_tiers": ["medium", "high"],
        "lat": 48.8600,
        "lon": 2.3266
    },
    {
        "city": "Paris",
        "category": "adventure",
        "content": "Climb to the top of the Arc de Triomphe for a panoramic view of the 12 radiating avenues, including the Champs-Élysées.",
        "tags": ["adventure", "iconic", "view"],
        "budget_tiers": ["medium"],
        "lat": 48.8738,
        "lon": 2.2950
    },
    {
        "city": "Paris",
        "category": "relaxation",
        "content": "Relax in the Jardin du Luxembourg, a tranquil oasis in the 6th arrondissement with beautiful Medici fountains and tree-lined promenades.",
        "tags": ["relaxation", "nature", "parks"],
        "budget_tiers": ["low", "medium", "high"],
        "lat": 48.8462,
        "lon": 2.3371
    },
    {
        "city": "Paris",
        "category": "neighborhoods",
        "content": "Le Marais (3rd and 4th arrondissements) is Paris's historic Jewish quarter and LGBTQ+ hub, packed with galleries, falafel shops on Rue des Rosiers, and boutique fashion.",
        "tags": ["neighborhoods", "culture", "local"],
        "budget_tiers": ["low", "medium", "high"],
        "lat": 48.8575,
        "lon": 2.3588
    },
    {
        "city": "Paris",
        "category": "neighborhoods",
        "content": "Montmartre (18th) is a hilltop village with Place du Tertre artists, Sacré-Cœur Basilica, and genuine local bistros on Rue Lepic.",
        "tags": ["neighborhoods", "culture", "local"],
        "budget_tiers": ["low", "medium", "high"],
        "lat": 48.8867,
        "lon": 2.3431
    },
    {
        "city": "Paris",
        "category": "cuisine",
        "content": "Classic Parisian breakfasts: a croissant and café au lait at any neighborhood boulangerie — avoid tourist cafés near major sights.",
        "tags": ["food", "local", "authentic"],
        "budget_tiers": ["low", "medium", "high"]
    },
    {
        "city": "Paris",
        "category": "culture",
        "content": "Greet shopkeepers with 'Bonjour' before speaking — it's considered rude not to. Tipping is not mandatory but rounding up 1–2 euros is appreciated.",
        "tags": ["culture", "etiquette", "tips"],
        "budget_tiers": ["low", "medium", "high", "luxury"]
    },
    {
        "city": "Paris",
        "category": "nightlife",
        "content": "Paris nightlife starts late — clubs don't fill until midnight. Canal Saint-Martin area has trendy bars with outdoor seating.",
        "tags": ["nightlife", "bars"],
        "budget_tiers": ["medium", "high"],
        "lat": 48.8732,
        "lon": 2.3645
    },
    {
        "city": "Paris",
        "category": "shopping",
        "content": "Galeries Lafayette and Le Bon Marché are Paris's iconic department stores — the food hall at Le Bon Marché (La Grande Épicerie) is spectacular.",
        "tags": ["shopping", "luxury"],
        "budget_tiers": ["medium", "high", "luxury"],
        "lat": 48.8738,
        "lon": 2.3323
    }
]

def main():
    path = "backend/data/kb/destinations.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Filter out old Paris data
    new_data = [entry for entry in data if entry.get("city") != "Paris"]
    
    # Insert new highly granular Paris data at the beginning
    new_data = paris_facts + new_data
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
        
    print("Successfully updated destinations.json with granular Paris facts and coordinates.")

if __name__ == "__main__":
    main()
