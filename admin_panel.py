import os
import uvicorn
import time
import uuid
import secrets
import logging
import datetime
import json
from typing import List, Optional, Dict
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# -------------------------------
# Logging-Konfiguration
# -------------------------------
logging.basicConfig(
    filename="admin_panel.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -------------------------------
# Globale Einstellungen (Serverkonfiguration)
# -------------------------------
class Settings(BaseSettings):
    DEFAULT_TEMPERATURE: float = 0.9
    DEFAULT_TOP_P: float = 0.95
    DEFAULT_TOP_K: int = 40
    DEFAULT_MAX_OUTPUT_TOKENS: int = 10240
    API_CALL_INTERVAL: int = 25
    AGENT_CONFIG_FILE: str = "programming_agent_config.json"
    LOG_FILE: str = "think_tank.log"
    DEFAULT_PROMPT_TEMPLATE: str = "{system_prompt}\nWissen: {knowledge}\nBisheriger Verlauf: {history}\nAktuelle Anfrage: {query}"
    MAX_CONCURRENT_REQUESTS: int = 5
    SANDBOX_TIMEOUT: int = 15
    WEB_CRAWLING_TIMEOUT: int = 15
    MAX_URLS_TO_CRAWL: int = 5
    MAX_FILE_SIZE_KB: int = 1024
    FILE_UPLOAD_DIR: str = "uploads"
    CACHE_DIR: str = "cache"
    VECTORDB_PATH: str = "vector_database.db"
    EMBEDDING_MODEL: str = "models/embedding-001"
    USE_BLOCKCHAIN: bool = True
    ENCRYPTION_KEY: Optional[str] = None
    ALLOW_ORIGINS: List[str] = ["*"]  # In der Produktion durch die tatsächlichen Ursprünge ersetzen
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    MAX_DISCUSSION_ROUNDS: int = 10  # Begrenzung für maximale Runden

# Erzeuge eine globale Settings-Instanz (Singleton)
settings = Settings()

# -------------------------------
# Agentenmodell und Orchestrator
# -------------------------------
class Agent(BaseModel):
    # Erzeugt eine eindeutige ID mittels uuid4
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                               # Name des Agenten
    description: str                        # Beschreibung des Agenten
    system_prompt: str                      # System-Prompt, der als Basis für die Antworten dient
    temperature: float = settings.DEFAULT_TEMPERATURE  # Arbeits-Temperatur
    role: str = "Analyst"                   # Rolle des Agenten (z. B. Analyst, Verifizierer etc.)

    async def generate_response(self, knowledge: Dict, history: List[Dict], query: str) -> str:
        """
        Generiert eine Antwort basierend auf dem aktuellen Agenten-Kontext.
        Dabei werden auch Modellparameter (top_p, top_k, max_output_tokens) aus den globalen Einstellungen verwendet.
        """
        # Beispiel: API-Schlüssel validieren (hier als Platzhalter)
        validate_api_key()

        # Falls die Anfrage eine Websuche erfordert, wird diese ausgeführt.
        if "web suchen" in query.lower():
            search_query = query.replace("web suchen", "").strip()
            web_results = await google_search(search_query)
            return f"Hier sind die Ergebnisse aus der Google-Suche: \n{web_results}"

        # Beispiel-Cache-Logik (vereinfacht)
        cache_key = generate_cache_key(self.name, knowledge, history, query)
        cached_response = await self.get_cached_response(cache_key)
        if cached_response:
            logging.info(f"Antwort aus Cache geladen für {self.name} ({self.agent_id})")
            return cached_response

        # Historische Antworten werden für Kontext in den Prompt aufgenommen.
        discussion_context = "\n".join(
            [f"{resp.get('agent_id', 'User')}: {resp.get('response', '')}" for resp in history]
        )
        prompt_text = (
            f"{self.system_prompt}\n"
            f"Aktuelle Diskussion:\n{discussion_context}\n"
            f"Dein Beitrag zur Diskussion: {query}\n"
            f"Formuliere eine Antwort, die auf die letzten Aussagen und Benutzereingaben reagiert, "
            f"und entweder zustimmt, hinterfragt, kritisiert oder neue Anweisungen integriert."
        )

        # Anfrage an das Modell mit den einstellbaren Parametern aus den globalen Einstellungen.
        client = genai.Client()
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt_text,
            config=GenerateContentConfig(
                temperature=self.temperature,
                top_p=settings.DEFAULT_TOP_P,
                top_k=settings.DEFAULT_TOP_K,
                max_output_tokens=settings.DEFAULT_MAX_OUTPUT_TOKENS,
            )
        )
        # Beispielhafte Verarbeitung der Antwort:
        if response and hasattr(response, 'text'):
            logging.info(f"Antwort vom LLM für Agent {self.name} ({self.agent_id}): {response.text}")
            await self.cache_response(cache_key, response.text)
            return response.text
        else:
            logging.error(f"Keine Antwort vom LLM erhalten für Agent {self.name} ({self.agent_id})")
            return "Fehler: Keine Antwort vom LLM erhalten."

    async def get_cached_response(self, cache_key: str) -> Optional[str]:
        # Platzhalter für Cache-Abruf
        return None

    async def cache_response(self, cache_key: str, response: str) -> None:
        # Platzhalter für das Zwischenspeichern der Antwort
        pass

# Beispielhafte Hilfsfunktionen (Platzhalter)
def validate_api_key():
    pass

def generate_cache_key(name: str, knowledge: Dict, history: List[Dict], query: str) -> str:
    data = {
        "name": name,
        "knowledge": knowledge,
        "history": history,
        "query": query
    }
    return str(uuid.uuid4())

def google_search(query: str) -> str:
    # Platzhalter: Hier sollte eine echte Google-Suche implementiert werden.
    return "Suchergebnis..."

# Orchestrator-Klasse, der auch die Agenten aus der JSON-Konfiguration lädt.
class Orchestrator:
    def __init__(self) -> None:
        self.agents: dict[str, Agent] = {}
        self.load_agents_from_config(settings.AGENT_CONFIG_FILE)

    def add_agent(self, agent: Agent) -> None:
        self.agents[agent.agent_id] = agent
        logging.info(f"Agent hinzugefügt: {agent.name} ({agent.agent_id})")

    def get_all_agents(self) -> list[Agent]:
        return list(self.agents.values())

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)

    def load_agents_from_config(self, config_file: str) -> None:
        if not os.path.exists(config_file):
            logging.error(f"Die Konfigurationsdatei '{config_file}' wurde nicht gefunden.")
            return
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                agents_data = json.load(f)
            for agent_data in agents_data:
                try:
                    agent = Agent(
                        name=agent_data["name"],
                        description=agent_data["description"],
                        system_prompt=agent_data["system_prompt"],
                        role=agent_data.get("role", "Analyst"),
                        temperature=agent_data.get("temperature", settings.DEFAULT_TEMPERATURE)
                    )
                    self.add_agent(agent)
                except KeyError as ke:
                    logging.error(f"Fehlender Schlüssel in Agentendaten: {ke}")
                except Exception as e:
                    logging.error(f"Fehler beim Erstellen eines Agenten: {e}")
            logging.info(f"{len(self.agents)} Agenten erfolgreich aus '{config_file}' geladen.")
        except Exception as e:
            logging.error(f"Fehler beim Laden der Agenten-Konfiguration: {e}")

# Erstelle einen globalen Orchestrator
orchestrator = Orchestrator()

# -------------------------------
# FastAPI App und Template-Konfiguration
# -------------------------------
app = FastAPI()

if not os.path.exists("static"):
    os.makedirs("static")
    logging.info("Ordner 'static' wurde erstellt.")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------------------
# Admin-Panel Endpunkte (HTML-Oberfläche)
# -------------------------------

@app.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request) -> HTMLResponse:
    """
    Startseite des Admin-Panels.
    Zeigt eine Übersicht mit Links zu den globalen Einstellungen und den Agenteneinstellungen.
    """
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request) -> HTMLResponse:
    """
    Zeigt ein Formular zur Bearbeitung aller globalen Einstellungen an.
    Die aktuellen Einstellungen werden aus der globalen Settings-Instanz gelesen.
    """
    return templates.TemplateResponse("settings.html", {"request": request, "settings": settings})

@app.post("/admin/settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,
    DEFAULT_TEMPERATURE: float = Form(...),
    DEFAULT_TOP_P: float = Form(...),
    DEFAULT_TOP_K: int = Form(...),
    DEFAULT_MAX_OUTPUT_TOKENS: int = Form(...),
    API_CALL_INTERVAL: int = Form(...),
    AGENT_CONFIG_FILE: str = Form(...),
    LOG_FILE: str = Form(...),
    DEFAULT_PROMPT_TEMPLATE: str = Form(...),
    MAX_CONCURRENT_REQUESTS: int = Form(...),
    SANDBOX_TIMEOUT: int = Form(...),
    WEB_CRAWLING_TIMEOUT: int = Form(...),
    MAX_URLS_TO_CRAWL: int = Form(...),
    MAX_FILE_SIZE_KB: int = Form(...),
    FILE_UPLOAD_DIR: str = Form(...),
    CACHE_DIR: str = Form(...),
    VECTORDB_PATH: str = Form(...),
    EMBEDDING_MODEL: str = Form(...),
    USE_BLOCKCHAIN: Optional[str] = Form(None),
    ENCRYPTION_KEY: str = Form(""),
    ALLOW_ORIGINS: str = Form(...),
    JWT_SECRET_KEY: str = Form(...),
    REDIS_HOST: str = Form(...),
    REDIS_PORT: int = Form(...),
    MAX_DISCUSSION_ROUNDS: int = Form(...)
) -> RedirectResponse:
    """
    Aktualisiert alle globalen Einstellungen anhand der Formularwerte.
    Es werden sämtliche Felder der Settings-Klasse geändert.
    """
    settings.DEFAULT_TEMPERATURE = DEFAULT_TEMPERATURE
    settings.DEFAULT_TOP_P = DEFAULT_TOP_P
    settings.DEFAULT_TOP_K = DEFAULT_TOP_K
    settings.DEFAULT_MAX_OUTPUT_TOKENS = DEFAULT_MAX_OUTPUT_TOKENS
    settings.API_CALL_INTERVAL = API_CALL_INTERVAL
    settings.AGENT_CONFIG_FILE = AGENT_CONFIG_FILE
    settings.LOG_FILE = LOG_FILE
    settings.DEFAULT_PROMPT_TEMPLATE = DEFAULT_PROMPT_TEMPLATE
    settings.MAX_CONCURRENT_REQUESTS = MAX_CONCURRENT_REQUESTS
    settings.SANDBOX_TIMEOUT = SANDBOX_TIMEOUT
    settings.WEB_CRAWLING_TIMEOUT = WEB_CRAWLING_TIMEOUT
    settings.MAX_URLS_TO_CRAWL = MAX_URLS_TO_CRAWL
    settings.MAX_FILE_SIZE_KB = MAX_FILE_SIZE_KB
    settings.FILE_UPLOAD_DIR = FILE_UPLOAD_DIR
    settings.CACHE_DIR = CACHE_DIR
    settings.VECTORDB_PATH = VECTORDB_PATH
    settings.EMBEDDING_MODEL = EMBEDDING_MODEL
    settings.USE_BLOCKCHAIN = True if USE_BLOCKCHAIN is not None else False
    settings.ENCRYPTION_KEY = ENCRYPTION_KEY if ENCRYPTION_KEY != "" else None
    settings.ALLOW_ORIGINS = [origin.strip() for origin in ALLOW_ORIGINS.split(",") if origin.strip()]
    settings.JWT_SECRET_KEY = JWT_SECRET_KEY
    settings.REDIS_HOST = REDIS_HOST
    settings.REDIS_PORT = REDIS_PORT
    settings.MAX_DISCUSSION_ROUNDS = MAX_DISCUSSION_ROUNDS

    logging.info("Globale Einstellungen wurden aktualisiert.")
    return RedirectResponse(url="/admin/settings", status_code=303)

# Neuer Endpunkt: Formular zum Hinzufügen eines neuen Agenten (GET)
@app.get("/admin/agents/new", response_class=HTMLResponse)
async def add_agent_form(request: Request) -> HTMLResponse:
    """
    Zeigt ein Formular zum Hinzufügen eines neuen Agenten an.
    """
    return templates.TemplateResponse("agent_add.html", {"request": request, "settings": settings})

# Neuer Endpunkt: Verarbeitung des Formulars zum Hinzufügen eines neuen Agenten (POST)
@app.post("/admin/agents/new", response_class=HTMLResponse)
async def add_agent(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    system_prompt: str = Form(...),
    temperature: float = Form(...),
    role: str = Form(...)
) -> RedirectResponse:
    """
    Nimmt die Formulardaten entgegen, erstellt einen neuen Agenten und fügt ihn dem Orchestrator hinzu.
    """
    new_agent = Agent(
        name=name,
        description=description,
        system_prompt=system_prompt,
        temperature=temperature,
        role=role
    )
    orchestrator.add_agent(new_agent)
    logging.info(f"Neuer Agent hinzugefügt: {new_agent.name} ({new_agent.agent_id})")
    return RedirectResponse(url="/admin/agents", status_code=303)

@app.get("/admin/agents", response_class=HTMLResponse)
async def admin_agents(request: Request) -> HTMLResponse:
    """
    Zeigt eine Übersicht aller registrierten Agenten an.
    Jeder Agent wird mit einem Link versehen, über den die Details bearbeitet werden können.
    """
    agents = orchestrator.get_all_agents()
    return templates.TemplateResponse("agents.html", {"request": request, "agents": agents})

@app.get("/admin/agents/{agent_id}", response_class=HTMLResponse)
async def edit_agent(request: Request, agent_id: str) -> HTMLResponse:
    """
    Zeigt ein Formular zur Bearbeitung der Einstellungen eines bestimmten Agenten an.
    Falls der Agent nicht gefunden wird, wird ein HTTP 404 Fehler ausgelöst.
    """
    agent = orchestrator.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent nicht gefunden.")
    return templates.TemplateResponse("agent_edit.html", {"request": request, "agent": agent})

@app.post("/admin/agents/{agent_id}", response_class=HTMLResponse)
async def update_agent(
    request: Request,
    agent_id: str,
    name: str = Form(...),
    description: str = Form(...),
    system_prompt: str = Form(...),
    temperature: float = Form(...),
    role: str = Form(...)
) -> RedirectResponse:
    """
    Aktualisiert die Daten eines Agenten anhand der Formularwerte.
    Mithilfe von strukturellem Pattern Matching (match/case) wird sichergestellt,
    dass der gefundene Agent aktualisiert wird.
    """
    agent = orchestrator.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent nicht gefunden.")
    match agent:
        case Agent():
            agent.name = name
            agent.description = description
            agent.system_prompt = system_prompt
            agent.temperature = temperature
            agent.role = role
            logging.info(f"Agent {agent.agent_id} wurde aktualisiert.")
    return RedirectResponse(url="/admin/agents", status_code=303)

# -------------------------------
# Automatisches Erstellen von Template-Dateien
# -------------------------------
def create_templates_if_not_exist() -> None:
    """
    Überprüft, ob die Ordner "templates" und "static" existieren.
    Falls nicht, werden sie angelegt und Beispiel-HTML-Templates erstellt.
    """
    if not os.path.exists("templates"):
        os.makedirs("templates")
    if not os.path.exists("static"):
        os.makedirs("static")

    # Template: admin.html – Startseite des Admin-Panels
    admin_html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Admin Panel</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Admin Panel</h1>
    <ul>
        <li><a href="/admin/settings">Globale Einstellungen bearbeiten</a></li>
        <li><a href="/admin/agents">Agenten Einstellungen bearbeiten</a></li>
        <li><a href="/admin/agents/new">Neuen Agenten hinzufügen</a></li>
    </ul>
</body>
</html>
"""
    with open("templates/admin.html", "w", encoding="utf-8") as f:
        f.write(admin_html)

    # Template: settings.html – Formular für globale Einstellungen (alle Felder)
    settings_html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Globale Einstellungen</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Globale Einstellungen</h1>
    <form action="/admin/settings" method="post">
        <label for="DEFAULT_TEMPERATURE">Default Temperature (0-1):</label>
        <input type="number" step="0.01" name="DEFAULT_TEMPERATURE" value="{{ settings.DEFAULT_TEMPERATURE }}" required><br>

        <label for="DEFAULT_TOP_P">Default Top P (0-1):</label>
        <input type="number" step="0.01" name="DEFAULT_TOP_P" value="{{ settings.DEFAULT_TOP_P }}" required><br>

        <label for="DEFAULT_TOP_K">Default Top K:</label>
        <input type="number" name="DEFAULT_TOP_K" value="{{ settings.DEFAULT_TOP_K }}" required><br>

        <label for="DEFAULT_MAX_OUTPUT_TOKENS">Default Max Output Tokens:</label>
        <input type="number" name="DEFAULT_MAX_OUTPUT_TOKENS" value="{{ settings.DEFAULT_MAX_OUTPUT_TOKENS }}" required><br>

        <label for="API_CALL_INTERVAL">API Call Interval (Sekunden):</label>
        <input type="number" name="API_CALL_INTERVAL" value="{{ settings.API_CALL_INTERVAL }}" required><br>

        <label for="AGENT_CONFIG_FILE">Agent Config File:</label>
        <input type="text" name="AGENT_CONFIG_FILE" value="{{ settings.AGENT_CONFIG_FILE }}" required><br>

        <label for="LOG_FILE">Log File:</label>
        <input type="text" name="LOG_FILE" value="{{ settings.LOG_FILE }}" required><br>

        <label for="DEFAULT_PROMPT_TEMPLATE">Default Prompt Template:</label>
        <textarea name="DEFAULT_PROMPT_TEMPLATE" required>{{ settings.DEFAULT_PROMPT_TEMPLATE }}</textarea><br>

        <label for="MAX_CONCURRENT_REQUESTS">Max Concurrent Requests:</label>
        <input type="number" name="MAX_CONCURRENT_REQUESTS" value="{{ settings.MAX_CONCURRENT_REQUESTS }}" required><br>

        <label for="SANDBOX_TIMEOUT">Sandbox Timeout (Sekunden):</label>
        <input type="number" name="SANDBOX_TIMEOUT" value="{{ settings.SANDBOX_TIMEOUT }}" required><br>

        <label for="WEB_CRAWLING_TIMEOUT">Web Crawling Timeout (Sekunden):</label>
        <input type="number" name="WEB_CRAWLING_TIMEOUT" value="{{ settings.WEB_CRAWLING_TIMEOUT }}" required><br>

        <label for="MAX_URLS_TO_CRAWL">Max URLs to Crawl:</label>
        <input type="number" name="MAX_URLS_TO_CRAWL" value="{{ settings.MAX_URLS_TO_CRAWL }}" required><br>

        <label for="MAX_FILE_SIZE_KB">Max File Size (KB):</label>
        <input type="number" name="MAX_FILE_SIZE_KB" value="{{ settings.MAX_FILE_SIZE_KB }}" required><br>

        <label for="FILE_UPLOAD_DIR">File Upload Directory:</label>
        <input type="text" name="FILE_UPLOAD_DIR" value="{{ settings.FILE_UPLOAD_DIR }}" required><br>

        <label for="CACHE_DIR">Cache Directory:</label>
        <input type="text" name="CACHE_DIR" value="{{ settings.CACHE_DIR }}" required><br>

        <label for="VECTORDB_PATH">Vector DB Path:</label>
        <input type="text" name="VECTORDB_PATH" value="{{ settings.VECTORDB_PATH }}" required><br>

        <label for="EMBEDDING_MODEL">Embedding Model:</label>
        <input type="text" name="EMBEDDING_MODEL" value="{{ settings.EMBEDDING_MODEL }}" required><br>

        <label for="USE_BLOCKCHAIN">Use Blockchain:</label>
        <input type="checkbox" name="USE_BLOCKCHAIN" {% if settings.USE_BLOCKCHAIN %}checked{% endif %}><br>

        <label for="ENCRYPTION_KEY">Encryption Key:</label>
        <input type="text" name="ENCRYPTION_KEY" value="{{ settings.ENCRYPTION_KEY or '' }}"><br>

        <label for="ALLOW_ORIGINS">Allow Origins (Komma-separiert):</label>
        <input type="text" name="ALLOW_ORIGINS" value="{{ settings.ALLOW_ORIGINS | join(', ') }}" required><br>

        <label for="JWT_SECRET_KEY">JWT Secret Key:</label>
        <input type="text" name="JWT_SECRET_KEY" value="{{ settings.JWT_SECRET_KEY }}" required><br>

        <label for="REDIS_HOST">Redis Host:</label>
        <input type="text" name="REDIS_HOST" value="{{ settings.REDIS_HOST }}" required><br>

        <label for="REDIS_PORT">Redis Port:</label>
        <input type="number" name="REDIS_PORT" value="{{ settings.REDIS_PORT }}" required><br>

        <label for="MAX_DISCUSSION_ROUNDS">Max Discussion Rounds:</label>
        <input type="number" name="MAX_DISCUSSION_ROUNDS" value="{{ settings.MAX_DISCUSSION_ROUNDS }}" required><br>

        <button type="submit">Einstellungen aktualisieren</button>
    </form>
    <br>
    <a href="/admin">Zurück zum Admin Panel</a>
</body>
</html>

"""
    with open("templates/settings.html", "w", encoding="utf-8") as f:
        f.write(settings_html)

    # Template: agents.html – Übersicht aller Agenten
    agents_html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Agenten Übersicht</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Agenten Übersicht</h1>
    <ul>
    {% for agent in agents %}
        <li>
            <a href="/admin/agents/{{ agent.agent_id }}">{{ agent.name }}</a> - {{ agent.description }}
        </li>
    {% endfor %}
    </ul>
    <br>
    <a href="/admin">Zurück zum Admin Panel</a>
</body>
</html>
"""
    with open("templates/agents.html", "w", encoding="utf-8") as f:
        f.write(agents_html)

    # Template: agent_edit.html – Formular zum Bearbeiten eines Agenten
    agent_edit_html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Agent bearbeiten</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Agent bearbeiten: {{ agent.name }}</h1>
    <form action="/admin/agents/{{ agent.agent_id }}" method="post">
        <label for="name">Name:</label>
        <input type="text" name="name" value="{{ agent.name }}" required><br>
        <label for="description">Beschreibung:</label>
        <textarea name="description" required>{{ agent.description }}</textarea><br>
        <label for="system_prompt">System Prompt:</label>
        <textarea name="system_prompt" required>{{ agent.system_prompt }}</textarea><br>
        <label for="temperature">Temperature (0-1):</label>
        <input type="number" step="0.01" name="temperature" value="{{ agent.temperature }}" required><br>
        <label for="role">Rolle:</label>
        <input type="text" name="role" value="{{ agent.role }}" required><br>
        <button type="submit">Agent aktualisieren</button>
    </form>
    <br>
    <a href="/admin/agents">Zurück zur Agenten Übersicht</a>
</body>
</html>
"""
    with open("templates/agent_edit.html", "w", encoding="utf-8") as f:
        f.write(agent_edit_html)

    # Neues Template: agent_add.html – Formular zum Hinzufügen eines neuen Agenten
    agent_add_html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Neuen Agenten hinzufügen</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Neuen Agenten hinzufügen</h1>
    <form action="/admin/agents/new" method="post">
        <label for="name">Name:</label>
        <input type="text" name="name" required><br>
        <label for="description">Beschreibung:</label>
        <textarea name="description" required></textarea><br>
        <label for="system_prompt">System Prompt:</label>
        <textarea name="system_prompt" required></textarea><br>
        <label for="temperature">Temperature (0-1):</label>
        <input type="number" step="0.01" name="temperature" value="{{ settings.DEFAULT_TEMPERATURE }}" required><br>
        <label for="role">Rolle:</label>
        <input type="text" name="role" value="Analyst" required><br>
        <button type="submit">Agent hinzufügen</button>
    </form>
    <br>
    <a href="/admin/agents">Zurück zur Agenten Übersicht</a>
</body>
</html>
"""
    with open("templates/agent_add.html", "w", encoding="utf-8") as f:
        f.write(agent_add_html)

    # Neues Template: index.html – Hauptseite der Anwendung
    index_html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KI-Agenten Think Tank</title>
    <link rel="stylesheet" href="/static/style.css">
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
</head>
<body>
    <div class="container">
        <h1>KI-Think Tank</h1>

        <div class="form-group">
            <label for="agentenSelect">Wähle Agenten:</label>
            <select id="agentenSelect" multiple>
                <option value="">Agenten werden geladen...</option>
            </select>
        </div>

        <div class="form-group">
            <label for="frage">Deine Frage (Für Websuche: "web suchen: Frage eingeben"):</label>
            <textarea id="frage" rows="6" cols="60"></textarea>
        </div>

        <div class="form-group">
            <label for="rounds">Anzahl der Runden (max. 10):</label>
            <input type="number" id="rounds" value="3" min="1" max="10">
        </div>

        <button onclick="frageSenden()" class="send-button">Think Tank starten</button>
        <button onclick="anweisungSenden()" class="send-button">Neue Anweisung senden</button>

        <h2>Diskussionsverlauf:</h2>
        <div id="antwort" class="response-area"></div>
    </div>

    <script>
    let aktuelleSitzung = null;  // Speichert die session_id für weitere Anweisungen

    // Lade Agenten dynamisch beim Start
    window.onload = async function() {
        const agentenSelect = document.getElementById('agentenSelect');
        agentenSelect.innerHTML = '<option>Agenten werden geladen...</option>';

        try {
            const response = await fetch('http://localhost:8000/agents/');
            const agenten = await response.json();
            agentenSelect.innerHTML = '';

            if (agenten.length === 0) {
                agentenSelect.innerHTML = '<option>Keine Agenten verfügbar</option>';
                return;
            }

            agenten.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.agent_id;
                option.textContent = agent.name;
                agentenSelect.appendChild(option);
            });

        } catch (error) {
            console.error('Fehler:', error);
            agentenSelect.innerHTML = '<option>Fehler beim Laden der Agenten</option>';
        }
    }

    // Think Tank starten (Neue Sitzung)
    async function frageSenden() {
        const agentenSelect = document.getElementById('agentenSelect');
        const agent_ids = Array.from(agentenSelect.selectedOptions).map(option => option.value);
        const frage = document.getElementById('frage').value;
        const rounds = parseInt(document.getElementById('rounds').value);
        const antwortDiv = document.getElementById('antwort');

        if (agent_ids.length < 1) {
            alert("Bitte wähle mindestens zwei Agenten!");
            return;
        }
        if (!frage) {
            alert("Bitte stelle eine Frage!");
            return;
        }

        antwortDiv.innerHTML = "<strong>Diskussion startet...</strong><br>";

        const requestBody = {
            agent_ids: agent_ids,
            query: frage,
            rounds: rounds
        };

        try {
            const response = await fetch('http://localhost:8000/interact_think_tank/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();
            aktuelleSitzung = data.session_id;  // Sitzung merken
            displayAntwort(data, antwortDiv);

        } catch (error) {
            antwortDiv.innerHTML = '<strong>Fehler:</strong> ' + error;
        }
    }

    // Neue Anweisung während einer laufenden Sitzung senden
    async function anweisungSenden() {
        if (!aktuelleSitzung) {
            alert("Es gibt keine aktive Sitzung! Starte erst eine neue Think Tank Diskussion.");
            return;
        }

        const frage = document.getElementById('frage').value;
        if (!frage) {
            alert("Bitte gib eine neue Anweisung ein!");
            return;
        }

        const antwortDiv = document.getElementById('antwort');
        antwortDiv.innerHTML += "<strong>Neue Anweisung wird verarbeitet...</strong><br>";

        const requestBody = {
            session_id: aktuelleSitzung,
            query: frage
        };

        try {
            const response = await fetch('http://localhost:8000/interact_think_tank/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();
            displayAntwort(data, antwortDiv);

        } catch (error) {
            antwortDiv.innerHTML = '<strong>Fehler:</strong> ' + error;
        }
    }

    // Antwort anzeigen (inklusive Code-Validierung)
    function displayAntwort(data, antwortDiv) {
        let discussionText = "<strong>Diskussionsverlauf:</strong><br><br>";

        data.history.forEach((entry, index) => {
            if (entry.role === "user") {
                discussionText += `<b>👤 Du:</b> ${entry.response}<br><br>`;
            } else {
                discussionText += `🔹 <b>Agent ${entry.agent_id}:</b> ${entry.response}<br><br>`;
            }
        });

        // Code-Validierung: Falls Code angefordert, aber nicht geliefert wurde
        if (data.error) {
            discussionText += `<hr><strong style="color:red;">⚠️ Fehler:</strong> ${data.error}`;
        } else {
            discussionText += `<hr><strong>Finale Antwort:</strong> ${data.history[data.history.length - 1].response}`;
        }

        antwortDiv.innerHTML = discussionText;
    }
    </script>
</body>
</html>
"""
    with open("templates/index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    # CSS-Datei: style.css
    style_css = """body {
    font-family: 'Roboto', sans-serif;
    background-color: #f7f7f7;
    color: #333;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
}

.container {
    background-color: #fff;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    width: 80%;
    max-width: 800px;
    margin: 2rem auto;
}

h1 {
    color: #2c3e50;
    text-align: center;
    margin-bottom: 1.5rem;
}

label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
}

input[type="number"],
textarea,
select {
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    box-sizing: border-box;
    font-family: inherit;
    font-size: 1rem;
    resize: vertical;
}

input[type="number"]:focus,
textarea:focus,
select:focus {
    border-color: #3498db;
    outline: none;
    box-shadow: 0 0 5px rgba(52, 152, 219, 0.3);
}

.send-button {
    background-color: #3498db;
    color: white;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    transition: background-color 0.2s ease;
}

.send-button:hover {
    background-color: #2980b9;
}

.response-area {
    margin-top: 1rem;
    padding: 1rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: #f9f9f9;
    white-space: pre-wrap;
}

.form-group {
    margin-bottom: 1.5rem;
}
"""
    with open("static/style.css", "w", encoding="utf-8") as f:
        f.write(style_css)

# -------------------------------
# Main-Funktion: Serverstart
# -------------------------------
if __name__ == "__main__":
    create_templates_if_not_exist()
    logging.info("Starte den Server auf http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8001)
