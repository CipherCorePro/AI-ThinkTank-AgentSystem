
# 🧠 KI-Think Tank: Kollaborative KI-Agenten Plattform

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/IhrName/KI-ThinkTank)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-black.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)]()  <!-- Optional: Zeigen Sie die Testabdeckung an -->


**Ein Framework für dynamische, kollaborative Problemlösung mit spezialisierten KI-Agenten.**

[English Version](README_EN.md) | [Spanisch Version](README_ES.md)

## ✨ Übersicht

KI-Think Tank ist eine innovative Plattform, die es mehreren spezialisierten KI-Agenten ermöglicht, in einer kollaborativen Umgebung zusammenzuarbeiten, um komplexe Probleme zu lösen, Aufgaben zu erledigen und kreative Lösungen zu generieren.  Jeder Agent bringt einzigartige Fähigkeiten und Fachkenntnisse ein, und durch einen strukturierten Diskussionsprozess wird ein Konsens oder die optimale Lösung erarbeitet.

**Kernfunktionen:**

*   **Kollaborative Problemlösung:** Mehrere KI-Agenten arbeiten zusammen, um ein gemeinsames Ziel zu erreichen.
*   **Spezialisierte Agenten:** Jeder Agent verfügt über spezifische Rollen, Fachkenntnisse und Tools (z.B. Websuche, Codeausführung).
*   **Dynamische Diskussion:** Ein iterativer Prozess ermöglicht es den Agenten, Ideen auszutauschen, zu kritisieren, zu verfeinern und zu validieren.
*   **Modulare Architektur:** Einfaches Hinzufügen und Anpassen von Agenten und Tools.
*   **Sichere Ausführung:**  Codeausführung in einer streng kontrollierten Sandbox-Umgebung mit Timeout-Mechanismen.
*   **Caching:**  Zwischenspeicherung von Ergebnissen zur Verbesserung der Leistung und Reduzierung von API-Anfragen.
*   **Blockchain-Integration (optional):**  Manipulationssichere Protokollierung von Ergebnissen und Entscheidungen.
*   **RESTful API:** Einfache Integration mit anderen Anwendungen und Diensten.
*   **Admin-Panel:**  Eine webbasierte Benutzeroberfläche zur Konfiguration von Agenten, globalen Einstellungen und zur Überwachung des Systems.
*   **Umfangreiche Tests:**  Gewährleistung von Stabilität und Zuverlässigkeit durch Unit- und Integrationstests.
*   **Detailliertes Logging:**  Nachvollziehbarkeit von Aktionen und Fehlern.
* **Fallback-Mechanismus für Cache:** Redis mit SQL-Fallback, um Ausfallsicherheit zu gewährleisten.
* **HTTPException-Handling**: Benutzerdefinierte Exception-Klassen und Handler für eine robuste Fehlerbehandlung.

## 🚀 Installation

1.  **Repository klonen:**

    ```bash
    git clone https://github.com/IhrName/KI-ThinkTank.git
    cd KI-ThinkTank
    ```
2.  **Abhängigkeiten installieren** (vorzugsweise in einer virtuellen Umgebung):

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Oder venv\Scripts\activate unter Windows
    pip install -r requirements.txt
    ```
    Stellen Sie sicher, dass `nltk.download('stopwords')` und `nltk.download('punkt')` ausgeführt werden, um die erforderlichen NLTK-Ressourcen herunterzuladen. Sie können dies in einer Python-Shell tun.

3.  **Google Cloud API-Schlüssel konfigurieren:**
    *   Erstellen Sie einen API-Schlüssel für die Google Gemini API.
    *   Setzen Sie eine Umgebungsvariable `GEMINI_API_KEY` mit Ihrem Schlüssel:

    ```bash
    export GEMINI_API_KEY="Ihr-API-Schlüssel"
    ```
    Oder, fügen Sie Ihren Schlüssel der `.env` file hinzu

    ```
    GEMINI_API_KEY=Ihr-API-Schlüssel
    ```
4. **Redis installieren und starten** (optional, aber empfohlen):

    ```bash
    # Installationsanweisungen für Ihr Betriebssystem finden Sie unter https://redis.io/
    ```
5.  **Admin-Panel einrichten (optional):**

    *   Navigieren Sie zum `admin_panel`-Verzeichnis.
    *   Folgen Sie den Anweisungen in der `README.md` des Admin-Panels.

6.  **Anwendung starten:**

    ```bash
    python main.py
    ```

    Die Anwendung läuft standardmäßig auf Port 8000.  Das Admin-Panel ist separat auf Port 8001 verfügbar.

## 🛠️ Verwendung

### Interaktion mit dem Think Tank

Die Interaktion mit dem Think Tank erfolgt über die `/interact_think_tank/` API.  Sie können entweder eine neue Sitzung starten oder eine bestehende fortsetzen.

**Neue Sitzung starten:**

```http
POST /interact_think_tank/
Content-Type: application/json

{
  "agent_ids": ["agent_id_1", "agent_id_2", ...],
  "query": "Ihre Frage oder Anweisung",
  "rounds": 3  // Optional, Standardwert ist 3
}
```

*   `agent_ids`:  Eine Liste der IDs der Agenten, die an der Diskussion teilnehmen sollen.
*   `query`: Die Eingabeaufforderung oder Frage, die an den Think Tank gestellt wird.
*   `rounds`:  Die Anzahl der Diskussionsrunden (optional).

**Bestehende Sitzung fortsetzen:**

```http
POST /interact_think_tank/
Content-Type: application/json

{
  "session_id": "Ihre-Sitzungs-ID",
  "query": "Ihre nächste Anweisung oder Frage"
}
```

*   `session_id`: Die ID der Sitzung, die Sie fortsetzen möchten.
*   `query`:  Ihre nächste Eingabe.

**Antwort:**

```json
{
  "session_id": "eindeutige-sitzungs-id",
  "history": [
    {
      "role": "user",
      "response": "Benutzereingabe"
    },
    {
      "agent_id": "agent_id_1",
      "response": "Antwort des Agenten 1"
    },
    ...
  ],
  "error": null // Optional: Fehlerbeschreibung, falls aufgetreten
}
```

*   `session_id`: Die eindeutige ID der Sitzung.
*   `history`:  Der vollständige Verlauf der Diskussion, einschließlich Benutzer- und Agentenantworten.
*   `error`: Enthält eine Fehlermeldung, falls während der Verarbeitung ein Fehler aufgetreten ist.

### Agentenkonfiguration

Agenten werden über die Datei `programming_agent_config.json` (oder eine andere, in den Einstellungen angegebene Datei) konfiguriert.  Das Format ist:

```json
[
  {
    "name": "Agentenname",
    "description": "Kurze Beschreibung des Agenten",
    "system_prompt": "Detaillierte Anweisungen für den Agenten",
    "role": "ANALYST", // Eine der verfügbaren Rollen (siehe AgentRole Enum)
    "temperature": 0.7, // Optional: Überschreibt den Standardwert
    "model_name": "gemini-2.0-flash", //Optional: Überschreibt den Standardwert
    "expertise_fields": ["Programmierung", "Python"], // Optional
    "caching": true // Optional: Aktiviert/Deaktiviert das Caching für diesen Agenten
  },
  ...
]
```
Sie können Agenten auch dynamisch über das Admin-Panel hinzufügen, bearbeiten und entfernen.

### Tools

Agenten können Tools verwenden, um zusätzliche Funktionen auszuführen.  Derzeit unterstützte Tools sind:

*   **`google_search`:** Führt eine Websuche mit der Google Gemini API durch.
*   **`crawl_website`:**  Extrahiert Textinhalt von einer gegebenen URL.

Die Definition der Tools erfolgt innerhalb der `create_tool_definitions`-Funktion.  Agenten können in ihrer Konfiguration angeben, welche Tools sie verwenden möchten.

### Codeausführung (Deaktiviert)

Die Funktion zur Ausführung von Python-Code wurde aus Sicherheitsgründen *deaktiviert*.  Es gibt einen Platzhalter (`execute_python_code`), der jedoch immer eine Meldung zurückgibt, dass die Ausführung deaktiviert ist.

### Textanalyse (Komplexitätsanalyse)

Die `analyze_text_complexity`-Funktion bietet eine grundlegende Analyse der Komplexität eines Textes, einschließlich der Anzahl der Sätze, Wörter, durchschnittlichen Wörter pro Satz und einer TF-IDF-basierten Dichtemessung.

### Sicheres Hochladen von Dateien

Der `/upload_file/`-Endpunkt ermöglicht das sichere Hochladen von Dateien.  Es werden folgende Sicherheitsmaßnahmen ergriffen:

*   **Validierung des Dateinamens:**  Es werden nur sichere Dateinamen akzeptiert, um Path-Traversal-Angriffe zu verhindern.
*   **Größenbeschränkung:** Die Dateigröße ist auf `MAX_FILE_SIZE_KB` begrenzt.
*   **Inhaltsdekodierung:**  Der Dateiinhalt wird Base64-dekodiert.
*   **Verhinderung von Überschreiben:**  Wenn eine Datei mit demselben Namen bereits existiert, wird ein Fehler zurückgegeben.

### Blockchain (Vereinfacht)

Die Blockchain-Funktionalität ist *vereinfacht* und dient hauptsächlich der Demonstration.  Sie bietet grundlegende Funktionen zum Hinzufügen von Blöcken und zur Validierung der Kette.  Die Implementierung ist *nicht* für den produktiven Einsatz geeignet und sollte durch eine robuste Blockchain-Lösung ersetzt werden.

### Caching

Das System verwendet Redis für das Caching.  Wenn Redis nicht verfügbar ist, wird ein SQLite-basiertes Fallback verwendet.  Dies stellt sicher, dass das Caching auch dann funktioniert, wenn Redis ausfällt.  Die Cache-Schlüssel werden auf Basis der Eingabeparameter generiert, um eine eindeutige Identifizierung der Ergebnisse zu gewährleisten.

### Rate Limiting

Ein `RateLimiter` ist implementiert, um die Anzahl der API-Anfragen pro Zeiteinheit zu begrenzen. Dies ist wichtig, um die Ressourcen zu schonen und die Stabilität des Systems zu gewährleisten.

### Admin-Panel

Das Admin-Panel bietet eine webbasierte Oberfläche zur Verwaltung der Anwendung.  Es ist unter `/admin` erreichbar (standardmäßig auf Port 8001).  Die folgenden Funktionen sind verfügbar:

*   **Globale Einstellungen:**  Anpassung aller globalen Konfigurationsparameter.
*   **Agentenverwaltung:**  Anzeigen, Hinzufügen, Bearbeiten und Löschen von Agenten.

### Tests

Das Projekt enthält umfangreiche Unit- und Integrationstests, um die Funktionalität und Stabilität zu gewährleisten.  Die Tests können mit folgendem Befehl ausgeführt werden:

```bash
python main.py # Startet die App und führt die Tests aus.
```

### Fehlerbehandlung

Die Anwendung verwendet benutzerdefinierte Exceptions (`ThinkTankError`, `APIConnectionError`) und einen globalen Exception-Handler, um Fehler konsistent zu behandeln und aussagekräftige Fehlermeldungen zurückzugeben.

### Logging

Detailliertes Logging ist implementiert, um alle wichtigen Ereignisse, Aktionen und Fehler aufzuzeichnen.  Die Logs werden in der Datei `think_tank.log` gespeichert (oder einer anderen, in den Einstellungen angegebenen Datei).  Sensible Daten wie API-Schlüssel werden maskiert.

## 🤝 Mitwirken

Beiträge sind willkommen! Wenn Sie Verbesserungen oder neue Funktionen vorschlagen möchten, erstellen Sie bitte einen Pull Request. Bitte stellen Sie sicher, dass Ihr Code den folgenden Richtlinien entspricht:

*   **Code-Stil:**  Halten Sie sich an den PEP 8-Stil (Black wird verwendet).
*   **Tests:**  Schreiben Sie Unit-Tests für alle neuen Funktionen und Änderungen.
*   **Dokumentation:**  Aktualisieren Sie die Dokumentation (einschließlich dieser README-Datei), wenn erforderlich.

## 📝 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert – siehe die Datei [LICENSE](LICENSE) für Details.

## 📧 Kontakt

Bei Fragen oder Anmerkungen wenden Sie sich bitte an [Ihr Name/Ihre E-Mail-Adresse].

## 📚 Weiterführende Informationen

*   **FastAPI:** [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
*   **Google Gemini API:** [https://ai.google.dev/](https://ai.google.dev/)
*   **Redis:** [https://redis.io/](https://redis.io/)
*   **NLTK:** [https://www.nltk.org/](https://www.nltk.org/)
*   **Scikit-learn:** [https://scikit-learn.org/](https://scikit-learn.org/)
*   **Pydantic:** [https://docs.pydantic.dev/](https://docs.pydantic.dev/)
*   **Uvicorn:** [https://www.uvicorn.org/](https://www.uvicorn.org/)

## ⚠️ Haftungsausschluss

Dieses Projekt ist ein experimentelles Framework und sollte mit Vorsicht verwendet werden.  Die Entwickler übernehmen keine Verantwortung für Schäden, die durch die Verwendung dieser Software entstehen. Insbesondere ist zu beachten, dass KI-generierte Inhalte unvorhersehbar sein können und vor der Verwendung in kritischen Kontexten überprüft werden sollten. Die Codeausführungsfunktion wurde deaktiviert, und jegliche Versuche, sie zu reaktivieren, geschehen auf eigenes Risiko. Die Blockchain-Implementierung ist stark vereinfacht und sollte *nicht* als Grundlage für produktionsreife Anwendungen dienen.
```

