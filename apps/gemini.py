from google import genai
from config import Config

def get_gemini_response(prompt):
    client = genai.Client(api_key=Config.GEMINI_API_KEY)

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )

    return response.text
