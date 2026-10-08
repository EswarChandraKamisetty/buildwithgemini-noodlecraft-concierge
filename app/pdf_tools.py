"""PDF generation tool for NoodleCraft Concierge spec sheets and wholesale invoices."""

import io
import datetime
from typing import Any, Dict
from google.cloud import storage
from google.adk.tools import ToolContext

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from app.firestore_tools import get_firestore_client, list_noodle_products

PROJECT_ID = "qwiklabs-gcp-04-9f640202d071"
BUCKET_NAME = "qwiklabs-gcp-04-9f640202d071-noodlecraft-media"

_storage_client = None


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


def build_spec_sheet_pdf(
    product_name: str,
    noodle_type: str,
    price_per_kg: float,
    shelf_life_days: int,
    ingredients: list,
    allergens: list,
    description: str,
    cut_gauge: str = "#22 Standard (1.5mm)",
    hydration: str = "35% - 37%",
    boil_time: str = "90 - 120 seconds",
) -> bytes:
    """Build a professional branded PDF spec sheet bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#d9480f'),
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555'),
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2d241e'),
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#222222'),
    )
    allergen_box_style = ParagraphStyle(
        'AllergenText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#c92a2a'),
    )

    story = []

    # Header
    header_data = [
        [
            Paragraph("🍜 <b>NOODLECRAFT ARTISAN FACTORY</b><br/><font size='8' color='#79685a'>COMMERCIAL SPECIFICATION SHEET & CHEF GUIDE</font>", title_style),
            Paragraph(f"<b>Date:</b> {datetime.datetime.now().strftime('%B %d, %Y')}<br/><b>Doc Ref:</b> SPEC-{product_name[:4].upper()}-2026", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[380, 160])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#d9480f'), spaceAfter=12))

    # Product Overview Table
    story.append(Paragraph("1. PRODUCT IDENTIFICATION", section_style))
    story.append(Spacer(1, 4))
    prod_data = [
        [Paragraph("<b>Product Name</b>", body_style), Paragraph(product_name, body_style)],
        [Paragraph("<b>Category / Type</b>", body_style), Paragraph(noodle_type, body_style)],
        [Paragraph("<b>Wholesale Base Price</b>", body_style), Paragraph(f"${price_per_kg:.2f} / kg", body_style)],
        [Paragraph("<b>Cold Shelf Stability</b>", body_style), Paragraph(f"{shelf_life_days} Days (Keep chilled at 34°F - 38°F / 1°C - 3°C)", body_style)],
        [Paragraph("<b>Sensory Profile</b>", body_style), Paragraph(description, body_style)],
    ]
    prod_table = Table(prod_data, colWidths=[150, 390])
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#fff4e6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#eadfcd')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(prod_table)
    story.append(Spacer(1, 12))

    # Technical Specs
    story.append(Paragraph("2. TECHNICAL CRAFTSMANSHIP & COOKING CURVE", section_style))
    story.append(Spacer(1, 4))
    spec_data = [
        [Paragraph("<b>Cutter Gauge / Cut</b>", body_style), Paragraph(cut_gauge, body_style)],
        [Paragraph("<b>Flour Hydration Rate</b>", body_style), Paragraph(hydration, body_style)],
        [Paragraph("<b>Recommended Boil Window</b>", body_style), Paragraph(boil_time, body_style)],
        [Paragraph("<b>Water-to-Noodle Ratio</b>", body_style), Paragraph("10:1 Rolling Boil (minimum 1.5L rapid boiling water per 140g basket)", body_style)],
        [Paragraph("<b>Strain Protocol</b>", body_style), Paragraph("Vigorous 6-beat vertical snap with teppo basket to shed excess water", body_style)],
    ]
    spec_table = Table(spec_data, colWidths=[150, 390])
    spec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8f9fa')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(spec_table)
    story.append(Spacer(1, 12))

    # Ingredients & Allergen Declaration
    story.append(Paragraph("3. INGREDIENTS & ALLERGEN DECLARATION", section_style))
    story.append(Spacer(1, 4))
    ing_text = ", ".join(ingredients) if ingredients else "Standard milled flour blend, filtered water, sea salt."
    allg_text = ", ".join(allergens) if allergens else "None / Allergen-Free"
    
    allg_data = [
        [Paragraph("<b>Full Ingredients</b>", body_style), Paragraph(ing_text, body_style)],
        [Paragraph("<b>ALLERGEN ADVISORY</b>", allergen_box_style), Paragraph(f"<b>CONTAINS: {allg_text.upper()}</b>", allergen_box_style)],
    ]
    allg_table = Table(allg_data, colWidths=[150, 390])
    allg_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#fff5f5')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#ffc9c9')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(allg_table)
    story.append(Spacer(1, 14))

    # Footer note
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=6))
    story.append(Paragraph("<font size='7' color='#888888'>NoodleCraft Commercial Kitchen Supply • Certified Food Facility • Contact: orders@noodlecraft.internal • Keep refrigerated at all times</font>", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def build_invoice_pdf(
    order_id: str,
    customer_name: str,
    product_name: str,
    quantity_kg: float,
    price_per_kg: float,
    total_price: float,
    delivery_address: str,
    delivery_date: str,
    special_notes: str = "",
) -> bytes:
    """Build a formal commercial wholesale order invoice PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#2d241e'),
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555'),
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#222222'),
    )
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#222222'),
    )

    story = []

    # Header
    header_data = [
        [
            Paragraph("🍜 <b>NOODLECRAFT FACTORY</b><br/><font size='9' color='#d9480f'>WHOLESALE COMMERCIAL INVOICE</font>", title_style),
            Paragraph(f"<b>Invoice #:</b> {order_id}<br/><b>Date:</b> {datetime.datetime.now().strftime('%Y-%m-%d')}<br/><b>Status:</b> CONFIRMED", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[350, 190])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#d9480f'), spaceAfter=12))

    # Customer & Logistics
    info_data = [
        [
            Paragraph(f"<b>Billed & Shipped To:</b><br/><b>{customer_name}</b><br/>{delivery_address}", body_style),
            Paragraph(f"<b>Delivery Target Date:</b> {delivery_date}<br/><b>Transport:</b> Direct Refrigerated Delivery<br/><b>Special Instructions:</b> {special_notes or 'Standard prep packaging'}", body_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fbf9f6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#eadfcd')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    # Line Item Table
    items_header = [
        Paragraph("<b>Item Description</b>", body_bold),
        Paragraph("<b>Qty (kg)</b>", body_bold),
        Paragraph("<b>Rate/kg</b>", body_bold),
        Paragraph("<b>Amount</b>", body_bold),
    ]
    items_row = [
        Paragraph(f"<b>{product_name}</b><br/><font size='7' color='#777777'>Fresh cold-aged restaurant wholesale batch</font>", body_style),
        Paragraph(f"{quantity_kg:.1f} kg", body_style),
        Paragraph(f"${price_per_kg:.2f}", body_style),
        Paragraph(f"${total_price:.2f}", body_bold),
    ]
    total_row = [
        Paragraph("<b>TOTAL DUE:</b>", body_bold),
        Paragraph("", body_style),
        Paragraph("", body_style),
        Paragraph(f"<b>${total_price:.2f} USD</b>", ParagraphStyle('TotalLarge', parent=body_bold, fontSize=11, textColor=colors.HexColor('#d9480f'))),
    ]
    items_table = Table([items_header, items_row, total_row], colWidths=[300, 70, 80, 90])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#fff4e6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#eadfcd')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('LINEBELOW', (0,1), (-1,1), 1, colors.HexColor('#d9480f')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#fbf9f6')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 25))

    # Terms & Signature Block
    story.append(Paragraph("<b>Payment Terms:</b> Net 15 for verified wholesale restaurant accounts. Thank you for your partnership!", body_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=6))
    story.append(Paragraph("<font size='7' color='#888888'>NoodleCraft Commercial Kitchen Supply • 452 Market St Industrial Dock, San Francisco, CA • accounting@noodlecraft.internal</font>", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


async def generate_product_spec_sheet_pdf(
    product_id: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a downloadable, publication-grade commercial PDF specification sheet for any inventory item.

    Includes full nutritional/ingredient profiles, allergen advisory callouts, hydration moisture rates,
    cut gauges, and chef boiling curves. Uploads to Cloud Storage and saves artifact for inspection.

    Args:
        product_id: The ID of the noodle product (e.g., 'ramen-tokyo-wave', 'udon-sanuki', 'soba-shinshu', 'pho-flat-rice').
        tool_context: ADK ToolContext to store the artifact for Playground view.

    Returns:
        Dictionary with the public downloadable PDF URL, filename, and product overview.
    """
    db = get_firestore_client()
    doc = db.collection("noodle_products").document(product_id).get()
    if not doc.exists:
        return {"error": f"Product with ID '{product_id}' not found."}

    data = doc.to_dict()
    name = data.get("name", product_id)
    ntype = data.get("type", "Artisan Noodle")
    price = data.get("price_per_kg", 7.50)
    shelf = data.get("shelf_life_days", 7)
    ingredients = data.get("ingredients", [])
    allergens = data.get("allergens", [])
    desc = data.get("description", "Premium artisan manufactured noodles.")

    # Determine specs
    cut_gauge = "#22 Standard Wavy (1.5mm)"
    hydration = "35% - 37%"
    boil_time = "90 - 120 seconds"
    if "udon" in ntype.lower():
        cut_gauge = "#10 Thick Sanuki Ribbon (2.5mm)"
        hydration = "45% Sea-Salt Brine"
        boil_time = "12 - 14 minutes"
    elif "soba" in ntype.lower():
        cut_gauge = "#24 Delicate Square (1.25mm)"
        hydration = "40% Spring Water"
        boil_time = "60 - 75 seconds"
    elif "egg" in ntype.lower():
        cut_gauge = "#26 Fine String (1.15mm)"
        hydration = "30% Duck Egg Yolk"
        boil_time = "25 - 35 seconds"
    elif "rice" in ntype.lower() or "pho" in ntype.lower():
        cut_gauge = "5mm Flat Ribbon (Bánh Phở)"
        hydration = "48% Fresh Steam"
        boil_time = "15 - 25 seconds"

    pdf_bytes = build_spec_sheet_pdf(
        product_name=name,
        noodle_type=ntype,
        price_per_kg=price,
        shelf_life_days=shelf,
        ingredients=ingredients,
        allergens=allergens,
        description=desc,
        cut_gauge=cut_gauge,
        hydration=hydration,
        boil_time=boil_time,
    )

    filename = f"spec_sheet_{product_id}.pdf"

    # 1. Save artifact to ToolContext
    try:
        tool_context.save_artifact(filename=filename, artifact=pdf_bytes)
    except Exception as e:
        print(f"Artifact save warning: {e}")

    # 2. Upload to public Cloud Storage bucket
    storage_client = get_storage_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"spec_sheets/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

    return {
        "status": "success",
        "product_id": product_id,
        "product_name": name,
        "pdf_download_url": public_url,
        "message": f"Generated official commercial PDF specification sheet for {name}.",
    }


async def generate_wholesale_invoice_pdf(
    order_id: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate an official downloadable commercial PDF invoice for an existing confirmed wholesale order.

    Args:
        order_id: The unique ID of the order in noodle_orders (e.g., 'ORDER-1001', 'ORDER-1002').
        tool_context: ADK ToolContext to store the artifact for Playground view.

    Returns:
        Dictionary with the public downloadable PDF URL, invoice number, and order details.
    """
    db = get_firestore_client()
    doc = db.collection("noodle_orders").document(order_id).get()
    if not doc.exists:
        return {"error": f"Order with ID '{order_id}' not found."}

    order = doc.to_dict()
    customer_name = order.get("customer_name", "Valued Restaurant Client")
    product_name = order.get("product_name", "Artisan Noodles")
    quantity_kg = float(order.get("quantity_kg", 50.0))
    price_per_kg = float(order.get("price_per_kg", 7.50))
    total_price = float(order.get("total_price", quantity_kg * price_per_kg))
    delivery_address = order.get("delivery_address", "Local Dock Delivery")
    delivery_date = order.get("delivery_date", datetime.datetime.now().strftime("%Y-%m-%d"))
    special_notes = order.get("special_notes", "")

    pdf_bytes = build_invoice_pdf(
        order_id=order_id,
        customer_name=customer_name,
        product_name=product_name,
        quantity_kg=quantity_kg,
        price_per_kg=price_per_kg,
        total_price=total_price,
        delivery_address=delivery_address,
        delivery_date=delivery_date,
        special_notes=special_notes,
    )

    filename = f"invoice_{order_id}.pdf"

    # 1. Save artifact to ToolContext
    try:
        tool_context.save_artifact(filename=filename, artifact=pdf_bytes)
    except Exception as e:
        print(f"Artifact save warning: {e}")

    # 2. Upload to public Cloud Storage bucket
    storage_client = get_storage_client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob_name = f"invoices/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

    return {
        "status": "success",
        "order_id": order_id,
        "customer_name": customer_name,
        "total_amount": f"${total_price:.2f}",
        "pdf_download_url": public_url,
        "message": f"Generated official commercial PDF wholesale invoice for Order #{order_id}.",
    }
