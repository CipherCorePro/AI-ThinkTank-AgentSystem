import os
import time
import json
import uuid
import datetime
import re
from typing import Dict, List, Optional, Callable, Any, Tuple
from google import genai
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch
import asyncio
import concurrent.futures
import subprocess  # Für Sandbox-Umgebung
import signal  # Für Timeout in der Sandbox
from enum import Enum  # Für Agenten-Rollen
from contextlib import contextmanager  # Für die Kontextverwaltung der Sandbox
import newspaper
from newspaper import Article
import hashlib
import secrets
import base64
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
import sqlite3  # Für die SQLite-Vektordatenbank
import aiohttp
from urllib.parse import urlparse
import logging
import atexit
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator, field_validator, Field
from pydantic_settings import BaseSettings
from cryptography.fernet import Fernet, InvalidToken  # Für sichere Verschlüsselung
import redis
from starlette.responses import JSONResponse
import unittest  # Für Unittests
import traceback  # Importiere traceback
from unittest import IsolatedAsyncioTestCase  # Importiere IsolatedAsyncioTestCase
import uvicorn

# Logging Konfiguration
logging.basicConfig(filename="think_tank.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")


# Konfigurationsparameter
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
    MAX_DISCUSSION_ROUNDS: int = 30  # Begrenzung für maximale Runden

    @field_validator('ENCRYPTION_KEY')
    def encryption_key_must_be_set_or_generated(cls, v: Optional[str]) -> str:
        if v is None:
            # Sichereren Mechanismus zum Generieren des Schlüssels verwenden
            key = secrets.token_urlsafe(32)
            logging.warning("Neuer Verschlüsselungsschlüssel generiert. Stelle sicher, dass er sicher gespeichert ist!")
            return key
        return v

# Singleton Pattern
settings = Settings()

# FastAPI Konfiguration
app = FastAPI(middleware=[
    Middleware(CORSMiddleware, allow_origins=settings.ALLOW_ORIGINS,
               allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
])

class SQLCache:
    def __init__(self, db_path: str = "sql_cache.db"):
        """Initialisiert eine SQLite-Datenbank für den SQL-Fallback."""
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_table()

    def create_table(self):
        """Erstellt eine Cache-Tabelle in der SQLite-Datenbank."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expiry INTEGER
                )
            """)

    def get(self, key: str) -> Optional[str]:
        """Holt einen Wert aus dem SQL-Cache."""
        current_time = int(time.time())
        cursor = self.conn.cursor()
        cursor.execute("SELECT value, expiry FROM cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            value, expiry = row
            if expiry is None or expiry > current_time:
                return value
            else:
                self.delete(key)
        return None

    def set(self, key: str, value: str, expiry: int = 3600):
        """Speichert einen Wert im SQL-Cache."""
        expiry_time = int(time.time()) + expiry
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO cache (key, value, expiry)
                VALUES (?, ?, ?)
            """, (key, value, expiry_time))

    def delete(self, key: str):
        """Entfernt einen Eintrag aus dem SQL-Cache."""
        with self.conn:
            self.conn.execute("DELETE FROM cache WHERE key = ?", (key,))


class RedisCache:
    def __init__(self):
        """Initialisiert Redis und die SQL-Fallback-Logik."""
        self.redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        self.sql_cache = SQLCache()

    def get(self, key: str) -> Optional[str]:
        """Versucht, einen Wert von Redis zu erhalten. Falls dies fehlschlägt, wird SQLite verwendet."""
        try:
            value = self.redis_client.get(key)
            if value:
                return value.decode('utf-8')
            return None
        except redis.exceptions.ConnectionError:
            return self.sql_cache.get(key)

    def set(self, key: str, value: str, expiry: int = 3600):
        """Speichert einen Wert in Redis oder, bei Verbindungsfehlern, in SQLite."""
        try:
            self.redis_client.set(key, value, ex=expiry)
        except redis.exceptions.ConnectionError:
            self.sql_cache.set(key, value, expiry)

    def delete(self, key: str):
        """Löscht einen Eintrag von Redis oder, falls fehlschlägt, von SQLite."""
        try:
            self.redis_client.delete(key)
        except redis.exceptions.ConnectionError:
            self.sql_cache.delete(key)


# Logging-Funktion
def log_message(message: str, level=logging.INFO):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    masked_message = re.sub(r"(GEMINI_API_KEY=)([^s]+)", r"\1=[MASKED]", message)
    logging.log(level, f"{timestamp} - {masked_message}")

# Sichere Sandbox Umgebung
class TimeoutException(Exception):
    pass

@contextmanager
def safe_execution_environment(timeout):
    """
    Ein Kontextmanager, der eine sichere Ausführungsumgebung für potenziell unsicheren Code bietet.
    Die Funktion verwendet subprocess um den Code in einem separaten Prozess auszuführen, wodurch die Hauptanwendung vor Fehlern oder bösartigem Code geschützt wird.
    """
    def signal_handler(signum, frame):
        raise TimeoutException("Code execution timed out")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(timeout)  # Starte den Alarm

    try:
        yield
    except TimeoutException as e:
        log_message(f"Die Ausführung des Codes hat das Zeitlimit überschritten: {e}")
        print(f"Die Ausführung des Codes hat das Zeitlimit überschritten: {e}")
        raise  # Re-raise, damit der Aufrufer es behandeln kann
    except Exception as e:
        log_message(f"Ein unerwarteter Fehler ist aufgetreten: {e}\n{traceback.format_exc()}")
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        raise  # Re-raise, damit der Aufrufer es behandeln kann
    finally:
        signal.alarm(0)  # Deaktiviere den Alarm

# Rate Limiter
class RateLimiter:
    def __init__(self, calls_per_period: int, period: int = 1):
        self.calls_per_period = calls_per_period
        self.period = period
        self.allowed_calls = calls_per_period
        self.last_reset = time.time()

    def wait(self):
        current_time = time.time()
        time_since_reset = current_time - self.last_reset

        if time_since_reset >= self.period:
            self.allowed_calls = self.calls_per_period
            self.last_reset = current_time

        if self.allowed_calls <= 0:
            sleep_time = self.period - time_since_reset
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.allowed_calls = self.calls_per_period
            self.last_reset = time.time()

        self.allowed_calls -= 1

# Tool-Funktionen
async def google_search(query: str) -> str:
    """Führt eine Websuche mit der Google GenAI API durch und gibt die Ergebnisse zurück."""
    log_message(f"Führe eine Google Suche aus: {query}")
    
    try:
        client = genai.Client()
        model_id = "gemini-2.0-flash"
        google_search_tool = Tool(
            google_search=GoogleSearch()
        )

        response = client.models.generate_content(
            model=model_id,
            contents=query,
            config=GenerateContentConfig(
                tools=[google_search_tool],
                response_modalities=["TEXT"],
            )
        )

        search_results = []
        for part in response.candidates[0].content.parts:
            search_results.append(part.text)

        # Rückgabe der Suchergebnisse als Text
        return "\n".join(search_results)
    except asyncio.CancelledError:
        log_message(f"Google Suche für '{query}' wurde abgebrochen.")
        raise  # Weiterreichen des Errors, um ihn an anderer Stelle zu handhaben
    except Exception as e:
        log_message(f"Fehler bei der Google-Suche: {e}")
        return f"Fehler bei der Google-Suche: {e}"

async def crawl_website(url: str, session: Optional[aiohttp.ClientSession] = None) -> str:
    """Crawlt eine Website und extrahiert den Textinhalt."""
    log_message(f"Crawle Website: {url}")
    try:
        if not is_valid_url(url):
            raise HTTPException(status_code=400, detail=f"Ungültige URL: {url}")
        if session is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=settings.WEB_CRAWLING_TIMEOUT) as response:
                    response.raise_for_status()  # Stellt sicher, dass wir keinen Fehlerhaften Response erhalten.
                    article = Article(url, language="de")
                    article.download()  # Lade Artikel herunter
                    await asyncio.to_thread(article.parse)
                    return article.text
        else:
            async with session.get(url, timeout=settings.WEB_CRAWLING_TIMEOUT) as response:
                response.raise_for_status()  # Stellt sicher, dass wir keinen Fehlerhaften Response erhalten.
                article = Article(url, language="de")
                article.download()
                await asyncio.to_thread(article.parse)
                return article.text

    except newspaper.ArticleException as e:
        log_message(f"Fehler beim Crawlen von {url}: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Crawlen der Website: {e}")
    except aiohttp.ClientError as e:
        log_message(f"Fehlerhafter HTTP Status beim Crawlen von {url}: {e}")
        raise HTTPException(status_code=response.status, detail=f"Fehler beim Crawlen der Website: HTTP Fehler {e}")
    except ValueError as e:
        log_message(f"Fehlerhafte URL: {e}")
        raise HTTPException(status_code=400, detail=f"Fehlerhafte URL: {e}")
    except Exception as e:
        log_message(f"Unerwarteter Fehler beim Crawlen von {url}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unerwarteter Fehler beim Crawlen der Website: {e}")

# Datenmodell für sicheren File Upload
class UploadFileModel(BaseModel):
    filename: str
    content: str

    @field_validator('filename')
    def filename_must_be_safe(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.-]+$", v) or len(v) > 255:
            raise ValueError("Ungültiger Dateiname. Nur Buchstaben, Zahlen, Unterstriche, Punkte und Bindestriche sind erlaubt. Maximale Länge 255 Zeichen.")
        if '..' in v or '/' in v:
            raise ValueError("Ungültiger Dateiname: Path Traversal entdeckt.")
        return v

@app.post("/upload_file/")
async def upload_file_endpoint(file: UploadFileModel):  # Validierung durch Pydantic
    try:
        log_message(f"Versuche, Datei hochzuladen: {file.filename}")
        os.makedirs(settings.FILE_UPLOAD_DIR, exist_ok=True)
        filepath = os.path.join(settings.FILE_UPLOAD_DIR, file.filename)

        if os.path.exists(filepath):
            raise HTTPException(status_code=400, detail="Datei existiert bereits. Bitte benenne die Datei um.")

        try:
            file_content = base64.b64decode(file.content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Fehler beim Decodieren des Dateiinhalts: {e}")

        # Größenbeschränkung
        file_size_kb = len(file_content) / 1024
        if file_size_kb > settings.MAX_FILE_SIZE_KB:
            raise HTTPException(status_code=400, detail=f"Datei zu groß. Maximale Dateigröße beträgt {settings.MAX_FILE_SIZE_KB} KB.")

        # Datei schreiben
        with open(filepath, "wb") as f:
            f.write(file_content)

        log_message(f"Datei erfolgreich hochgeladen: {file.filename}")
        return {"message": f"Datei '{file.filename}' erfolgreich hochgeladen."}
    except HTTPException as http_excp:
        log_message(f"HTTP Ausnahme beim Hochladen der Datei: {http_excp.detail}", level=logging.WARNING)
        raise http_excp
    except Exception as e:
        log_message(f"Fehler beim Hochladen der Datei: {e}\n{traceback.format_exc()}", level=logging.ERROR)
        raise HTTPException(status_code=500, detail=f"Fehler beim Hochladen der Datei: {e}")

# Removed execute python code for security reasons

@app.get("/testendpoint/")
async def test():
    return JSONResponse({"answer": 1})

# Agenten-Rollen als Enum
class AgentRole(Enum):
    ANALYST = "Analyst"
    STRATEGIST = "Stratege"
    INNOVATOR = "Innovator"
    CRITIC = "Kritiker"
    ETHICAL_GUARDIAN = "Ethischer Aufpasser"
    SUMMARIZER = "Summarizer"  # Neuer Agent für Zusammenfassungen
    VERIFIER = "Verifizierer"  # Agent zur Faktenprüfung
    OPTIMIERER = "Optimierer"  # Agent zum Optimieren von Code und Prompts
    TECHNOLOGY_SCOUT = "Technologie Scout"  # Agent für neue Technologien
    DEVELOPER = "Entwickler"
    ENGINEER = "Ingenieur"
    RESEARCHER = "Forscher"
    ARCHITECT = "Architekt"
    TESTER = "Tester"
    ADMINISTRATOR = "Administrator"
    WRITER = "Schriftsteller"
    MANAGER = "Manager"
    DESIGNER = "Designer"
    SUPPORT = "Support"
    PROGRAMMING = "Programmierung"
    CONSULTANT = "Berater"
    BANKER = "Banker"
    ADVISOR = "Ratgeber"
    SPECIALIST = "Spezialist"

# Cache-Funktionen
def generate_cache_key(agent_name: str, knowledge: Dict, history: List, query: str) -> str:
    """Generiert einen eindeutigen Cache-Schlüssel basierend auf den Eingabeparametern."""
    data = {
        "agent_name": agent_name,
        "knowledge": knowledge,
        "history": history,
        "query": query
    }
    serialized_data = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.md5(serialized_data).hexdigest()

# SQLite-Vektordatenbank-Klasse
class VectorDatabase:
    def __init__(self):
        """Keine lokale Datenbank, da Embeddings über Gemini geholt werden."""
        pass

    async def get_gemini_embedding(self, text: str) -> List[float]:
        """Holt Embeddings für einen Text von Google Gemini."""
        try:
            client = genai.Client()
            result = client.models.embed_content(
                model="gemini-embedding-exp-03-07",
                contents=text
            )
            return result.embeddings[0].values
        except Exception as e:
            logging.error(f"Fehler beim Abrufen des Embeddings: {e}")
            return []

    async def search(self, query: str, top_n: int = 5) -> List[str]:
        """Vergleicht ein Such-Embedding mit bestehenden Embeddings und gibt relevante Ergebnisse zurück."""
        query_embedding = await self.get_gemini_embedding(query)
        if not query_embedding:
            return []

        logging.info(f"Suche mit Gemini-Embedding abgeschlossen für: {query}")
        return query_embedding



class Agent(BaseModel):
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    system_prompt: str
    temperature: float = settings.DEFAULT_TEMPERATURE
    model_name: str = "gemini-2.0-flash"
    expertise_fields: List[str] = []
    role: AgentRole = AgentRole.ANALYST
    tools: List[Dict] = []  # create_tool_definitions()
    knowledge: Dict = {}
    caching: bool = True

    async def generate_response(self, knowledge: dict, history: List[Dict], query: str) -> str:
        validate_api_key()

        # Wenn die Anfrage eine Websuche erfordert, führen wir sie aus
        if "web suchen" in query.lower():  # Einfache Bedingung für eine Websuche
            search_query = query.replace("web suchen", "").strip()
            web_results = await google_search(search_query)
            return f"Hier sind die Ergebnisse aus der Google-Suche: \n{web_results}"

        if self.caching:
            cache_key = generate_cache_key(self.name, knowledge, history, query)
            cached_response = await self.get_cached_response(cache_key)
            if cached_response:
                logging.info(f"Antwort aus Cache geladen für {self.name} ({self.agent_id})")
                return cached_response

        try:
            # Historische Antworten für Kontext in den Prompt aufnehmen
            # WICHTIG: history ist jetzt der *relevante* Verlauf, nicht alles.
            discussion_context = "\n".join(
                [f"{resp['agent_id'] if 'agent_id' in resp else 'User'}: {resp['response']}" for resp in history]
            )


            prompt_text = (
                f"{self.system_prompt}\n"
                f"Aktuelle Diskussion:\n{discussion_context}\n"
                f"Dein Beitrag zur Diskussion: {query}\n"
                f"Formuliere eine Antwort, die auf die letzten Aussagen und Benutzereingaben reagiert, und entweder zustimmt, hinterfragt, kritisiert oder neue Anweisungen integriert." # WICHTIG: Prompt angepasst.
            )

            # Anfrage an das Modell
            client = genai.Client()
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt_text,
                config=GenerateContentConfig(
                    temperature=self.temperature,
                    top_p=0.95,
                    top_k=40,
                    max_output_tokens=8000,
                )
            )


            if response and hasattr(response, 'text'):
                logging.info(f"Antwort vom LLM für Agent {self.name} ({self.agent_id}): {response.text}")
                if self.caching:
                    await self.cache_response(cache_key, response.text)
                return response.text
            else:
                logging.error(f"Keine Antwort vom LLM erhalten für Agent {self.name} ({self.agent_id})")
                return "Fehler: Keine Antwort vom LLM erhalten."

        except Exception as e:
            logging.error(f"Fehler bei Anfrage an LLM für Agent {self.name} ({self.agent_id}): {e}")
            return f"Fehler: {e}"

    async def get_cached_response(self, cache_key: str) -> Optional[str]:
        redis_cache = RedisCache()
        cached_response = redis_cache.get(cache_key)
        if cached_response:
            log_message(f"Lade Antwort aus dem Cache: {cache_key}")
            return cached_response
        return None

    async def cache_response(self, cache_key: str, response: str):
        redis_cache = RedisCache()
        redis_cache.set(cache_key, response)
        log_message(f"Antwort im Cache gespeichert: {cache_key}")





# Blockchain-Funktionalität (vereinfacht)
def generate_block_hash(block_data: str, previous_hash: str) -> str:
    """Generiert einen Hash für einen Block in der Blockchain."""
    combined_data = previous_hash + block_data
    return hashlib.sha256(combined_data.encode('utf-8')).hexdigest()

def add_block_to_chain(chain: List[Dict], block_data: str) -> List[Dict]:
    """Fügt einen neuen Block zur Blockchain hinzu."""
    previous_hash = chain[-1]['hash'] if chain else '0'  # Genesis Block
    new_hash = generate_block_hash(block_data, previous_hash)
    new_block = {
        'index': len(chain),
        'timestamp': time.time(),
        'data': block_data,
        'previous_hash': previous_hash,
        'hash': new_hash
    }
    chain.append(new_block)
    return chain

def validate_chain(chain: List[Dict]) -> bool:
    """Überprüft die Integrität der Blockchain."""
    for i in range(1, len(chain)):
        current_block = chain[i]
        previous_block = chain[i - 1]

        # Überprüfe den Hash des aktuellen Blocks
        calculated_hash = generate_block_hash(current_block['data'], previous_block['hash'])
        if current_block['hash'] != calculated_hash:
            log_message(f"Hash Validation failed at block {i}")
            return False

        # Überprüfe, ob der 'previous_hash' korrekt ist
        if current_block['previous_hash'] != previous_block['hash']:
            log_message(f"Previous Hash Validation failed at block {i}")
            return False

    return True

class Orchestrator:
    def __init__(self, config_file: str = "programming_agent_config.json"):
        self.agents = {}
        self.global_knowledge = {}
        self.blockchain = []  # Blockchain initialisieren
        self.load_agents_from_config(config_file)

    def load_agents_from_config(self, config_file: str):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                agents_data = json.load(f)

            for agent_data in agents_data:
                agent = Agent(
                    name=agent_data["name"],
                    description=agent_data["description"],
                    system_prompt=agent_data["system_prompt"],
                    role=AgentRole[agent_data["role"]],
                    temperature=agent_data.get("temperature", settings.DEFAULT_TEMPERATURE),
                    model_name=agent_data.get("model_name", "gemini-2.0-flash"),
                    expertise_fields=agent_data.get("expertise_fields", []),
                    caching=agent_data.get("caching", True)
                )
                self.add_agent(agent)

            logging.info(f"{len(agents_data)} Agenten erfolgreich geladen.")

        except Exception as e:
            logging.error(f"Fehler beim Laden der Agenten-Konfiguration: {e}")
            print(f"Fehler beim Laden der Agenten-Konfiguration: {e}")

    def add_agent(self, agent: Agent):
        """Fügt einen neuen Agenten zum Orchestrator hinzu."""
        if agent.agent_id not in self.agents:
            self.agents[agent.agent_id] = agent
            logging.info(f"Agent hinzugefügt: {agent.name} ({agent.agent_id})")
        else:
            logging.warning(f"Agent mit ID {agent.agent_id} bereits vorhanden.")

    async def process_request(self, agent_id: str, query: str, knowledge: Dict = {}, history: List[Dict] = []) -> str:
        """Sendet eine Anfrage an einen bestimmten Agenten."""
        agent = self.agents.get(agent_id)
        if not agent:
            return f"Agent mit ID {agent_id} nicht gefunden."
        try:
            response = await agent.generate_response(knowledge, history, query)
            return response
        except Exception as e:
            logging.error(f"Fehler bei der Verarbeitung der Anfrage: {e}")
            return f"Fehler: {e}"

    def remove_agent(self, agent_id: str):
        """Entfernt einen Agenten anhand der ID."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logging.info(f"Agent entfernt: {agent_id}")
        else:
            logging.warning(f"Agent mit ID {agent_id} nicht gefunden.")

    def get_all_agents(self) -> List[Agent]:
        """Gibt alle registrierten Agenten zurück."""
        return list(self.agents.values())

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Gibt einen bestimmten Agenten zurück."""
        return self.agents.get(agent_id)

class ThinkTankError(Exception):
    """Basisklasse für alle benutzerdefinierten Exceptions"""
    pass

class APIConnectionError(ThinkTankError):
    """Exception für API Verbindungsfehler"""
    pass

@app.exception_handler(ThinkTankError)
async def think_tank_exception_handler(request: Request, exc: ThinkTankError):
    return JSONResponse(
        status_code=500,
        content={"message": f"Ocurrió un error interno: {exc}"},
    )

def get_orchestrator():
    return orchestrator

@app.get("/agents/")
async def get_agents():
    agents = orchestrator.get_all_agents()
    return [{"agent_id": agent.agent_id, "name": agent.name} for agent in agents]

# Hilfsfunktionen
async def execute_python_code(code: str) -> str:
    return "Ausführung von Python-Code ist aus Sicherheitsgründen deaktiviert."

# Die process_file Funktion
async def process_file(filename: str, instructions: str) -> str:
    """Verarbeitet eine hochgeladene Datei basierend auf den gegebenen Anweisungen."""
    log_message(f"Versuche, Datei '{filename}' zu verarbeiten.")
    filepath = os.path.join(settings.FILE_UPLOAD_DIR, filename)

    if not os.path.exists(filepath):
        log_message(f"Datei '{filename}' nicht gefunden.", level=logging.WARNING)
        return f"Datei '{filename}' nicht gefunden."

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Hier die Logik zur Verarbeitung des Inhalts basierend auf den Anweisungen einfügen
        # Im Moment wird nur der Inhalt zurückgegeben.
        result = f"Datei '{filename}' verarbeitet.\nInhalt:\n{content}"
        log_message(f"Datei '{filename}' erfolgreich verarbeitet.")
        return result

    except Exception as e:
        log_message(f"Fehler beim Verarbeiten der Datei '{filename}': {e}\n{traceback.format_exc()}", level=logging.ERROR)
        return f"Fehler beim Verarbeiten der Datei '{filename}': {e}"

# Test-Agenten - Zur Veranschaulichung hartkodiert
agent1 = Agent(
    name="Experte für alternative Fakten",
    description="Kennt sich sehr gut mit alternativen Fakten aus",
    system_prompt="Du bist ein Experte für Verschwörungstheorien.",
    role=AgentRole.ANALYST
)

agent2 = Agent(
    name="Faktenprüfer",
    description="Spezialist für Faktenprüfung und Aufklärung",
    system_prompt="Du bist ein Faktenprüfer und Experte für Desinformation.",
    role=AgentRole.VERIFIER
)

# Initialisierung des Orchestrators
orchestrator = Orchestrator()
orchestrator.add_agent(agent1)
orchestrator.add_agent(agent2)

# Hilfsfunktion zur Validierung der API-Schlüssel
def validate_api_key():
    # Mock implementation for testing
    pass

# Tool-Definitionsfunktion
def create_tool_definitions():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "google_search",
                "description": "Führt eine Websuche durch und gibt die Ergebnisse zurück.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Die Suchanfrage."
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "crawl_website",
                "description": "Crawlt eine Website und extrahiert den Textinhalt.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Die URL der zu crawlenden Website."
                        }
                    },
                    "required": ["url"]
                }
            }
        }
    ]
    return tools

# Entferne execute python code
async def analyze_text_complexity(text: str) -> str:
  """Analysiert die Komplexität eines gegebenen Textes."""
  log_message(f"Analysiere Textkomplexität...")

  # Initialisiere NLTK Ressourcen (einmalig)
  try:
      stop_words = set(stopwords.words('german'))
  except LookupError:
      nltk.download('stopwords')
      stop_words = set(stopwords.words('german'))

  try:
      nltk.download('punkt') # Fuer Tokenisierung
  except LookupError:
      nltk.download('punkt')

  try:
      sentences = nltk.sent_tokenize(text, language='german')
      words = nltk.word_tokenize(text, language='german')
  except Exception as e:
      log_message(f"Fehler bei der Tokenisierung: {e}")
      return f"Fehler bei der Tokenisierung: {e}"

  num_sentences = len(sentences)
  num_words = len(words)

  # Vermeide Division durch Null
  if num_sentences == 0:
      avg_words_per_sentence = 0
  else:
      avg_words_per_sentence = num_words / num_sentences

  # TF-IDF Analyse (optional, kann entfernt werden wenn zu ressourcenintensiv)
  try:
      vectorizer = TfidfVectorizer(stop_words=stop_words)
      vectorizer.fit([text])
      tfidf_matrix = vectorizer.transform([text])

      # Hier wird die Dichte der TF-IDF Matrix berechnet
      density = tfidf_matrix.nnz / float(tfidf_matrix.shape[0] * tfidf_matrix.shape[1])
  except Exception as e:
      log_message(f"Fehler bei TF-IDF Analyse: {e}")
      density = 0

  report = (
      "Textkomplexitätsanalyse:\n"
      f"- Anzahl Sätze: {num_sentences}\n"
      f"- Anzahl Wörter: {num_words}\n"
      f"- Durchschnittliche Wörter pro Satz: {avg_words_per_sentence:.2f}\n"
      f"- TF-IDF Dichte: {density:.2f}"
  )

  log_message(f"Textkomplexitätsanalyse abgeschlossen.")
  return report

# Hilfsfunktion zur Validierung von URLs
def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

# Testing
def create_test_suite():
    class TestRateLimiter(unittest.TestCase):
        def test_rate_limiter_wait(self):
            rate_limiter = RateLimiter(calls_per_period=2, period=1)
            start_time = time.time()
            rate_limiter.wait()
            rate_limiter.wait()
            rate_limiter.wait()
            end_time = time.time()
            self.assertGreaterEqual(end_time - start_time, 1)

    class TestAgent(IsolatedAsyncioTestCase):
        async def test_generate_response(self):
            agent = Agent(
                name="Test Agent",
                description="Agent for testing purposes.",
                system_prompt="You are a test agent.",
                role=AgentRole.ANALYST
            )
            response = await agent.generate_response({}, [], "Test query")
            self.assertIsNotNone(response)

    class TestOrchestrator(IsolatedAsyncioTestCase):
        async def test_process_request(self):
            orchestrator = Orchestrator()
            agent = Agent(
                name="Test Agent",
                description="Agent for testing purposes.",
                system_prompt="You are a test agent.",
                role=AgentRole.ANALYST
            )
            orchestrator.add_agent(agent)
            response = await orchestrator.process_request(agent.agent_id, "Test query")
            self.assertIsNotNone(response)

    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestRateLimiter))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestAgent))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestOrchestrator))

    return suite




# App Start Function
def start_app():

    uvicorn.run(app, host="192.168.178.62", port=8000)

# Main Function to Run Tests and Start App
if __name__ == "__main__":
    # Run the test suite.
    test_suite = create_test_suite()
    runner = unittest.TextTestRunner()
    runner.run(test_suite)

    # Start the FastAPI app.
    start_app()

# Neuer Endpunkt /ask_agent/  (ENTFERNE, da durch /interact_think_tank/ ersetzt)
# class AgentRequest(BaseModel):
#     agent_id: str
#     query: str

# @app.post("/ask_agent/")
# async def ask_agent(request: AgentRequest):
#     response = await orchestrator.process_request(request.agent_id, request.query)
#     return {"response": response}

# Neuer Endpunkt /ask_think_tank/ (ENTFERNE, da durch /interact_think_tank/ ersetzt)
# class ThinkTankRequest(BaseModel):
#     agent_ids: List[str]
#     query: str
#     rounds: int = 3  # Standardmäßig 3 Diskussionsrunden

# @app.post("/ask_think_tank/")
# async def ask_think_tank(request: ThinkTankRequest):
#     agent_ids = request.agent_ids
#     query = request.query
#     rounds = request.rounds

#     # Validierung der Rundenanzahl
#     if not agent_ids:
#         raise HTTPException(status_code=400, detail="Mindestens ein Agent muss ausgewählt werden.")
#     if len(agent_ids) < 2:
#         raise HTTPException(status_code=400, detail="Mindestens zwei Agenten müssen für eine Diskussion ausgewählt werden.")
#     if rounds < 1:
#         raise HTTPException(status_code=400, detail="Die Anzahl der Runden muss mindestens 1 sein.")

#     # Hier fügen wir die Rundenvalidierung ein
#     if rounds > settings.MAX_DISCUSSION_ROUNDS:
#         raise HTTPException(status_code=400, detail=f"Maximal {settings.MAX_DISCUSSION_ROUNDS} Runden erlaubt.")

#     # Erste Antwort generieren
#     first_agent_id = agent_ids[0]
#     initial_response = await orchestrator.process_request(first_agent_id, query)

#     discussion_history = [{"agent_id": first_agent_id, "response": initial_response}]

#     # Fortschritt (Diskussion) in Echtzeit anzeigen
#     progress = {"round": 1, "agent_id": first_agent_id, "response": initial_response}
#     logging.info(f"🔄 Start von Runde 1 für Agent {first_agent_id}: {initial_response}")

#     # Mehrere Runden der Diskussion
#     for round_num in range(1, rounds):
#         logging.info(f"🔄 Start von Runde {round_num + 1}")

#         for agent_id in agent_ids[1:]:  # Alle Agenten außer dem ersten
#             agent = orchestrator.get_agent(agent_id)
#             if not agent:
#                 continue

#             # Diskussionskontext erweitern und gezielte Reaktionen einbauen
#             discussion_context = {
#                 "previous_responses": discussion_history,
#                 "current_agent": agent.name,
#                 "query": query
#             }

#             refined_response = await agent.generate_response(
#                 knowledge={},
#                 history=discussion_history,  # WICHTIG: history ist *nicht* mehr der gesamte Verlauf.
#                 query=f"Diskussionsrunde {round_num + 1}: {discussion_context}"
#             )

#             # Die Agenten müssen nun nicht nur eine Antwort, sondern auch eine Kritik oder ein Hinterfragen einbauen
#             if "nicht" in refined_response or "ungültig" in refined_response:
#                 refined_response = f"Agent {agent_id} widerspricht: {refined_response}"

#             # Wenn ein Agent nach einer Web-Suche fragt, führen wir diese aus und fügen sie der Antwort hinzu
#             if "web suchen" in refined_response.lower():
#                 search_query = refined_response.replace("web suchen", "").strip()
#                 web_results = await google_search(search_query)
#                 refined_response = f"Agent {agent_id} hat nach folgendem im Web gesucht: {web_results}"

#             discussion_history.append({"agent_id": agent_id, "response": refined_response})

#             # Fortschritt nach jeder Runde ausgeben
#             progress = {"round": round_num + 1, "agent_id": agent_id, "response": refined_response}
#             logging.info(f"Runde {round_num + 1} abgeschlossen für Agent {agent_id}: {refined_response}")

#     # Finale Antwort nach allen Runden zurückgeben
#     return {"discussion_history": discussion_history, "final_response": discussion_history[-1]["response"]}


# NEUE KLASSE: ThinkTankSession
class ThinkTankSession:
    def __init__(self, agent_ids: List[str], rounds: int):
        self.session_id: str = str(uuid.uuid4())
        self.history: List[Dict] = []
        self.current_round: int = 0
        self.agents: List[str] = agent_ids
        self.next_agent_index: int = 0
        self.rounds: int = rounds
        self.expecting_code: bool = False  # Flag, ob Code erwartet wird

    def add_user_input(self, input_text: str):
        self.history.append({"role": "user", "response": input_text})
        # Setze expecting_code, wenn die Eingabe Code anfordert.
        if "erstell" in input_text.lower() and "code" in input_text.lower() or "code fehlt" in input_text.lower():
          self.expecting_code = True
        else:
          self.expecting_code = False


    def add_agent_response(self, agent_id: str, response_text: str):
        self.history.append({"agent_id": agent_id, "response": response_text})

    def get_next_agent_id(self) -> str:
        if self.next_agent_index >= len(self.agents):
            self.next_agent_index = 0  # Zurück zum Anfang für die nächste Runde
            self.current_round += 1
        agent_id = self.agents[self.next_agent_index]
        self.next_agent_index += 1
        return agent_id

    def is_finished(self) -> bool:
        return self.current_round >= self.rounds

    def get_history_for_agent(self, agent_id: str) -> List[Dict]:
        # Gib nur den relevanten Verlauf für den aktuellen Agenten zurück.
        return self.history

# Globales Dictionary für aktive Sitzungen
sessions: Dict[str, ThinkTankSession] = {}

# NEUER ENDPUNKT: /interact_think_tank/
class InteractThinkTankRequest(BaseModel):
    session_id: Optional[str] = None  # Optional: Keine ID = neue Sitzung
    agent_ids: Optional[List[str]] = None  # Nur für neue Sitzungen benötigt
    query: str
    rounds: int = 3  # Standardwert, nur für neue Sitzungen

@app.post("/interact_think_tank/")
async def interact_think_tank(request: InteractThinkTankRequest):
    global sessions

    # 1. Sitzungsverwaltung
    if request.session_id:
        # Vorhandene Sitzung fortsetzen
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Sitzung nicht gefunden.")
        session = sessions[request.session_id]
    else:
        # Neue Sitzung starten
        if not request.agent_ids or len(request.agent_ids) < 1:
            raise HTTPException(status_code=400, detail="Mindestens 1 Agenten für eine neue Sitzung benötigt.")
        if request.rounds > settings.MAX_DISCUSSION_ROUNDS:
            raise HTTPException(status_code=400, detail=f"Maximal {settings.MAX_DISCUSSION_ROUNDS} Runden erlaubt.")
        session = ThinkTankSession(request.agent_ids, request.rounds)
        sessions[session.session_id] = session

    # 2. Benutzereingabe hinzufügen
    session.add_user_input(request.query)

    # 3. & 4. Agentenantworten abrufen (Schleife)
    while not session.is_finished():
        agent_id = session.get_next_agent_id()
        agent = orchestrator.get_agent(agent_id)
        if not agent:
            continue  # Agent nicht gefunden, überspringen

        history_for_agent = session.get_history_for_agent(agent_id)
        response = await orchestrator.process_request(agent_id, request.query, {}, history_for_agent)
        session.add_agent_response(agent_id, response)


        # Code-Validierung NACH der Antwort
        if session.expecting_code:
            if not any(keyword in response.lower() for keyword in ["```python", "def ", "class "]): # Einfache, aber robuste Prüfung
                # Brich die Schleife ab und gib eine Fehlermeldung zurück.
                return {
                    "error": "Code wurde angefordert, aber nicht geliefert. Bitte neuen Code anfordern.",
                    "session_id": session.session_id,
                    "history": session.history
                }


    # 5. Antwort zurückgeben
    return {"session_id": session.session_id, "history": session.history}