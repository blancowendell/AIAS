from groq import Groq
from app.config import settings

# Initialize Groq client with settings
client = Groq(api_key=settings.GROQ_API_KEY)

async def ask_groq(prompt: str) -> str:
    """Send a message to Groq's LLaMA3 model and get a response."""
    response = client.chat.completions.create(
        model="llama3-8b-8192",  # free model on Groq
        messages=[
            {"role": "system", "content": "You are a helpful HR assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content
