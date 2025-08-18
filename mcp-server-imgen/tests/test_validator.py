import asyncio
import base64
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..\src")))

from mcp_server_imgen.google_client.config import get_gemini_model
from mcp_server_imgen.validation import validate_image, validation_prompt


async def run_validation_tests():
    image_dir = "mcp-server-imgen/tests/files"

    # Initialize the Gemini model
    gemini_model = get_gemini_model()

    for filename in os.listdir(image_dir):
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
            filepath = os.path.join(image_dir, filename)
            print(f"Processing image: {filepath}")

            with open(filepath, "rb") as image_file:
                image_bytes = image_file.read()
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            try:
                is_valid = await validate_image(
                    model=gemini_model,
                    image_base64=image_base64,
                    validation_prompt=validation_prompt,
                )
                print(
                    f"Validation result for {filename}: {'Valid' if is_valid else 'Invalid'}"
                )
            except Exception as e:
                print(f"Error validating {filename}: {e}")


if __name__ == "__main__":
    asyncio.run(run_validation_tests())
