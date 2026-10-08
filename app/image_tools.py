"""Image generation tool for NoodleCraft Concierge using gemini-3.1-flash-lite-image."""

import re
import uuid
from typing import Any, Dict
from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext

# Hardcoded project ID and public Cloud Storage bucket
PROJECT_ID = "qwiklabs-gcp-04-9f640202d071"
BUCKET_NAME = "qwiklabs-gcp-04-9f640202d071-noodlecraft-media"

_genai_client = None
_storage_client = None


def get_genai_client() -> genai.Client:
    """Return a singleton GenAI Client configured for global Vertex AI."""
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )
    return _genai_client


def get_storage_client() -> storage.Client:
    """Return a singleton Google Cloud Storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


async def generate_noodle_dish_image(
    prompt: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate an appetizing culinary or packaging image for an artisan noodle product, serving concept, or custom order.

    The generated image is:
    1. Saved to the session's artifacts using tool_context.save_artifact so it displays in the Playground Artifacts panel.
    2. Uploaded directly to the public Cloud Storage bucket as an image object and returned as a public HTTPS URL.

    Args:
        prompt: Detailed description of the noodle dish, plated presentation, packaging preview, or factory batch (e.g. 'Steaming bowl of Tokyo wavy ramen with rich chashu and shoyu broth', 'Plated Sanuki udon with tempura flakes and dashi broth', 'Artisan kraft retail box packaging for Hakata straight noodles').
        tool_context: ADK ToolContext used to record artifacts for Playground inspection.

    Returns:
        Dictionary containing the public image URL, artifact filename, and description.
    """
    client = get_genai_client()

    # Call gemini-3.1-flash-lite-image model in global region
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    image_bytes = None
    mime_type = "image/jpeg"

    if response.candidates:
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.inline_data and part.inline_data.data:
                        image_bytes = part.inline_data.data
                        if part.inline_data.mime_type:
                            mime_type = part.inline_data.mime_type
                        break
            if image_bytes:
                break

    if not image_bytes:
        return {"error": "Failed to generate image from prompt."}

    # Generate a clean filename for artifact and storage
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", prompt[:24]).strip("_").lower() or "noodle"
    unique_suffix = uuid.uuid4().hex[:8]
    ext = "png" if "png" in mime_type else "jpg"
    filename = f"{slug}_{unique_suffix}.{ext}"

    # 1. Save to ADK artifacts via tool_context
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    artifact_version = await tool_context.save_artifact(
        filename=filename,
        artifact=artifact_part,
    )

    # 2. Upload to public Cloud Storage bucket and return public HTTPS URL
    storage_cli = get_storage_client()
    bucket = storage_cli.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    return {
        "status": "success",
        "prompt": prompt,
        "filename": filename,
        "artifact_version": artifact_version,
        "public_url": public_url,
    }
