# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types


MODEL = "gemini-3.8-flash"


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


from app.a2ui_utils import a2ui_callback
from app.firestore_tools import (
    calculate_quote_and_discounts,
    calculate_restaurant_batch_yield,
    check_walkin_depletion_and_reorder_reminder,
    check_weather_and_dispatch_impact,
    estimate_delivery_window,
    generate_custom_batch_spec,
    get_kitchen_cooking_guide,
    get_noodle_product,
    get_personalized_recommendations,
    list_noodle_products,
    place_noodle_order,
    request_chef_sample_flight,
    track_order,
)
from app.image_tools import generate_noodle_dish_image
from app.video_tools import generate_noodle_video
from app.pdf_tools import (
    generate_product_spec_sheet_pdf,
    generate_wholesale_invoice_pdf,
)

try:
    from app.a2ui_instruction import INSTRUCTION as instruction
except ImportError:
    from a2ui.schema.manager import A2uiSchemaManager
    from a2ui.basic_catalog.provider import BasicCatalog
    schema_manager = A2uiSchemaManager(
        version="0.8",
        catalogs=[BasicCatalog.get_config("0.8")],
    )
    instruction = schema_manager.generate_system_prompt(
        role_description=(
            "You are NoodleCraft Concierge, the AI ordering and customer support assistant "
            "for an artisan noodle manufacturing company. You help local restaurants and customers "
            "check current factory inventory levels, prices, batch availability, allergens, and ingredients, calculate bulk quotes and volume tier discounts, "
            "estimate kitchen delivery schedules and production lead times, consult on technical noodle craft specs "
            "(hydration, cutter gauges, boil times), calculate restaurant portion yield and weekly procurement needs, "
            "suggest items based on recent kitchen order activity and pairings, "
            "monitor walk-in stock depletion and trigger automated wholesale reorder reminders, "
            "provide chef-validated commercial kitchen cooking curves and handling protocols, "
            "generate downloadable commercial PDF specification sheets and wholesale invoices, "
            "evaluate local weather and humidity for dough hydration calibration and dispatch alerts, "
            "dispatch 3-item Chef Sample Flight Kits for restaurant evaluation, "
            "place new orders, track order deliveries, and generate appetizing "
            "dish visual concepts, packaging previews, or custom batch presentations using the image generation tool. "
            "Always use the available tools to fetch up-to-date product, pricing, specs, logistics information, "
            "and generate images or PDFs when requested."
        ),
        workflow_description="Analyze the request, call relevant tools, and return structured UI when appropriate.",
        ui_description=(
            "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
            "Never nest a Card inside a Card. "
            "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
            "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
            "nothing in adk web). "
            "You may include one Image component, but only when you have a public https "
            "URL for the image (for example the URL an image tool returns after uploading "
            "to a public bucket). Set the Image url to that exact https link, for example "
            '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
            "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
            "not have a public URL, add a short Text line noting the image instead. "
            "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
            "headings and emphasis. "
            "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
            "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
        ),
        include_schema=True,
        include_examples=True,
    )

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    after_model_callback=a2ui_callback,
    tools=[
        get_weather,
        get_current_time,
        list_noodle_products,
        get_noodle_product,
        calculate_quote_and_discounts,
        estimate_delivery_window,
        check_weather_and_dispatch_impact,
        generate_custom_batch_spec,
        calculate_restaurant_batch_yield,
        check_walkin_depletion_and_reorder_reminder,
        get_kitchen_cooking_guide,
        get_personalized_recommendations,
        request_chef_sample_flight,
        generate_product_spec_sheet_pdf,
        generate_wholesale_invoice_pdf,
        place_noodle_order,
        track_order,
        generate_noodle_dish_image,
        generate_noodle_video,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
