```markdown
# 🤖 Think Tank: KI-Agenten-Orchestrierungssystem

Willkommen beim Think Tank, einem fortschrittlichen System zur Orchestrierung von KI-Agenten! Dieses Handbuch führt dich durch die Installation, Konfiguration und Verwendung des Systems, egal ob du ein Anfänger oder ein erfahrener Entwickler bist.

## Inhaltsverzeichnis

1.  [Überblick](#überblick)
2.  [Installation](#installation)
    *   [Voraussetzungen](#voraussetzungen)
    *   [Schritt-für-Schritt-Anleitung](#schritt-für-schritt-anleitung)
3.  [Konfiguration](#konfiguration)
    *   [Globale Einstellungen](#globale-einstellungen)
    *   [Agentenkonfiguration](#agentenkonfiguration)
        *   [Agenten-Rollen (AgentRole)](#agenten-rollen-agentrole)
4.  [Verwendung](#verwendung)
    *   [Admin-Panel](#admin-panel)
        *   [Globale Einstellungen bearbeiten](#globale-einstellungen-bearbeiten)
        *   [Agenten verwalten](#agenten-verwalten)
            *  [Agenten hinzufügen](#agenten-hinzufügen)
            *   [Agenten bearbeiten/löschen](#agenten-bearbeitenlöschen)
    *   [Interaktion mit dem Think Tank](#interaktion-mit-dem-think-tank)
    *  [Websuchen](#websuchen)
5.  [Erweiterte Funktionen](#erweiterte-funktionen)
    *   [Caching](#caching)
    *   [Rate Limiting](#rate-limiting)
    *   [Sichere Sandbox-Umgebung](#sichere-sandbox-umgebung)
    *   [Datei-Upload und -Verarbeitung](#datei-upload-und--verarbeitung)
    *   [Textanalyse](#textanalyse)
    *   [Blockchain (vereinfacht)](#blockchain-vereinfacht)
6.  [API-Endpunkte](#api-endpunkte)
7.  [Testen](#testen)
8.  [Fehlerbehebung](#fehlerbehebung)
9.  [Sicherheitshinweise](#sicherheitshinweise)
10. [Beitragen](#beitragen)
11. [Lizenz](#lizenz)

## 1. <a name="überblick"></a>Überblick

Think Tank ist ein System, das es dir ermöglicht, mehrere KI-Agenten zu erstellen, zu konfigurieren und zu orchestrieren. Diese Agenten können:

*   Spezifische Rollen und Fachgebiete haben.
*   Miteinander interagieren, um komplexe Probleme zu lösen.
*   Externe Ressourcen wie Webseiten und Dateien nutzen.
*   Aufgaben wie Websuchen, Textanalysen und mehr durchführen.
*   Über ein benutzerfreundliches Admin-Panel verwaltet werden.

Das System ist modular aufgebaut, sodass du es leicht erweitern und an deine Bedürfnisse anpassen kannst.

## 2. <a name="installation"></a>Installation

### 2.1 <a name="voraussetzungen"></a>Voraussetzungen

*   Python 3.7+
*   pip (Python-Paketmanager)
*   Git (optional, für einfaches Klonen)
*   Google Gemini API Key
*   Redis (optional, für verbessertes Caching)

### 2.2 <a name="schritt-für-schritt-anleitung"></a>Schritt-für-Schritt-Anleitung

1.  **Repository klonen (oder herunterladen):**

    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```
    Wenn du Git nicht verwendest, lade das Projekt als ZIP-Datei herunter und entpacke es.

2.  **Virtuelle Umgebung erstellen (empfohlen):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Für Linux/macOS
    venv\Scripts\activate  # Für Windows
    ```
    Eine virtuelle Umgebung isoliert die Projektabhängigkeiten.

3.  **Abhängigkeiten installieren:**

    ```bash
    pip install -r requirements.txt
    ```
    Dies installiert alle benötigten Bibliotheken, die in der `requirements.txt`-Datei aufgelistet sind.

4. **Google Gemini API einrichten**
    ```bash
    export GEMINI_API_KEY="dein-api-schlüssel"
    ```

5. **NLTK-Daten herunterladen:**

   Im Python-Interpreter:

   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('stopwords')
   ```

   Dies lädt die benötigten Ressourcen für die Textverarbeitung herunter.

6.  **Starte die Anwendung:**

    ```bash
    python main.py
    ```
    Die Anwendung sollte nun unter `http://127.0.0.1:8001` (Admin-Panel) erreichbar sein.  Die Interaktions-URL ist `http://192.168.178.62:8000` (oder deine konfigurierte IP-Adresse und Port).

## 3. <a name="konfiguration"></a>Konfiguration

### 3.1 <a name="globale-einstellungen"></a>Globale Einstellungen

Du kannst die globalen Einstellungen des Think Tanks über das Admin-Panel (`/admin/settings`) oder direkt in der Datei `global_settings.json` anpassen.  Hier sind einige der wichtigsten Einstellungen:

*   `DEFAULT_TEMPERATURE`: Steuert die "Kreativität" der KI-Antworten (0.0 = deterministisch, 1.0 = sehr kreativ).
*   `DEFAULT_TOP_P`, `DEFAULT_TOP_K`:  Weitere Parameter zur Feinabstimmung der KI-Modelle.
*   `AGENT_CONFIG_FILE`:  Der Pfad zur JSON-Datei, in der die Agentenkonfigurationen gespeichert sind.
*   `MAX_CONCURRENT_REQUESTS`:  Die maximale Anzahl gleichzeitiger Anfragen an die KI-API.
*   `SANDBOX_TIMEOUT`:  Zeitlimit für die Ausführung von Code in der Sandbox (in Sekunden).
*   `WEB_CRAWLING_TIMEOUT`:  Zeitlimit für das Abrufen von Webseiten (in Sekunden).
*   `MAX_FILE_SIZE_KB`:  Maximale Größe für hochgeladene Dateien.
*  `REDIS_HOST`, `REDIS_PORT`:  Einstellungen für die optionale Redis-Verbindung.
* `MAX_DISCUSSION_ROUNDS`: Maximale Anzahl der Interaktionsrunden zwischen Agenten.

**Wichtig:** Nach Änderungen an den globalen Einstellungen musst du den Server neu starten, damit die Änderungen wirksam werden.

### 3.2 <a name="agentenkonfiguration"></a>Agentenkonfiguration

Agenten werden in der Datei definiert, die in `settings.AGENT_CONFIG_FILE` angegeben ist (standardmäßig `programming_agent_config.json`).  Jeder Agent hat folgende Eigenschaften:

*   `name`:  Ein eindeutiger Name für den Agenten.
*   `description`:  Eine Beschreibung der Fähigkeiten und des Zwecks des Agenten.
*   `system_prompt`:  Eine Anweisung, die das grundlegende Verhalten und die "Persönlichkeit" des Agenten definiert.
*   `temperature`: (Optional) Eine agentspezifische Temperatur, die die globale Einstellung überschreibt.
*   `role`:  Die Rolle des Agenten (siehe [Agenten-Rollen](#agenten-rollen-agentrole)).
* `model_name`: Das zu verwendende KI-Modell.
* `expertise_fields`: Eine optionale Liste von Fachgebieten.
* `caching`: Gibt an, ob Antworten für diesen Agenten gecacht werden sollen.

**Beispielhafte Agentenkonfiguration (`programming_agent_config.json`):**

```json
[
  {
    "name": "Analyst",
    "description": "Ein Agent, der Daten analysiert und Schlussfolgerungen zieht.",
    "system_prompt": "Du bist ein erfahrener Datenanalyst. Analysiere die gegebenen Informationen und ziehe fundierte Schlussfolgerungen.",
    "role": "ANALYST",
    "temperature": 0.7
  },
  {
    "name": "Faktenprüfer",
    "description": "Ein Agent, der Informationen auf ihren Wahrheitsgehalt überprüft.",
    "system_prompt": "Du bist ein unbestechlicher Faktenprüfer. Überprüfe die gegebenen Informationen und stelle fest, ob sie korrekt sind.",
    "role": "VERIFIER"
  }
]
```

#### 3.2.1 <a name="agenten-rollen-agentrole"></a>Agenten-Rollen (AgentRole)

Die `AgentRole`-Enum definiert vordefinierte Rollen, die du deinen Agenten zuweisen kannst.  Diese helfen, die Verantwortlichkeiten und das Verhalten der Agenten zu strukturieren.  Du kannst die Enum um eigene Rollen erweitern.  Hier sind die Standardrollen:

```python
class AgentRole(Enum):
    ANALYST = "Analyst"
    STRATEGIST = "Stratege"
    INNOVATOR = "Innovator"
    CRITIC = "Kritiker"
    ETHICAL_GUARDIAN = "Ethischer Aufpasser"
    SUMMARIZER = "Summarizer"
    VERIFIER = "Verifizierer"
    OPTIMIERER = "Optimierer"
    TECHNOLOGY_SCOUT = "Technologie Scout"
    # ... (weitere Rollen)
```

## 4. <a name="verwendung"></a>Verwendung

### 4.1 <a name="admin-panel"></a>Admin-Panel

Das Admin-Panel ist die zentrale Schnittstelle zur Verwaltung des Think Tanks. Du erreichst es unter `http://127.0.0.1:8001/admin` (oder der von dir konfigurierten Adresse).

#### 4.1.1 <a name="globale-einstellungen-bearbeiten"></a>Globale Einstellungen bearbeiten

Gehe zu `/admin/settings`, um die globalen Einstellungen anzupassen.  Speichere deine Änderungen mit dem "Einstellungen aktualisieren"-Button.

#### 4.1.2 <a name="agenten-verwalten"></a>Agenten verwalten

Unter `/admin/agents` siehst du eine Liste aller konfigurierten Agenten.

##### 4.1.2.1 <a name="agenten-hinzufügen"></a>Agenten hinzufügen

Klicke auf "Neuen Agenten hinzufügen" (`/admin/agents/new`), um einen neuen Agenten zu erstellen.  Fülle das Formular aus und klicke auf "Agent hinzufügen".

##### 4.1.2.2 <a name="agenten-bearbeitenlöschen"></a>Agenten bearbeiten/löschen

Klicke auf den Namen eines Agenten in der Liste, um seine Einstellungen zu bearbeiten (`/admin/agents/{agent_id}`).  Speichere Änderungen mit "Agent aktualisieren".  Es gibt derzeit keine explizite Löschfunktion im Frontend, aber du kannst Agenten direkt aus der `programming_agent_config.json` Datei entfernen (Serverneustart erforderlich).

### 4.2 <a name="interaktion-mit-dem-think-tank"></a>Interaktion mit dem Think Tank

Die Hauptinteraktion mit dem Think Tank erfolgt über die Startseite der Anwendung (`http://192.168.178.62:8000`). Hier ist der Ablauf:

1.  **Agenten auswählen:** Wähle einen oder mehrere Agenten aus der Dropdown-Liste aus.
2.  **Frage/Anweisung eingeben:** Gib deine Frage oder Anweisung in das Textfeld ein.
3.  **Rundenanzahl festlegen:** Bestimme, wie viele Interaktionsrunden die Agenten durchlaufen sollen.
4.  **"Think Tank starten" klicken:**  Dies initiiert eine neue Diskussionssitzung.
5. **Neue Anweisung senden** Dies setzt eine neue Interaktionsrunde, für die Session fort.
6.  **Diskussionsverlauf und Antwort anzeigen:** Der Verlauf der Diskussion und die finale Antwort werden angezeigt.

**Wichtige Hinweise zur Interaktion:**

*   **Sitzungsbasiert:** Jede Interaktion wird durch eine eindeutige Sitzungs-ID (`session_id`) verwaltet.
*   **Mehrere Runden:** Die Agenten interagieren in mehreren Runden miteinander, basierend auf ihren Rollen und der vorherigen Diskussion.
*  **Code-Validierung:** Wenn Code angefordert, aber nicht geliefert wurde, wird die aktuelle Sitzung mit einem Fehler beendet.

### 4.3 <a name="websuchen"></a>Websuchen

Um eine Websuche auszulösen, füge den Befehl "web suchen: " gefolgt von deiner Suchanfrage in die Benutzereingabe ein. Zum Beispiel:

```
web suchen: Aktuelle Nachrichten zur KI-Entwicklung
```

Der Think Tank wird dann die Google-Suche verwenden, um relevante Informationen abzurufen.

## 5. <a name="erweiterte-funktionen"></a>Erweiterte Funktionen

### 5.1 <a name="caching"></a>Caching

Das System verwendet ein zweistufiges Caching-System (Redis und SQLite), um die Leistung zu verbessern und die API-Nutzung zu reduzieren.

*   **Redis:** Für schnellen Zugriff auf häufig verwendete Daten (optional, erfordert eine Redis-Installation).
*   **SQLite:** Als Fallback, falls Redis nicht verfügbar ist.

Du kannst das Caching für einzelne Agenten in der Agentenkonfiguration aktivieren oder deaktivieren.  Cache-Schlüssel werden basierend auf dem Agentennamen, dem Wissen, dem Verlauf und der Anfrage generiert.

### 5.2 <a name="rate-limiting"></a>Rate Limiting

Ein `RateLimiter` schützt die Google GenAI API vor Überlastung.  Die Standardeinstellungen (Anrufe pro Zeitraum und Zeitraum) sind in den globalen Einstellungen konfigurierbar.

### 5.3 <a name="sichere-sandbox-umgebung"></a>Sichere Sandbox-Umgebung

Die `safe_execution_environment`-Funktion (derzeit deaktiviert) sollte eine sichere Ausführung von potenziell unsicherem Code ermöglichen.  Sie verwendet `subprocess` und `signal`, um den Code in einem separaten Prozess mit einem Timeout auszuführen.  **Diese Funktion ist derzeit aus Sicherheitsgründen deaktiviert.**

### 5.4 <a name="datei-upload-und--verarbeitung"></a>Datei-Upload und -Verarbeitung

Du kannst Dateien über den `/upload_file/`-Endpunkt hochladen.

*   **Sicherheitsvorkehrungen:**
    *   Validierung des Dateinamens, um Path-Traversal-Angriffe zu verhindern.
    *   Begrenzung der Dateigröße.
    *   Überprüfung, ob die Datei bereits existiert.
*   **Verarbeitung:** Die `process_file`-Funktion kann verwendet werden, um die hochgeladene Datei basierend auf bestimmten Anweisungen zu verarbeiten. Derzeit gibt sie jedoch nur den Inhalt der Datei zurück.

### 5.5 <a name="textanalyse"></a>Textanalyse

Die `analyze_text_complexity`-Funktion bietet eine grundlegende Textanalyse, einschließlich:

*   Anzahl der Sätze und Wörter.
*   Durchschnittliche Wörter pro Satz.
*   TF-IDF-Dichte (Term Frequency-Inverse Document Frequency) – ein Maß für die Wichtigkeit von Wörtern im Text.

### 5.6 <a name="blockchain-vereinfacht"></a>Blockchain (vereinfacht)

Das System enthält eine vereinfachte Blockchain-Implementierung zu Demonstrationszwecken.

*   **`generate_block_hash`:** Generiert einen Hash für einen Block.
*   **`add_block_to_chain`:** Fügt einen neuen Block zur Kette hinzu.
*   **`validate_chain`:** Überprüft die Integrität der Kette.

**Wichtiger Hinweis:** Diese Blockchain-Implementierung ist *nicht* für den produktiven Einsatz geeignet und dient nur zur Veranschaulichung.

## 6. <a name="api-endpunkte"></a>API-Endpunkte

Hier ist eine Übersicht der wichtigsten API-Endpunkte:

*   `/admin`:  Startseite des Admin-Panels.
*   `/admin/settings`:  Globale Einstellungen (GET und POST).
*   `/admin/agents`:  Agentenübersicht.
*   `/admin/agents/new`:  Neuen Agenten hinzufügen (GET und POST).
*   `/admin/agents/{agent_id}`:  Agenten bearbeiten (GET und POST).
*   `/upload_file/`:  Datei hochladen (POST).
*   `/interact_think_tank/`:  Interaktion mit dem Think Tank (POST).
* `/agents/`: Gibt eine Liste aller registrierten Agenten zurück (GET).
* `/testendpoint/`: Einfacher Testendpunkt (GET).

## 7. <a name="testen"></a>Testen

Das Projekt enthält eine Reihe von Unittests, die du mit folgendem Befehl ausführen kannst:

```bash
python main.py
```
Die Tests decken Teile des Rate Limiters, der Agenten, und des Orchestrators ab.

## 8. <a name="fehlerbehebung"></a>Fehlerbehebung

*   **Fehler beim Laden der Agentenkonfiguration:** Stelle sicher, dass die `programming_agent_config.json`-Datei (oder deine konfigurierte Datei) wohlgeformtes JSON enthält und dass alle erforderlichen Felder vorhanden sind.
*   **Verbindungsfehler zu Redis:** Überprüfe, ob Redis installiert ist und läuft und ob die `REDIS_HOST`- und `REDIS_PORT`-Einstellungen korrekt sind.
*   **Fehler beim Abrufen von Webseiten:** Stelle sicher, dass die URL gültig ist und dass keine Netzwerkprobleme vorliegen. Überprüfe auch das `WEB_CRAWLING_TIMEOUT`.
*   **Timeout-Fehler:** Wenn du Timeout-Fehler erhältst, erhöhe die `SANDBOX_TIMEOUT` oder `WEB_CRAWLING_TIMEOUT`-Werte.
* **Allgemeine Fehler**: Überprüfe die Logdatei (standardmäßig `think_tank.log`), in der detailliertere Fehlermeldungen protokolliert werden.

## 9. <a name="sicherheitshinweise"></a>Sicherheitshinweise

*   **API-Schlüssel:** Speichere deine API-Schlüssel *niemals* direkt im Code. Verwende Umgebungsvariablen oder sichere Konfigurationsdateien.
*   **Code-Ausführung:** Sei äußerst vorsichtig bei der Ausführung von Benutzercode. Die `execute_python_code`-Funktion ist aus gutem Grund deaktiviert. Aktiviere sie nur, wenn du die Risiken vollständig verstehst und geeignete Sicherheitsvorkehrungen getroffen hast.
*   **Datei-Uploads:** Validiere hochgeladene Dateien *immer* gründlich, um Sicherheitslücken zu vermeiden.
*  **Abhängigkeiten:** Halte deine Python-Pakete auf dem neuesten Stand, um Sicherheitslücken zu schließen.
* **HTTPS**: Verwende in einer Produktionsumgebung HTTPS, um die Kommunikation zu verschlüsseln.
* **Authentifizierung**: Erwäge die Implementierung einer Authentifizierung für das Admin-Panel, um unbefugten Zugriff zu verhindern.
* **Eingabevalidierung**: Validiere alle Benutzereingaben sorgfältig, um Injection-Angriffe zu verhindern.
* **Rate Limiting**: Implementiere ein Rate Limiting nicht nur für die API, sondern auch für andere Endpunkte, um Denial-of-Service-Angriffe zu verhindern.
* **Geheimnisse**: Speichere niemals sensible Daten wie Passwörter oder API-Schlüssel im Klartext in der Konfigurationsdatei oder im Code.

## 10. <a name="beitragen"></a>Beitragen

Beiträge zum Think Tank-Projekt sind willkommen! Wenn du Fehler findest, Verbesserungsvorschläge hast oder neue Funktionen hinzufügen möchtest, erstelle bitte einen Pull Request.

## 11. <a name="lizenz"></a>Lizenz

Dieses Projekt ist [Deine Lizenz]-lizenziert.

---
