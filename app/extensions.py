import os
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from langchain_google_genai import ChatGoogleGenerativeAI

db = SQLAlchemy()
oauth = OAuth()

# Initialize LLM
llm = None
GENAI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GENAI_API_KEY:
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=0.2,
            max_output_tokens=2000,
            google_api_key=GENAI_API_KEY
        )
    except Exception as e:
        print(f"ERROR: Failed to initialize LLM: {e}")
else:
    print("WARNING: GEMINI_API_KEY not found in environment. AI features will be disabled.")
