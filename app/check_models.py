import os

from google import genai

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY is not configured.")

client = genai.Client(api_key=api_key)

print("Asking Google for the list of available models...\n")
print("-" * 40)

# 2. Call the list() function
try:
    models = client.models.list()
    for model in models:
        # We only want to see models that can generate text (generateContent)
        if "generateContent" in model.supported_actions:
            print(f"✅ Model Name: {model.name}")
            
    print("-" * 40)
    print("Done! Copy one of the names above and use it in your main.py")

except Exception as e:
    print(f"An error occurred: {e}")
