
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load .env from the project folder
project_folder = Path(__file__).resolve().parent
load_dotenv(project_folder / ".env", override=True)

api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

print("Project folder:", project_folder)
print("API key loaded:", bool(api_key))
print("Model:", model)

if not api_key:
    print("ERROR: API key is missing.")
    print("Check the .env filename and its contents.")
else:
    try:
        client = OpenAI(api_key=api_key, timeout=30)

        print("\nSending test request...")

        response = client.responses.create(
            model=model,
            input="Explain Python variables in two simple sentences."
        )

        print("\nSUCCESS! API is working.")
        print(response.output_text)

    except Exception as error:
        print("\nAPI TEST FAILED")
        print("Error type:", type(error).__name__)
        print("Error message:", str(error))
