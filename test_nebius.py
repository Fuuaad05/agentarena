import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("NEBIUS_BASE_URL"),
    api_key=os.getenv("NEBIUS_API_KEY"),
)

model = os.getenv("NEBIUS_MODEL")

print("Connecting to Nebius Token Factory...")
print(f"Model: {model}")

response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "system",
            "content": "Follow the user's instruction exactly."
        },
        {
            "role": "user",
            "content": "Reply with exactly: AGENTARENA_OK"
        }
    ],
    max_tokens=100,
    temperature=0,
)

print("\n=== FULL RESPONSE ===")
print(response.model_dump_json(indent=2))

print("\n=== CHOICE ===")
print(response.choices[0])

print("\n=== MESSAGE ===")
print(response.choices[0].message)

print("\n=== CONTENT ===")
print(repr(response.choices[0].message.content))

print("\n=== FINISH REASON ===")
print(response.choices[0].finish_reason)

print("\n=== USAGE ===")
print(response.usage)