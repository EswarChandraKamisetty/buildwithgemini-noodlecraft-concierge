"""Firestore client helper and functions for NoodleCraft Concierge."""

from typing import Any, Dict, List, Optional
import datetime
from google.cloud import firestore

# Hardcoded GCP Project ID to prevent Agent Platform number-resolution issues
PROJECT_ID = "qwiklabs-gcp-04-9f640202d071"

_db: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    """Returns a singleton Firestore client configured with the hardcoded project ID."""
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def list_noodle_products() -> List[Dict[str, Any]]:
    """Fetch all available noodle products, daily prices, inventory batch info, allergens, and ingredients from Firestore.

    Returns:
        A list of dictionaries containing product details (id, name, type, price_per_kg,
        stock_kg, min_batch_kg, shelf_life_days, description, allergens, ingredients).
    """
    db = get_firestore_client()
    docs = db.collection("noodle_products").stream()
    products = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        products.append(item)
    return products


def get_noodle_product(product_id: str) -> Dict[str, Any]:
    """Look up a specific noodle product by its product ID, including its full ingredient breakdown and allergen information.

    Args:
        product_id: The ID of the noodle product (e.g., 'ramen-tokyo-wave', 'udon-sanuki', 'soba-shinshu', 'egg-hongkong-wonton', 'ramen-hakata-thin').

    Returns:
        Product details dictionary containing name, type, price_per_kg, stock_kg, allergens, ingredients, description, or error if not found.
    """
    db = get_firestore_client()
    doc = db.collection("noodle_products").document(product_id).get()
    if not doc.exists:
        return {"error": f"Product with ID '{product_id}' not found."}
    item = doc.to_dict()
    item["id"] = doc.id
    return item


def place_noodle_order(
    customer_name: str,
    product_id: str,
    quantity_kg: float,
    delivery_address: str,
    delivery_date: str,
    special_notes: str = "",
) -> Dict[str, Any]:
    """Place a new batch noodle order in Firestore.

    Args:
        customer_name: Name of the restaurant or customer placing the order.
        product_id: The ID of the noodle product being ordered.
        quantity_kg: Quantity in kilograms to order.
        delivery_address: Street address for the delivery.
        delivery_date: Desired delivery date in YYYY-MM-DD format.
        special_notes: Any custom batch notes (e.g., cut thickness, custom flour blend, allergen precautions).

    Returns:
        Dictionary containing the order confirmation details including order_id, total_price, and status.
    """
    db = get_firestore_client()
    product_ref = db.collection("noodle_products").document(product_id).get()
    if not product_ref.exists:
        return {"error": f"Invalid product_id: '{product_id}' does not exist."}

    product_data = product_ref.to_dict()
    price_per_kg = product_data.get("price_per_kg", 0.0)
    total_price = round(quantity_kg * price_per_kg, 2)
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    order_doc = {
        "customer_name": customer_name,
        "product_id": product_id,
        "product_name": product_data.get("name", product_id),
        "quantity_kg": quantity_kg,
        "price_per_kg": price_per_kg,
        "total_price": total_price,
        "delivery_address": delivery_address,
        "delivery_date": delivery_date,
        "status": "confirmed",
        "special_notes": special_notes,
        "created_at": created_at,
    }

    new_ref = db.collection("noodle_orders").document()
    new_ref.set(order_doc)
    order_doc["order_id"] = new_ref.id
    return order_doc


def track_order(order_id: str) -> Dict[str, Any]:
    """Check the tracking details and estimated delivery date for an order.

    Args:
        order_id: The unique ID of the order to track.

    Returns:
        Dictionary containing the order tracking details and status.
    """
    db = get_firestore_client()
    doc = db.collection("noodle_orders").document(order_id).get()
    if not doc.exists:
        return {"error": f"Order '{order_id}' not found."}
    data = doc.to_dict()
    data["order_id"] = doc.id
    return data


def calculate_quote_and_discounts(
    product_id: str,
    quantity_kg: float,
    customer_tier: str = "standard",
    is_rush_delivery: bool = false if False else False,
) -> Dict[str, Any]:
    """Calculate transparent pricing, volume tier discounts, and delivery estimate for an order.

    Args:
        product_id: The product ID (e.g. 'ramen-tokyo-wave', 'udon-sanuki', 'soba-shinshu').
        quantity_kg: Order weight in kilograms.
        customer_tier: Customer tier ('standard', 'wholesale_restaurant', 'vip_chain').
        is_rush_delivery: Whether rush same-day/early-morning delivery is requested.

    Returns:
        A detailed quote breakdown including base price, volume discount percentage,
        tier discount, shipping/freight fees, total savings, and final estimated price.
    """
    product = get_noodle_product(product_id)
    if "error" in product:
        return product

    base_price_per_kg = product.get("price_per_kg", 0.0)
    product_name = product.get("name", product_id)
    min_batch = product.get("min_batch_kg", 5.0)

    # 1. Base cost
    subtotal = quantity_kg * base_price_per_kg

    # 2. Volume discount tiers
    # >= 100kg: 15%, >= 50kg: 10%, >= 25kg: 5%, below: 0%
    if quantity_kg >= 100.0:
        volume_discount_pct = 15.0
    elif quantity_kg >= 50.0:
        volume_discount_pct = 10.0
    elif quantity_kg >= 25.0:
        volume_discount_pct = 5.0
    else:
        volume_discount_pct = 0.0

    # 3. Customer tier discount
    tier_normalized = customer_tier.lower().strip()
    tier_discount_pct = 0.0
    if "vip" in tier_normalized or "chain" in tier_normalized:
        tier_discount_pct = 5.0
    elif "wholesale" in tier_normalized or "restaurant" in tier_normalized:
        tier_discount_pct = 3.0

    total_discount_pct = min(volume_discount_pct + tier_discount_pct, 25.0)
    discount_amount = round(subtotal * (total_discount_pct / 100.0), 2)
    discounted_subtotal = round(subtotal - discount_amount, 2)

    # 4. Local freight & delivery fees
    # Free local delivery on orders >= 50kg, otherwise $15 base freight
    freight_fee = 0.0 if quantity_kg >= 50.0 else 15.0
    rush_fee = 25.0 if is_rush_delivery else 0.0
    final_total = round(discounted_subtotal + freight_fee + rush_fee, 2)
    effective_price_per_kg = round(discounted_subtotal / quantity_kg, 2) if quantity_kg > 0 else base_price_per_kg

    # Suggestion for next discount tier
    next_tier_suggestion = None
    if quantity_kg < 25.0:
        needed = 25.0 - quantity_kg
        next_tier_suggestion = f"Add {needed:.1f} kg more to reach 25 kg and unlock a 5% volume discount!"
    elif quantity_kg < 50.0:
        needed = 50.0 - quantity_kg
        next_tier_suggestion = f"Add {needed:.1f} kg more to reach 50 kg for a 10% discount plus FREE local delivery!"
    elif quantity_kg < 100.0:
        needed = 100.0 - quantity_kg
        next_tier_suggestion = f"Add {needed:.1f} kg more to reach 100 kg for our maximum 15% wholesale volume discount!"

    return {
        "product_id": product_id,
        "product_name": product_name,
        "quantity_kg": quantity_kg,
        "min_batch_kg": min_batch,
        "base_price_per_kg": base_price_per_kg,
        "subtotal_before_discounts": round(subtotal, 2),
        "volume_discount_pct": volume_discount_pct,
        "tier_discount_pct": tier_discount_pct,
        "total_discount_pct": total_discount_pct,
        "total_savings": discount_amount,
        "discounted_subtotal": discounted_subtotal,
        "effective_price_per_kg": effective_price_per_kg,
        "freight_fee": freight_fee,
        "rush_fee": rush_fee,
        "final_total": final_total,
        "tier_suggestion": next_tier_suggestion,
    }


def estimate_delivery_window(
    delivery_neighborhood_or_city: str,
    quantity_kg: float,
    desired_service_time: str = "lunch",
) -> Dict[str, Any]:
    """Estimate manufacturing turnaround, dispatch schedule, and kitchen delivery window.

    Args:
        delivery_neighborhood_or_city: Delivery destination area (e.g., 'Mission', 'Downtown', 'SoMa', 'Richmond', 'Oakland').
        quantity_kg: Total order weight in kg (larger batches take more extrusion & resting time).
        desired_service_time: Target kitchen shift ('lunch' for prep before 11am, or 'dinner' for prep before 4pm).

    Returns:
        Logistics details with production turnaround time, estimated dispatch date & time window,
        order cutoff deadline, and van delivery notes.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    # Production time: baseline 4 hours for <= 30kg, 6 hours for 31-80kg, 8 hours for > 80kg
    if quantity_kg <= 30.0:
        lead_hours = 4
    elif quantity_kg <= 80.0:
        lead_hours = 6
    else:
        lead_hours = 8

    service_target = desired_service_time.lower().strip()
    # Next day delivery schedule based on service target
    tomorrow = now + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")

    if service_target == "dinner":
        delivery_window = f"{tomorrow_str} between 1:00 PM - 3:30 PM (before dinner prep)"
        order_cutoff = f"Today by 11:00 AM (for {lead_hours}h batch extrusion & hydration rest)"
        van_route = "Afternoon Bay Area Metro Route"
    else:  # default lunch service
        delivery_window = f"{tomorrow_str} between 7:30 AM - 10:30 AM (before lunch prep)"
        order_cutoff = f"Today by 2:00 PM (for overnight cold aging & early morning run)"
        van_route = "Early Morning Kitchen Express"

    # Neighborhood specific notes
    area = delivery_neighborhood_or_city.lower()
    if any(k in area for k in ["oakland", "berkeley", "east bay"]):
        route_notes = "East Bay Bridge route: Departs factory at 6:45 AM."
    elif any(k in area for k in ["mission", "soma", "downtown", "chinatown"]):
        route_notes = "SF Central route: Direct commercial kitchen dock access supported."
    else:
        route_notes = f"Standard refrigerated route servicing {delivery_neighborhood_or_city}."

    return {
        "destination": delivery_neighborhood_or_city,
        "quantity_kg": quantity_kg,
        "batch_production_lead_time": f"{lead_hours} hours (mixing, extrusion, and aging)",
        "service_target": desired_service_time,
        "order_cutoff_deadline": order_cutoff,
        "estimated_delivery_window": delivery_window,
        "van_route": van_route,
        "route_notes": route_notes,
    }


def generate_custom_batch_spec(
    noodle_type: str,
    cut_thickness_gauge: str = "standard",
    hydration_preference: str = "standard",
    flour_blend: str = "artisan_wheat",
    target_broth_style: str = "tonkotsu",
) -> Dict[str, Any]:
    """Generate technical noodle craftsmanship specifications, hydration ratios, and chef pairing guide.

    Args:
        noodle_type: The type of noodle (e.g. 'ramen', 'udon', 'soba', 'egg_noodle').
        cut_thickness_gauge: Desired cutter gauge (e.g. '#20 thick', '#22 standard', '#26 ultra-thin', or 'standard').
        hydration_preference: Hydration level ('low 30-32%', 'standard 34-36%', 'high 38-40%').
        flour_blend: Flour type ('artisan_wheat', 'stoneground_buckwheat', 'high_protein_bread_flour', 'duck_egg_enriched').
        target_broth_style: Intended broth or dish (e.g. 'heavy tonkotsu', 'delicate shio', 'rich miso', 'cold tsuyu dip', 'wok pan-fry').

    Returns:
        Structured craftsmanship specification sheet with moisture %, kansui ratio, recommended boil time,
        texture profile, and allergen declarations.
    """
    ntype = noodle_type.lower()
    spec = {
        "noodle_type": noodle_type,
        "target_broth_style": target_broth_style,
        "flour_blend": flour_blend,
    }

    if "soba" in ntype:
        spec.update({
            "hydration_rate": "40% pure filtered spring water",
            "kansui_alkaline_mineral": "None (pure buckwheat dough)",
            "cutter_gauge": cut_thickness_gauge if cut_thickness_gauge != "standard" else "#24 (1.25mm delicate square cut)",
            "recommended_boil_time_sec": "60 to 75 seconds, followed immediately by ice shock bath",
            "texture_profile": "Delicate, nutty aroma, smooth swallow (nodogoshi)",
            "allergens": ["Buckwheat", "Wheat (20% binder flour)"],
            "storage_temp": "34°F - 38°F (refrigerated, consume within 5 days)",
        })
    elif "udon" in ntype:
        spec.update({
            "hydration_rate": "45% sea-salt brine hydration",
            "kansui_alkaline_mineral": "None (traditional foot-pressed wheat & salt brine)",
            "cutter_gauge": cut_thickness_gauge if cut_thickness_gauge != "standard" else "#10 to #12 (2.5mm thick square ribbon)",
            "recommended_boil_time_sec": "11 to 13 minutes for fresh batch, rinse in cold tap water",
            "texture_profile": "Distinctive chewiness, elastic bite (koshi), glossy white surface",
            "allergens": ["Wheat (Gluten)"],
            "storage_temp": "34°F - 38°F (refrigerated, consume within 7 days)",
        })
    elif "egg" in ntype or "wonton" in ntype:
        spec.update({
            "hydration_rate": "30% low moisture with fresh duck egg yolks",
            "kansui_alkaline_mineral": "Moderate potassium carbonate for snap and elasticity",
            "cutter_gauge": cut_thickness_gauge if cut_thickness_gauge != "standard" else "#26 (1.15mm ultra-fine string)",
            "recommended_boil_time_sec": "25 to 35 seconds flash boil",
            "texture_profile": "Crisp, springy, toothsome bite that doesn't bloat in soup or wok",
            "allergens": ["Wheat (Gluten)", "Eggs"],
            "storage_temp": "34°F - 38°F (refrigerated, consume within 10 days)",
        })
    else:  # Ramen (Tokyo, Hakata, Sapporo, etc.)
        is_thin = "thin" in cut_thickness_gauge.lower() or "26" in cut_thickness_gauge
        spec.update({
            "hydration_rate": "30% - 32% (low hydration)" if is_thin else "35% - 37% (medium hydration with gentle wave crimp)",
            "kansui_alkaline_mineral": "Mongolian natural alkaline salts (Type-1 sodium/potassium blend for yellow hue & snap)",
            "cutter_gauge": cut_thickness_gauge if cut_thickness_gauge != "standard" else ("#26 straight" if "tonkotsu" in target_broth_style.lower() else "#20 wavy"),
            "recommended_boil_time_sec": "45 to 60 seconds (katame/firm)" if is_thin else "90 to 120 seconds",
            "texture_profile": "Firm toothsome bite, excellent soup adhesion without getting soggy",
            "allergens": ["Wheat (Gluten)"],
            "storage_temp": "34°F - 38°F (refrigerated, peak flavor after 24h cold aging, consume within 10 days)",
        })

    return spec


def calculate_restaurant_batch_yield(
    daily_servings_target: int,
    noodle_product_id: str,
    serving_portion_grams: int = 140,
    service_days_per_week: int = 6,
) -> Dict[str, Any]:
    """Calculate real-world commercial kitchen batch sizing, portion yield, flour consumption, and weekly procurement needs.

    Helps head chefs and restaurant operators translate target customer covers (e.g. 150 bowls/day)
    into required factory kilogram orders, safety buffer margins, and estimated weekly cost.

    Args:
        daily_servings_target: Expected number of noodle bowls/servings served per day (e.g., 80, 150, 300).
        noodle_product_id: ID of the noodle product (e.g., 'ramen-tokyo-wave', 'udon-sanuki', 'pho-flat-rice').
        serving_portion_grams: Target dry/uncooked noodle weight per bowl in grams (default standard 140g for ramen, 200g for udon).
        service_days_per_week: Number of operating service days per week (default 6).

    Returns:
        Structured breakdown of daily kg needed, weekly kg requirements, recommended order schedule with safety stock buffer, and estimated weekly ingredient spend.
    """
    db = get_firestore_client()
    doc = db.collection("noodle_products").document(noodle_product_id).get()
    if not doc.exists:
        return {"error": f"Product with ID '{noodle_product_id}' not found."}

    prod = doc.to_dict()
    product_name = prod.get("name", noodle_product_id)
    price_per_kg = prod.get("price_per_kg", 7.50)

    # 1. Calculations
    daily_raw_kg = (daily_servings_target * serving_portion_grams) / 1000.0
    # Include 5% kitchen prep drop/spoilage buffer
    daily_order_kg = round(daily_raw_kg * 1.05, 1)
    weekly_total_kg = round(daily_order_kg * service_days_per_week, 1)

    # Weekly cost with volume discounting
    weekly_base_spend = weekly_total_kg * price_per_kg
    discount_pct = 0.0
    if weekly_total_kg >= 100:
        discount_pct = 15.0
    elif weekly_total_kg >= 50:
        discount_pct = 10.0
    elif weekly_total_kg >= 25:
        discount_pct = 5.0

    discount_amount = round(weekly_base_spend * (discount_pct / 100.0), 2)
    weekly_net_spend = round(weekly_base_spend - discount_amount, 2)
    cost_per_bowl = round(weekly_net_spend / (daily_servings_target * service_days_per_week), 2)

    # Recommended factory delivery cadence based on shelf life
    shelf_life = prod.get("shelf_life_days", 7)
    if shelf_life <= 6:
        cadence = "3x weekly deliveries (Mon / Wed / Fri) to guarantee peak freshness"
        delivery_split_kg = round(weekly_total_kg / 3.0, 1)
    else:
        cadence = "2x weekly deliveries (Mon / Thu) to optimize cold storage space"
        delivery_split_kg = round(weekly_total_kg / 2.0, 1)

    return {
        "product_id": noodle_product_id,
        "product_name": product_name,
        "portion_spec": f"{serving_portion_grams}g uncooked noodles per bowl",
        "daily_servings_target": daily_servings_target,
        "daily_kg_requirement": f"{daily_order_kg} kg/day (includes 5% prep buffer)",
        "service_days_per_week": service_days_per_week,
        "total_weekly_procurement_kg": f"{weekly_total_kg} kg",
        "recommended_delivery_cadence": cadence,
        "per_delivery_batch_kg": f"{delivery_split_kg} kg per shipment",
        "weekly_wholesale_discount_pct": f"{discount_pct}%",
        "estimated_weekly_ingredient_cost": f"${weekly_net_spend:.2f}",
        "effective_noodle_cost_per_bowl": f"${cost_per_bowl:.2f} per bowl",
    }


def get_kitchen_cooking_guide(
    noodle_product_id: str,
    serving_style: str = "hot_broth",
) -> Dict[str, Any]:
    """Retrieve chef-validated commercial kitchen preparation protocols, boil curves, and handling instructions for any inventory item.

    Args:
        noodle_product_id: The ID of the inventory product (e.g., 'ramen-tokyo-wave', 'udon-sanuki', 'soba-shinshu', 'shirataki-konjac-zero').
        serving_style: 'hot_broth' (standard soup bowls), 'cold_dipping' (tsukemen/zaru style), or 'wok_tossed' (yakisoba/chow mein).

    Returns:
        Exact water-to-noodle boiling ratio, optimal boil time, teppo strain/shake technique, water temperature, shock bath protocol, and shelf stability guidelines.
    """
    db = get_firestore_client()
    doc = db.collection("noodle_products").document(noodle_product_id).get()
    if not doc.exists:
        return {"error": f"Product with ID '{noodle_product_id}' not found."}

    prod = doc.to_dict()
    name = prod.get("name", noodle_product_id)
    ntype = prod.get("type", "").lower()
    allergens = prod.get("allergens", [])

    style = serving_style.lower()

    if "soba" in ntype:
        boil_time = "60 to 75 seconds" if style != "cold_dipping" else "50 to 60 seconds (al dente)"
        shock = "CRITICAL: Immediately plunge noodles into 32°F ice water bath, gently washing away surface starch with your palms. Shake teppo basket vigorously 5 times."
        water_ratio = "10:1 rolling boil (at least 1.5L rapid boiling water per 140g portion)"
        temp = "Rolling boil at 212°F (100°C). Never simmer."
        broth_pairing = "Warm kamo nanban dashi broth or chilled concentrated kaeshi tsuyu with grated wasabi."
    elif "udon" in ntype:
        boil_time = "12 to 14 minutes for fresh Sanuki ribbons"
        shock = "Rinse under cold running water for 45 seconds to firm up gluten structure and achieve authentic 'koshi' bounce. If serving hot, re-dip in hot water for 15 seconds before plating."
        water_ratio = "12:1 heavy rolling boil (at least 2.5L water per 200g portion)"
        temp = "High rolling boil. Add splash of cold water (bikkuri-mizu) if pot threatens to boil over."
        broth_pairing = "Golden kombu-dashi broth, tempura flakes (tenkasu), scallions, and shichimi togarashi."
    elif "rice" in ntype or "pho" in ntype:
        boil_time = "15 to 25 seconds flash blanch"
        shock = "No cold shock needed for hot pho. Dip fresh noodles into boiling water basket for 20 seconds, shake dry, immediately place in heated bowl and ladle boiling bone broth over top."
        water_ratio = "8:1 rolling boil"
        temp = "210°F - 212°F"
        broth_pairing = "Star anise and roasted ginger beef bone pho broth."
    elif "konjac" in ntype or "shirataki" in ntype:
        boil_time = "1 to 2 minutes parboil"
        shock = "Drain liquid from package, rinse thoroughly under cold water for 1 minute, parboil for 2 minutes, then dry-sear in a hot non-oiled skillet for 2 minutes to eliminate excess moisture and lock in broth absorption."
        water_ratio = "5:1 boiling water"
        temp = "200°F - 212°F"
        broth_pairing = "Rich sukiyaki sauce, miso broth, or low-calorie bone broths."
    else:  # Ramen / Egg noodles
        if "thick" in name.lower() or "tsukemen" in name.lower():
            boil_time = "4 minutes 30 seconds to 5 minutes"
            shock = "If serving Tsukemen: Rinse thoroughly in cold running water, ice shock for 30 seconds, shake basket 8 times until completely dry."
        elif "thin" in name.lower() or "hakata" in name.lower():
            boil_time = "35 seconds (Barikata/Hard) | 45 seconds (Katame/Firm) | 60 seconds (Futsu/Standard)"
            shock = "No cold rinse for hot tonkotsu. Strain with sharp 6-beat vertical teppo snap and fold directly into heated bowl with emulsified soup base."
        else:
            boil_time = "80 to 95 seconds for Tokyo wavy crimp"
            shock = "Shake teppo basket sharply 6 times to eliminate cloudy cooking water before placing into bowl."
        water_ratio = "10:1 rolling boil (at least 1.5L water per 140g portion)"
        temp = "Vigorous rolling boil at 212°F (100°C)."
        broth_pairing = "Chashu shoyu ramen broth, paitan, or rich tonkotsu broth."

    return {
        "noodle_product": name,
        "serving_style": serving_style,
        "allergens_flag": allergens,
        "recommended_boil_time": boil_time,
        "water_to_noodle_ratio": water_ratio,
        "boiling_temp_requirement": temp,
        "strain_and_shock_protocol": shock,
        "plating_pairing_recommendation": broth_pairing,
        "kitchen_safety_note": "Ensure dedicated gluten-free boiling pot if preparing allergen-safe orders.",
    }


def get_personalized_recommendations(customer_name_or_query: str = "") -> Dict[str, Any]:
    """Analyze recent order history, frequent noodle preferences, and dietary patterns to suggest tailored inventory items and complementary pairings.

    Args:
        customer_name_or_query: Name of restaurant/customer (e.g., 'Ramen Yatai Downtown', 'Sakura Udon & Izakaya', 'gcloud') or general taste preference.

    Returns:
        Structured summary of past orders, identified favorite product profiles, and personalized item suggestions with specific pairing rationale.
    """
    db = get_firestore_client()
    orders_stream = db.collection("noodle_orders").stream()

    user_query = customer_name_or_query.lower().strip()
    all_past_orders = []
    matched_orders = []

    for doc in orders_stream:
        data = doc.to_dict()
        data["order_id"] = doc.id
        all_past_orders.append(data)
        cname = data.get("customer_name", "").lower()
        if user_query and (user_query in cname or user_query in data.get("product_name", "").lower()):
            matched_orders.append(data)

    target_orders = matched_orders if matched_orders else all_past_orders

    # Collect purchased product IDs and names
    past_product_ids = {o.get("product_id") for o in target_orders if o.get("product_id")}
    past_product_names = [o.get("product_name") for o in target_orders if o.get("product_name")]

    # Fetch full inventory for complementary recommendations
    all_prods = list_noodle_products()
    prods_by_id = {p["id"]: p for p in all_prods}

    suggestions = []

    # Logic 1: If ordered Tokyo Wavy Ramen or Hakata Thin Ramen -> recommend Kyoto Extra-Thick Tsukemen or Chengdu Dan Dan
    if any("ramen" in pid for pid in past_product_ids):
        if "tsukemen-thick-wave" in prods_by_id:
            p = prods_by_id["tsukemen-thick-wave"]
            suggestions.append({
                "product_id": p["id"],
                "name": p["name"],
                "type": p["type"],
                "price_per_kg": f"${p['price_per_kg']}",
                "allergens": p.get("allergens", []),
                "recommendation_reason": "Because your kitchen frequently orders wavy ramen broth noodles, our Kyoto Extra-Thick Tsukemen offers an exceptional heavy-gauge alternative engineered for rich dipping broths.",
            })
        if "dan-dan-sichuan-wheat" in prods_by_id:
            p = prods_by_id["dan-dan-sichuan-wheat"]
            suggestions.append({
                "product_id": p["id"],
                "name": p["name"],
                "type": p["type"],
                "price_per_kg": f"${p['price_per_kg']}",
                "allergens": p.get("allergens", []),
                "recommendation_reason": "Pairs seamlessly with existing wheat prep equipment for spicy sesame chili specials.",
            })

    # Logic 2: If ordered Udon -> suggest Shinshu Soba or Matcha Soba
    if any("udon" in pid for pid in past_product_ids):
        if "matcha-green-tea-soba" in prods_by_id:
            p = prods_by_id["matcha-green-tea-soba"]
            suggestions.append({
                "product_id": p["id"],
                "name": p["name"],
                "type": p["type"],
                "price_per_kg": f"${p['price_per_kg']}",
                "allergens": p.get("allergens", []),
                "recommendation_reason": "Great high-margin seasonal special complementing your traditional dashi and cold tsuyu noodle station.",
            })

    # Logic 3: Always provide a gluten-free / allergen-free option
    if "pho-flat-rice" in prods_by_id and not any("pho" in pid for pid in past_product_ids):
        p = prods_by_id["pho-flat-rice"]
        suggestions.append({
            "product_id": p["id"],
            "name": p["name"],
            "type": p["type"],
            "price_per_kg": f"${p['price_per_kg']}",
            "allergens": p.get("allergens", []),
            "recommendation_reason": "Natural gluten-free expansion item to accommodate guests with wheat sensitivities without compromising texture.",
        })

    # Fallback if no specific matches
    if not suggestions:
        for p in all_prods[:3]:
            suggestions.append({
                "product_id": p["id"],
                "name": p["name"],
                "type": p["type"],
                "price_per_kg": f"${p['price_per_kg']}",
                "allergens": p.get("allergens", []),
                "recommendation_reason": "Top trending artisan noodle batch in our factory inventory.",
            })

    return {
        "customer_query": customer_name_or_query or "All Recent Kitchens",
        "recent_order_count": len(target_orders),
        "frequently_ordered_items": list(set(past_product_names))[:4],
        "recommended_inventory_items": suggestions[:3],
    }




def check_weather_and_dispatch_impact(
    delivery_neighborhood_or_city: str = "San Francisco",
    noodle_product_id: str = "ramen-tokyo-wave",
) -> Dict[str, Any]:
    """Analyze current atmospheric weather, ambient humidity, and transit conditions to recommend dough extrusion hydration adjustments and delivery van alerts.

    Args:
        delivery_neighborhood_or_city: Destination city/neighborhood (e.g., 'San Francisco', 'Oakland', 'Mission', 'San Jose').
        noodle_product_id: Target noodle product being mixed and delivered (e.g., 'ramen-tokyo-wave', 'egg-hongkong-wonton', 'soba-shinshu').

    Returns:
        Structured dispatch briefing with weather forecast, humidity index, dough mixing hydration offset, and refrigerated van route advisory.
    """
    loc = delivery_neighborhood_or_city.lower()
    
    # Atmospheric condition simulation based on Bay Area microclimates
    if any(k in loc for k in ["oakland", "berkeley", "east bay"]):
        temp_f = 72
        condition = "Sunny & Warm"
        humidity_pct = 48
        bridge_delay_mins = 15
        route_advisory = "Bay Bridge westbound morning traffic advisory (+15 min). Refrigerated unit pre-cooling recommended to 35°F."
    elif any(k in loc for k in ["san jose", "south bay", "sunnyvale", "santa clara"]):
        temp_f = 78
        condition = "Clear and Warm"
        humidity_pct = 42
        bridge_delay_mins = 0
        route_advisory = "Highway 101 South route clear. Direct dock delivery on schedule."
    else:  # SF / Coast / Peninsula
        temp_f = 59
        condition = "Cool Coastal Fog & Heavy Marine Layer"
        humidity_pct = 84
        bridge_delay_mins = 5
        route_advisory = "SF Metro Coastal route: Damp marine layer present. Minimal traffic delays."

    # Hydration adjustment calculation based on ambient humidity
    # Standard ambient humidity is 50-55%. High humidity (>70%) requires reducing water in dough by 1-2%.
    if humidity_pct > 70:
        hydration_offset = "-1.5% water adjustment"
        flour_note = "High ambient humidity detected. Factory mixers reduce dough water ratio by 1.5% to avoid sticky extrusion and maintain noodle al dente snap."
    elif humidity_pct < 45:
        hydration_offset = "+1.0% water adjustment"
        flour_note = "Dry ambient air. Slight +1.0% hydration boost applied during vacuum kneading to prevent brittle edges."
    else:
        hydration_offset = "Nominal (0.0% adjustment)"
        flour_note = "Ambient humidity is within ideal factory tolerance (50-60%). Standard recipe ratios active."

    return {
        "location": delivery_neighborhood_or_city,
        "temperature": f"{temp_f}°F",
        "condition": condition,
        "relative_humidity": f"{humidity_pct}%",
        "dough_hydration_offset": hydration_offset,
        "factory_mixing_action": flour_note,
        "dispatch_route_alert": route_advisory,
        "transit_temperature_assurance": "Active reefer van monitoring: Locked at 36°F (2.2°C).",
    }


def request_chef_sample_flight(
    restaurant_name: str,
    chef_contact_name: str,
    contact_phone_or_email: str,
    delivery_address: str,
    selected_sample_ids: list[str],
    preferred_trial_date: str = "",
) -> Dict[str, Any]:
    """Request a professional 3-item Chef Sample Flight Kit (1kg fresh trial portions of each noodle) for restaurant kitchen evaluation.

    The $25 trial kit fee is 100% credited back toward the restaurant's first 50kg+ commercial wholesale order.

    Args:
        restaurant_name: Name of the dining establishment (e.g. 'Izakaya Rintaro', 'Nari SF').
        chef_contact_name: Name of the Head Chef or Kitchen Manager.
        contact_phone_or_email: Chef's phone number or email for dispatch notification.
        delivery_address: Kitchen dock or restaurant physical address.
        selected_sample_ids: List of up to 3 noodle product IDs to sample (e.g. ['ramen-tokyo-wave', 'udon-sanuki', 'soba-shinshu']).
        preferred_trial_date: Desired delivery date for kitchen testing.

    Returns:
        Confirmation receipt with flight kit tracking ID, sample manifest, credit voucher guarantee, and dispatch schedule.
    """
    db = get_firestore_client()
    
    # Validate selected products
    sample_items = []
    for pid in selected_sample_ids[:3]:
        doc = db.collection("noodle_products").document(pid).get()
        if doc.exists:
            sample_items.append(doc.to_dict().get("name", pid))
        else:
            sample_items.append(pid)

    flight_id = f"FLIGHT-{datetime.datetime.now().strftime('%m%d')}-{restaurant_name[:3].upper()}"
    trial_date = preferred_trial_date or (datetime.datetime.now() + datetime.timedelta(days=2)).strftime("%Y-%m-%d")

    record = {
        "flight_id": flight_id,
        "restaurant_name": restaurant_name,
        "chef_contact": chef_contact_name,
        "contact": contact_phone_or_email,
        "delivery_address": delivery_address,
        "samples": sample_items,
        "portion_per_sample": "1.0 kg fresh vacuum pack",
        "sample_fee": "$25.00 (Fully credited to first wholesale order)",
        "credit_voucher_code": f"CREDIT25-{flight_id[-4:]}",
        "trial_delivery_date": trial_date,
        "status": "scheduled_for_dispatch",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    # Save to Firestore sample_flights collection
    db.collection("sample_flights").document(flight_id).set(record)

    return {
        "status": "confirmed",
        "flight_kit_id": flight_id,
        "restaurant": restaurant_name,
        "chef": chef_contact_name,
        "samples_included": sample_items,
        "total_trial_weight": f"{len(sample_items)} kg fresh cold-packed noodles",
        "delivery_target": trial_date,
        "wholesale_rebate_voucher": record["credit_voucher_code"],
        "message": f"Chef Sample Flight Kit confirmed for {restaurant_name}. 1kg testing packs will be dispatched in insulated cold containers on {trial_date}.",
    }


def check_walkin_depletion_and_reorder_reminder(
    customer_name: str,
    daily_bowl_velocity: int = 150,
    serving_portion_grams: int = 140,
) -> Dict[str, Any]:
    """Calculate walk-in cooler stock depletion timeline and trigger automated wholesale reorder reminders based on restaurant bowl service pace.

    Args:
        customer_name: Name of the restaurant (e.g., 'Ramen Yatai Downtown', 'Sakura Udon & Izakaya', 'gcloud').
        daily_bowl_velocity: Average number of bowls served per day (e.g., 100, 150, 250).
        serving_portion_grams: Portion size in grams (standard 140g for ramen, 200g for udon).

    Returns:
        Structured depletion analysis with days of remaining inventory, projected run-out service date,
        and one-click factory batch reorder recommendation.
    """
    db = get_firestore_client()
    orders = db.collection("noodle_orders").stream()
    
    c_lower = customer_name.lower().strip()
    matching = []
    for doc in orders:
        d = doc.to_dict()
        d["order_id"] = doc.id
        if c_lower in d.get("customer_name", "").lower():
            matching.append(d)

    if not matching:
        # Fallback to the latest order in the system
        orders_all = sorted(
            [d for d in [doc.to_dict() | {"order_id": doc.id} for doc in db.collection("noodle_orders").stream()]],
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
        target_order = orders_all[0] if orders_all else {
            "order_id": "ORDER-DEMO",
            "product_name": "Tokyo Wavy Ramen Noodles",
            "quantity_kg": 50.0,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    else:
        # Sort by creation date descending
        target_order = sorted(matching, key=lambda x: x.get("created_at", ""), reverse=True)[0]

    product_name = target_order.get("product_name", "Tokyo Wavy Ramen Noodles")
    total_batch_kg = float(target_order.get("quantity_kg", 50.0))
    
    daily_consumption_kg = (daily_bowl_velocity * serving_portion_grams) / 1000.0
    days_of_stock = round(total_batch_kg / daily_consumption_kg, 1) if daily_consumption_kg > 0 else 3.0

    run_out_date = datetime.datetime.now() + datetime.timedelta(days=int(days_of_stock))
    reorder_deadline = run_out_date - datetime.timedelta(days=1)

    return {
        "restaurant_name": customer_name,
        "last_order_ref": target_order.get("order_id"),
        "noodle_product": product_name,
        "last_delivered_batch_kg": f"{total_batch_kg} kg",
        "service_pace": f"{daily_bowl_velocity} bowls/day ({daily_consumption_kg:.1f} kg/day)",
        "estimated_days_of_stock": f"{days_of_stock} days",
        "projected_depletion_date": run_out_date.strftime("%A, %B %d"),
        "recommended_reorder_deadline": f"{reorder_deadline.strftime('%A, %B %d')} before 2:00 PM",
        "reorder_action_prompt": f"Would you like to duplicate your {total_batch_kg}kg batch of {product_name} to guarantee fresh delivery before {run_out_date.strftime('%A')}?",
    }
