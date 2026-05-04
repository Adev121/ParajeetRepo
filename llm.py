import google.generativeai as genai
import os
import base64
from PIL import Image
from dotenv import load_dotenv

try:
    from groq import Groq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False

load_dotenv()
os.environ['GOOGLE_API_KEY'] = os.getenv('GOOGLE_API_KEY') or ''
os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY') or ''

# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_quota_error(exc: Exception) -> bool:
    """Return True if the exception is a Gemini quota / permission error."""
    msg = str(exc).lower()
    return any(k in msg for k in ('403', '429', 'quota', 'resource_exhausted',
                                   'permission_denied', 'rate limit', 'ratelimit'))

def _groq_text(prompt: str) -> str:
    """Call Groq text model (fallback)."""
    if not _GROQ_AVAILABLE:
        return "Groq SDK not installed. Run: pip install groq"
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY is not set. Please add it to your .env file."
    client = Groq(api_key=api_key)
    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return chat.choices[0].message.content

def _groq_vision(image_path: str, prompt: str) -> str:
    """Call Groq vision model with a local image (fallback)."""
    if not _GROQ_AVAILABLE:
        return "Groq SDK not installed. Run: pip install groq"
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY is not set. Please add it to your .env file."
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    client = Groq(api_key=api_key)
    chat = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    )
    return chat.choices[0].message.content

# ── Public API ────────────────────────────────────────────────────────────────

def init_llm():
    """Initialize the Gemini API client using the environment variable."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def process_vision_query(image_path, prompt="Please read any questions or problems on this screen. Provide the best answer clearly and concisely. Explain briefly if needed."):
    """Processes an image using Gemini; falls back to Groq on quota/403 errors."""
    if not os.environ.get("GOOGLE_API_KEY"):
        return "Error: GOOGLE_API_KEY environment variable is not set."
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        img = Image.open(image_path)
        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        if _is_quota_error(e):
            note = "⚠️ Gemini quota exceeded — switching to Groq fallback.\n\n"
            return note + _groq_vision(image_path, prompt)
        return f"Error interacting with LLM: {str(e)}"

def process_text_query(text):
    """Processes plain text using Gemini; falls back to Groq on quota/403 errors."""
    if not os.environ.get("GOOGLE_API_KEY"):
        return "Error: GOOGLE_API_KEY environment variable is not set."
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Please answer the following question or respond to the prompt: {text}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if _is_quota_error(e):
            note = "⚠️ Gemini quota exceeded — switching to Groq fallback.\n\n"
            prompt = f"Please answer the following question or respond to the prompt: {text}"
            return note + _groq_text(prompt)
        return f"Error interacting with LLM: {str(e)}"
