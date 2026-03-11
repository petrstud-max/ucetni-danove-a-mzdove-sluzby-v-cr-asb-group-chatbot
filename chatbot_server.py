"""
ASB Group AI Chatbot — webovy server.
Pouziva FastAPI + OpenAI GPT-4o + znalostni bazi o ASB Group.
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import uvicorn

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                OPENAI_API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")

client = OpenAI(api_key=OPENAI_API_KEY)
KNOWLEDGE_FILE = Path(__file__).parent / "knowledge.txt"


def get_system_prompt() -> str:
    knowledge = KNOWLEDGE_FILE.read_text(encoding="utf-8") if KNOWLEDGE_FILE.exists() else ""
    return f"""Jsi pratelsky a profesionalni zakaznicky asistent spolecnosti ASB Group.
Odpovidas na otazky zakazniku o firme ASB Group, jejich sluzbech, pobockach a kontaktech.

DULEZITE PRAVIDLO: Odpovidej VELMI STRUCNE — maximalne 2-3 kratke vety.
Pokud se zakaznik pta na detail, odpovez kratce a nabidni ze muzes upresnit.
Odpovidej cesky, presne na zaklade znalostni baze.
Pokud odpoved neznas, doporuc kontaktovat ASB Group primo.

=== ZNALOSTNI BAZE ===
{knowledge}
=== KONEC ZNALOSTNI BAZE ===
"""

app = FastAPI(title="ASB Group Chatbot")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
conversations: dict[str, list] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    reply: str

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    return HTMLResponse((Path(__file__).parent / "index.html").read_text(encoding="utf-8"))

@app.get("/widget.js")
async def serve_widget():
    return Response(content=(Path(__file__).parent / "widget.js").read_text(encoding="utf-8"), media_type="application/javascript")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if req.session_id not in conversations:
        conversations[req.session_id] = [{"role": "system", "content": get_system_prompt()}]
    messages = conversations[req.session_id]
    messages.append({"role": "user", "content": req.message})
    if len(messages) > 21:
        messages = [messages[0]] + messages[-20:]
        conversations[req.session_id] = messages
    try:
        response = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.7, max_tokens=1024)
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Omlouvam se, doslo k chybe: {e}"
    messages.append({"role": "assistant", "content": reply})
    return ChatResponse(reply=reply)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
