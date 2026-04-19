import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
try:
    api_key = os.getenv('GEMINI_API_KEY')
    print(f"Loaded API Key: {api_key}")
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-pro", contents="Explain how AI works in 5 words"
    )
    print("\n✅ Success!")
    print(response.text)
except Exception as e:
    print(f"\n❌ API Error: {e}")
