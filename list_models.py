import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Erro: GEMINI_API_KEY não encontrado.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

print("Listando modelos disponíveis:")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name} ({m.display_name})")
except Exception as e:
    print(f"Erro ao listar modelos: {e}")
