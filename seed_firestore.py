"""Seed script to populate Firestore with initial noodle products and sample orders."""

from google.cloud import firestore

# Hardcoded GCP Project ID
PROJECT_ID = "qwiklabs-gcp-04-9f640202d071"

SEED_PRODUCTS = [
    {
        "id": "ramen-tokyo-wave",
        "name": "Tokyo Wavy Ramen Noodles",
        "type": "Ramen",
        "price_per_kg": 7.50,
        "stock_kg": 250,
        "min_batch_kg": 5.0,
        "shelf_life_days": 10,
        "description": "Medium-thick, wavy alkaline noodles perfect for shoyu, miso, and rich tonkotsu broths.",
    },
    {
        "id": "ramen-hakata-thin",
        "name": "Hakata Straight Thin Ramen Noodles",
        "type": "Ramen",
        "price_per_kg": 8.00,
        "stock_kg": 180,
        "min_batch_kg": 5.0,
        "shelf_life_days": 8,
        "description": "Ultra-thin, low hydration straight noodles with high firmness for traditional Hakata tonkotsu.",
    },
    {
        "id": "udon-sanuki",
        "name": "Artisan Sanuki Udon",
        "type": "Udon",
        "price_per_kg": 6.80,
        "stock_kg": 300,
        "min_batch_kg": 10.0,
        "shelf_life_days": 7,
        "description": "Thick, chewy, square-cut wheat noodles with exceptional elasticity (koshi).",
    },
    {
        "id": "soba-shinshu",
        "name": "Shinshu Buckwheat Soba (80% Buckwheat)",
        "type": "Soba",
        "price_per_kg": 9.50,
        "stock_kg": 120,
        "min_batch_kg": 5.0,
        "shelf_life_days": 6,
        "description": "Aromatic stone-ground buckwheat noodles (Ni-Hachi style) with delicate earthy flavor.",
    },
    {
        "id": "egg-hongkong-wonton",
        "name": "Hong Kong Crispy Wonton Noodles",
        "type": "Egg Noodles",
        "price_per_kg": 7.20,
        "stock_kg": 150,
        "min_batch_kg": 5.0,
        "shelf_life_days": 12,
        "description": "Fine, springy egg noodles enriched with fresh duck egg yolks, ideal for wonton soups or pan-frying.",
    },
]

SEED_ORDERS = [
    {
        "id": "ORDER-1001",
        "customer_name": "Ramen Yatai Downtown",
        "product_id": "ramen-tokyo-wave",
        "product_name": "Tokyo Wavy Ramen Noodles",
        "quantity_kg": 25.0,
        "price_per_kg": 7.50,
        "total_price": 187.50,
        "delivery_address": "452 Market St, San Francisco, CA",
        "delivery_date": "2026-10-10",
        "status": "in_transit",
        "special_notes": "Firm cut #22 gauge",
        "created_at": "2026-10-08T10:00:00Z",
    },
    {
        "id": "ORDER-1002",
        "customer_name": "Sakura Udon & Izakaya",
        "product_id": "udon-sanuki",
        "product_name": "Artisan Sanuki Udon",
        "quantity_kg": 50.0,
        "price_per_kg": 6.80,
        "total_price": 340.00,
        "delivery_address": "789 Mission St, San Francisco, CA",
        "delivery_date": "2026-10-11",
        "status": "processing",
        "special_notes": "Deliver before 11am before lunch rush",
        "created_at": "2026-10-08T12:30:00Z",
    },
]


def seed_firestore():
    print(f"Connecting to Firestore with project '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)

    print("Seeding 'noodle_products' collection...")
    for prod in SEED_PRODUCTS:
        doc_id = prod["id"]
        doc_data = {k: v for k, v in prod.items() if k != "id"}
        db.collection("noodle_products").document(doc_id).set(doc_data)
        print(f"  + Added product: {doc_id} ({prod['name']})")

    print("Seeding 'noodle_orders' collection...")
    for order in SEED_ORDERS:
        order_id = order["id"]
        order_data = {k: v for k, v in order.items() if k != "id"}
        db.collection("noodle_orders").document(order_id).set(order_data)
        print(f"  + Added sample order: {order_id} for {order['customer_name']}")

    print("Firestore seeding completed successfully!")


if __name__ == "__main__":
    seed_firestore()
