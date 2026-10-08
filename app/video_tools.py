"""Video generation tool for NoodleCraft Concierge using gemini-omni-flash-preview."""

import base64
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


async def generate_noodle_video(
    prompt: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generate a short video for an item in the artisan noodle domain using Google's Omni model (gemini-omni-flash-preview) in the global region.

    The generated video is:
    1. Saved to the session's artifacts using tool_context.save_artifact so it displays in the Playground Artifacts panel.
    2. Uploaded directly to the public Cloud Storage bucket as an mp4 object and returned as a public HTTPS URL.

    Args:
        prompt: Detailed description of the short noodle video to generate (e.g. 'Fresh artisan ramen noodles being gently lifted from a steaming bowl of rich broth with chopsticks', 'Slow motion dough extrusion of fresh square-cut Sanuki udon noodles', 'Artisan soba noodles boiling in bubbling water').
        tool_context: ADK ToolContext used to record artifacts for Playground inspection.

    Returns:
        Dictionary containing the public video URL, artifact filename, and status.
    """
    client = get_genai_client()

    # Call gemini-omni-flash-preview using the interactions API in global location
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=[{"type": "text", "text": prompt}],
        response_format=[{"type": "video"}],
    )

    video_bytes = None
    mime_type = "video/mp4"

    # Extract video bytes from interaction output steps
    if interaction and interaction.steps:
        for step in interaction.steps:
            if getattr(step, "type", None) == "model_output" and getattr(step, "content", None):
                for item in step.content:
                    if getattr(item, "type", None) == "video":
                        if getattr(item, "data", None):
                            raw_data = item.data
                            if isinstance(raw_data, bytes):
                                video_bytes = raw_data
                            elif isinstance(raw_data, str):
                                try:
                                    video_bytes = base64.b64decode(raw_data)
                                except Exception:
                                    video_bytes = raw_data.encode("utf-8")
                        if getattr(item, "mime_type", None):
                            mime_type = item.mime_type
                        if video_bytes:
                            break
            if video_bytes:
                break

    if not video_bytes:
        return {"error": "Failed to generate video from prompt with gemini-omni-flash-preview."}

    # Generate a clean filename for artifact and storage
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", prompt[:24]).strip("_").lower() or "noodle_video"
    unique_suffix = uuid.uuid4().hex[:8]
    filename = f"{slug}_{unique_suffix}.mp4"

    # 1. Save to ADK artifacts via tool_context
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    artifact_version = await tool_context.save_artifact(
        filename=filename,
        artifact=artifact_part,
    )

    # 2. Upload to public Cloud Storage bucket and return public HTTPS URL
    storage_cli = get_storage_client()
    bucket = storage_cli.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    return {
        "status": "success",
        "prompt": prompt,
        "filename": filename,
        "artifact_version": artifact_version,
        "public_url": public_url,
    }
