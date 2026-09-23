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

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .a2ui_utils import a2ui_callback


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


FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-415e839ac4f7"


def search_destinations(category: str = "", max_daily_cost_usd: float = 0.0) -> str:
    """Searches the Firestore destinations catalog for matching travel destinations.

    Args:
        category: Optional category filter (e.g. 'Culinary', 'Historical', 'Beach', 'Metropolitan').
        max_daily_cost_usd: Optional budget limit on average daily cost in USD (e.g. 150.0).

    Returns:
        A formatted string listing matching destinations with budget, description, and highlights.
    """
    from google.cloud import firestore

    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    docs = db.collection("destinations").stream()
    results = []

    for doc in docs:
        data = doc.to_dict()
        name = data.get("name", doc.id)
        doc_cat = data.get("category", "")
        cost = data.get("avg_daily_cost_usd", 0.0)

        if category and category.lower() not in doc_cat.lower():
            continue
        if max_daily_cost_usd > 0 and cost > max_daily_cost_usd:
            continue

        highlights_str = ", ".join(data.get("highlights", []))
        dietary_str = ", ".join(data.get("dietary_friendly", []))
        results.append(
            f"- {name} [{doc_cat} | Budget Tier: {data.get('budget_tier', 'N/A')}] "
            f"Avg Daily Cost: ${cost:.2f}/day. {data.get('description', '')} "
            f"Highlights: {highlights_str}. Dietary: {dietary_str}"
        )

    if not results:
        return f"No destinations found matching category='{category}' and max cost=${max_daily_cost_usd}."
    return "\n".join(results)


def add_destination(
    name: str,
    category: str,
    budget_tier: str,
    avg_daily_cost_usd: float,
    description: str,
    highlights: str,
) -> str:
    """Adds a new destination entry into the Firestore destinations catalog.

    Args:
        name: Name of the city/country (e.g. 'Barcelona, Spain').
        category: Category (e.g. 'Culinary', 'Historical', 'Beach', 'Metropolitan').
        budget_tier: Budget tier ('Budget', 'Moderate', 'Luxury').
        avg_daily_cost_usd: Estimated daily cost in USD (e.g. 140.0).
        description: Short overview of the destination.
        highlights: Comma-separated list of top attractions/spots (e.g. 'Sagrada Familia, Park Guell').

    Returns:
        Confirmation message with document ID.
    """
    from google.cloud import firestore

    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    doc_id = name.lower().replace(" ", "-").replace(",", "")
    doc_ref = db.collection("destinations").document(doc_id)

    highlights_list = [h.strip() for h in highlights.split(",") if h.strip()]
    data = {
        "name": name,
        "category": category,
        "budget_tier": budget_tier,
        "avg_daily_cost_usd": float(avg_daily_cost_usd),
        "description": description,
        "highlights": highlights_list,
        "dietary_friendly": ["Vegetarian Options"],
    }
    doc_ref.set(data)
    return f"Successfully added '{name}' to Firestore (doc_id: '{doc_id}')."


MEDIA_BUCKET_NAME = "smart-travel-concierge-media-415e839a"


def convert_currency(amount: float, from_currency: str = "USD", to_currency: str = "EUR") -> str:
    """Converts an amount from one currency to another using live exchange rates.

    Args:
        amount: Numeric amount to convert.
        from_currency: 3-letter source currency code (e.g. 'USD', 'EUR', 'GBP').
        to_currency: 3-letter target currency code (e.g. 'JPY', 'EUR', 'INR').

    Returns:
        Formatted conversion string with live rate information.
    """
    import json
    import urllib.request

    src = from_currency.upper().strip()
    tgt = to_currency.upper().strip()
    try:
        url = f"https://open.er-api.com/v6/latest/{src}"
        req = urllib.request.Request(url, headers={"User-Agent": "SmartTravelConcierge/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rates = data.get("rates", {})
            if tgt in rates:
                rate = float(rates[tgt])
                converted = amount * rate
                return f"{amount:.2f} {src} = {converted:.2f} {tgt} (exchange rate: 1 {src} = {rate:.4f} {tgt})"
            return f"Currency symbol '{tgt}' not found in exchange rate table."
    except Exception as exc:
        return f"Could not fetch live exchange rates: {exc}"


def publish_destination_teaser(destination_name: str, teaser_text: str) -> str:
    """Publishes a destination teaser/postcard to the public Cloud Storage bucket.

    Args:
        destination_name: Name of the destination (e.g. 'Tokyo').
        teaser_text: Short promotional teaser text or itinerary overview.

    Returns:
        The public HTTPS URL of the published teaser asset.
    """
    from google.cloud import storage

    client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = client.bucket(MEDIA_BUCKET_NAME)
    slug = destination_name.lower().replace(" ", "-").replace(",", "")
    blob_name = f"teasers/{slug}.txt"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(teaser_text, content_type="text/plain")
    public_url = f"https://storage.googleapis.com/{MEDIA_BUCKET_NAME}/{blob_name}"
    return f"Successfully published teaser for '{destination_name}'. Public URL: {public_url}"


def search_local_spots(location: str, query: str = "top attractions") -> str:
    """Searches for real local spots, dining options, or attractions in a given location.

    Args:
        location: City or region name (e.g. 'Tokyo', 'Paris').
        query: Search topic (e.g. 'vegetarian restaurants', 'museums', 'historical landmarks').

    Returns:
        Formatted summary of real places found.
    """
    import json
    import urllib.parse
    import urllib.request

    search_term = urllib.parse.quote(f"{query} {location}")
    url = f"https://nominatim.openstreetmap.org/search?q={search_term}&format=json&limit=3"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartTravelConciergeApp/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            places = json.loads(resp.read().decode("utf-8"))
            if not places:
                return f"No local spots found for '{query}' in {location}."
            results = []
            for p in places:
                display_name = p.get("display_name", "Unknown Place")
                place_type = p.get("type", "spot")
                results.append(f"- {display_name} (Category: {place_type})")
            return f"Found local spots for '{query}' in {location}:\n" + "\n".join(results)
    except Exception as exc:
        return f"Could not search local spots for {location}: {exc}"


def get_destination_public_holidays(country_code: str, year: int = 2026) -> str:
    """Fetches upcoming public holidays for a destination country from the Nager.Date Public API.

    Args:
        country_code: 2-letter ISO country code (e.g. 'JP' for Japan, 'FR' for France, 'IT' for Italy, 'ES' for Spain, 'US' for USA).
        year: Year for holiday schedule (defaults to 2026).

    Returns:
        Formatted list of public holidays with dates and local names.
    """
    import os
    import json
    import urllib.request

    cc = country_code.upper().strip()
    api_key = os.environ.get("HOLIDAY_API_KEY", os.environ.get("NAGER_API_KEY", ""))
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{cc}"

    headers = {"User-Agent": "SmartTravelConcierge/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            holidays = json.loads(resp.read().decode("utf-8"))
            if not holidays:
                return f"No public holidays found for country code '{cc}' in {year}."
            results = []
            for h in holidays[:10]:
                date_str = h.get("date", "")
                name = h.get("name", "")
                local_name = h.get("localName", "")
                results.append(f"- {date_str}: {name} ({local_name})")
            return f"Public holidays in {cc} for {year}:\n" + "\n".join(results)
    except Exception as exc:
        return f"Could not fetch public holidays for country '{cc}': {exc}"


def geocode_address(address: str) -> str:
    """Converts a location or street address into geographic coordinates (latitude, longitude) using Google Geocoding API.

    Args:
        address: Location query or address (e.g. 'Shibuya Crossing, Tokyo' or 'Eiffel Tower, Paris').

    Returns:
        Formatted summary with address, latitude, longitude, and place details.
    """
    import os
    import json
    import urllib.parse
    import urllib.request

    key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartTravelConcierge/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "OK" or not data.get("results"):
                return f"Geocoding failed for address '{address}': {data.get('status', 'ZERO_RESULTS')}"

            result = data["results"][0]
            formatted_addr = result.get("formatted_address", address)
            loc = result.get("geometry", {}).get("location", {})
            lat = loc.get("lat")
            lng = loc.get("lng")
            return (
                f"Geocoding result for '{address}':\n"
                f"- Name: {address}\n"
                f"- Address: {formatted_addr}\n"
                f"- Location: {lat}, {lng}"
            )
    except Exception as exc:
        return f"Could not geocode address '{address}': {exc}"


def search_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "restaurant",
    radius_meters: float = 1000.0,
) -> str:
    """Searches for nearby points of interest of a given type around a coordinate using Google Places API (New).

    Args:
        latitude: Latitude of the center location (e.g. 35.659482).
        longitude: Longitude of the center location (e.g. 139.7005596).
        place_type: Type of place to search for (e.g. 'restaurant', 'cafe', 'tourist_attraction', 'museum', 'lodging').
        radius_meters: Radius in meters to search within (e.g. 1000.0).

    Returns:
        Formatted list of nearby places including name, address, and location (latitude/longitude).
    """
    import os
    import json
    import urllib.request

    key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    payload = {
        "includedTypes": [place_type.lower().strip()],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                },
                "radius": float(radius_meters),
            }
        },
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            places = data.get("places", [])
            if not places:
                return f"No nearby places found of type '{place_type}' near coordinates ({latitude}, {longitude})."

            results = []
            for p in places:
                name = p.get("displayName", {}).get("text", "Unknown Place")
                addr = p.get("formattedAddress", "No address")
                loc = p.get("location", {})
                lat = loc.get("latitude")
                lng = loc.get("longitude")
                results.append(
                    f"- Name: {name}\n  Address: {addr}\n  Location: {lat}, {lng}"
                )
            return f"Found {len(places)} nearby '{place_type}' places:\n" + "\n\n".join(results)
    except Exception as exc:
        return f"Could not search nearby places: {exc}"


def generate_destination_image(
    destination_name: str,
    prompt: str,
    tool_context: ToolContext,
) -> str:
    """Generates a visual postcard/teaser image for a travel destination using Gemini Image model in the global region, saves it as an artifact, and uploads it to public Cloud Storage.

    Args:
        destination_name: Name of the travel destination (e.g. 'Tokyo', 'Paris').
        prompt: Detailed description of the image to generate (e.g. 'A vibrant postcard of Tokyo Tower with cherry blossoms').
        tool_context: Context provided by the agent framework for saving artifacts.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    from google import genai
    from google.genai import types
    from google.cloud import storage

    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    img_bytes = None
    mime_type = "image/jpeg"
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            img_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or mime_type

    if not img_bytes:
        return "Failed to generate destination image."

    slug = destination_name.lower().replace(" ", "-").replace(",", "").strip()
    filename = f"{slug}-postcard.jpg"

    # 1. Save artifact with tool_context.save_artifact so it shows up in Playground's Artifacts panel
    artifact_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(MEDIA_BUCKET_NAME)
    blob_name = f"postcards/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(img_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{MEDIA_BUCKET_NAME}/{blob_name}"
    return public_url


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to extract and save session memories to Memory Bank after each turn."""
    await callback_context.add_session_to_memory()
    return None


code_executor = AgentEngineSandboxCodeExecutor()

a2ui_schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = a2ui_schema_manager.generate_system_prompt(
    role_description=(
        "You are a helpful Smart Travel Concierge. You remember the user's stated "
        "travel preferences, dietary requirements, and food allergies from previous "
        "conversations and use them to personalize all travel recommendations, dining "
        "suggestions, and itineraries. Always pay strict attention to user allergies."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
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
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        get_weather,
        get_current_time,
        search_destinations,
        add_destination,
        convert_currency,
        publish_destination_teaser,
        search_local_spots,
        get_destination_public_holidays,
        geocode_address,
        search_nearby_places,
        generate_destination_image,
        PreloadMemoryTool(),
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
