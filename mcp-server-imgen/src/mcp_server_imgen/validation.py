import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)

class ImageValidationError(Exception):
    """Errors during image validation."""
    pass

validation_prompt = """
You are an expert at evaluating images.
You are given an image and its original prompt. Your task is to determine if the image is valid based on a strict set of rules.

You must DECLINE the image and mark it as "invalid" if it violates any of the following criteria:
1.  **Abnormal Hands**: Any depiction of human hands must be anatomically correct. This means exactly five fingers per hand, naturally placed, without any overlapping or malformations.
2.  **Anatomical Body Positioning**: All body parts, especially joints and limbs (e.g., elbows, arms, shoulders, knees, legs), must be anatomically correct and positioned naturally relative to each other, without distortion or unnatural angles.
3.  **Incorrect Background Text**: Any text in the background must consist of real, recognizable words from a known language. Gibberish or nonsensical strings of characters are not allowed. However, well-formed words from a consistent, fictional language are permissible.
3. **Non-anatomical hands**: 

You should output JSON with the following format:
{{
    "image_validity": "valid" or "invalid",
    "reasoning": "reasoning"
}}

- "image_validity" should be "valid" if the image meets all criteria.
- "image_validity" should be "invalid" if the image violates one or more criteria.
- "reasoning" should be a concise explanation for your decision, specifically referencing the rule that was violated if the image is invalid.
"""

async def validate_image(model: genai.GenerativeModel, 
                         image_base64: str, 
                         validation_prompt: str) -> bool:
        """Validate image using Google Gemini Pro Vision.
        
        Raises:
            ImageValidationError: If the validation fails.
        """
        try:
            response = await model.generate_content_async(
                [                
                    validation_prompt,
                    "Here is the image:",
                    {"mime_type": "image/jpeg", "data": image_base64}
                ]
            )

            logger.info(f"Validation response: {response.text}")
            return "invalid" not in response.text.lower()
        except Exception as e:
            logger.error(f"Error during image validation: {e}")
            raise ImageValidationError(f"Error during image validation: {e}") from e