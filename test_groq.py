import os
from groq import Groq
from app.config import settings

def ask_groq(prompt: str) -> str:
    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content  # ✅ fixed

if __name__ == "__main__":
    print(ask_groq("Hello AI! Can you tell me a joke?"))
