// Globale Variablen
let aktuelleSitzung = null;  // Speichert die aktuelle session_id
let pollingInterval = null;  // Für das Polling-Intervall

// Funktion zum Anpassen der Breite des Dropdowns
function adjustDropdownWidth(width) {
    const dropdown = document.getElementById('agentenSelect');
    if (dropdown) {
        dropdown.style.width = width + 'px';
    }
}

// Lade Agenten dynamisch beim Start
window.onload = async function() {
    const agentenSelect = document.getElementById('agentenSelect');
    if (!agentenSelect) {
        console.error('Element mit der ID "agentenSelect" nicht gefunden.');
        return;
    }
    agentenSelect.innerHTML = '<option>Agenten werden geladen...</option>';
    adjustDropdownWidth(400);

    try {
        const response = await fetch('http://localhost:8000/agents/');
        if (!response.ok) {
            throw new Error(`HTTP-Fehler! Status: ${response.status}`);
        }
        const agenten = await response.json();
        agentenSelect.innerHTML = '';

        if (agenten.length === 0) {
            agentenSelect.innerHTML = '<option>Keine Agenten verfügbar</option>';
            return;
        }

        // Option: Alle Agenten auswählen
        const alleAgentenOption = document.createElement('option');
        alleAgentenOption.value = 'alle';
        alleAgentenOption.textContent = 'Alle Agenten auswählen';
        agentenSelect.appendChild(alleAgentenOption);

        agenten.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.agent_id;
            // Falls Expertise-Felder vorhanden sind, diese zusammenfassen
            const expertiseFields = agent.expertise_fields && agent.expertise_fields.length > 0
                ? agent.expertise_fields.join(', ')
                : 'Keine Expertise-Felder verfügbar';
            option.textContent = `${agent.name} - ${agent.description} | Expertise: ${expertiseFields}`;
            agentenSelect.appendChild(option);
        });

    } catch (error) {
        console.error('Fehler beim Laden der Agenten:', error);
        agentenSelect.innerHTML = '<option>Fehler beim Laden der Agenten</option>';
    }
};

// Funktion, um eine neue Sitzung zu starten (Frage senden)
async function frageSenden() {
    const agentenSelect = document.getElementById('agentenSelect');
    const frage = document.getElementById('frage').value;
    const roundsInput = document.getElementById('rounds');
    const antwortDiv = document.getElementById('antwort');

    if (!agentenSelect || !roundsInput || !antwortDiv) {
        alert("Wichtige Elemente wurden nicht gefunden!");
        return;
    }

    let agent_ids = Array.from(agentenSelect.selectedOptions).map(option => option.value);
    if (agent_ids.includes('alle')) {
        // Wenn "Alle Agenten auswählen" gewählt ist, wird agent_ids als null gesendet
        agent_ids = null;
    }

    const rounds = parseInt(roundsInput.value);

    if ((!agent_ids || (Array.isArray(agent_ids) && agent_ids.length === 0)) &&
         !agentenSelect.querySelector('option[value="alle"]:checked')) {
        alert("Bitte wähle mindestens einen Agenten oder 'Alle Agenten auswählen'!");
        return;
    }
    if (!frage) {
        alert("Bitte stelle eine Frage!");
        return;
    }
    if (isNaN(rounds) || rounds <= 0) {
        alert("Bitte gib eine gültige Anzahl an Runden an (muss eine positive Zahl sein)!");
        return;
    }

    antwortDiv.innerHTML = "<strong>Diskussion startet...</strong><br>";

    const requestBody = {
        agent_ids: agent_ids, // Entweder null oder spezifische IDs
        query: frage,
        rounds: rounds,
        exit_session: false  // Für den Start einer Sitzung
    };

    try {
        const response = await fetch('http://localhost:8000/interact_think_tank/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorDetails = await response.json();
            antwortDiv.innerHTML = `<strong>Fehler beim Starten der Diskussion:</strong><br>${errorDetails.detail || response.statusText}`;
            return;
        }

        const data = await response.json();
        aktuelleSitzung = data.session_id;
        // Starte Polling nach dem Start einer neuen Sitzung
        startPolling(aktuelleSitzung);
        displayAntwort(data, antwortDiv); // Zeige die initiale Antwort

    } catch (error) {
        antwortDiv.innerHTML = '<strong>Fehler:</strong> ' + error.message;
        console.error("Fehler beim Senden der Anfrage:", error);
    }
}

// Funktion für Folgeanweisungen (ohne Neustart des Pollings)
async function folgeAnweisungSenden() {
    const folgeFrage = document.getElementById('folgeFrage').value;
    const antwortDiv = document.getElementById('antwort');

    if (!aktuelleSitzung) {
        alert("Keine aktive Sitzung gefunden. Bitte starte zuerst eine neue Diskussion.");
        return;
    }
    if (!folgeFrage) {
        alert("Bitte gib eine Folgeanweisung ein!");
        return;
    }

    antwortDiv.innerHTML = "<strong>Verarbeite Folgeanweisung...</strong><br>";

    const requestBody = {
        session_id: aktuelleSitzung,
        query: folgeFrage,
        exit_session: false
    };

    try {
        const response = await fetch('http://localhost:8000/interact_think_tank/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorDetails = await response.json();
            antwortDiv.innerHTML = `<strong>Fehler bei der Folgeanweisung:</strong><br>${errorDetails.detail || response.statusText}`;
            return;
        }

        const data = await response.json();
        // Polling läuft bereits – nur die Antwort aktualisieren
        displayAntwort(data, antwortDiv);
        document.getElementById('folgeFrage').value = '';

    } catch (error) {
        antwortDiv.innerHTML = '<strong>Fehler:</strong> ' + error.message;
        console.error("Fehler beim Senden der Folgeanweisung:", error);
    }
}

// Funktion zum Beenden der Sitzung
async function beendeSitzung() {
    const antwortDiv = document.getElementById('antwort');
    if (!aktuelleSitzung) {
        alert("Keine aktive Sitzung gefunden!");
        return;
    }
    const requestBody = {
        session_id: aktuelleSitzung,
        query: "",      // Kein neuer Input
        exit_session: true  // Flag zum Beenden der Sitzung
    };

    try {
        const response = await fetch('http://localhost:8000/interact_think_tank/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorDetails = await response.json();
            antwortDiv.innerHTML = `<strong>Fehler beim Beenden der Sitzung:</strong><br>${errorDetails.detail || response.statusText}`;
            return;
        }

        const data = await response.json();
        antwortDiv.innerHTML = `<strong>Sitzung beendet:</strong><br>${JSON.stringify(data.history)}`;
        aktuelleSitzung = null;
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    } catch (error) {
        antwortDiv.innerHTML = '<strong>Fehler:</strong> ' + error.message;
        console.error("Fehler beim Beenden der Sitzung:", error);
    }
}

// Polling-Funktion zum regelmäßigen Abruf des aktuellen Sitzungsverlaufs
function startPolling(session_id) {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    pollingInterval = setInterval(async () => {
        if (!aktuelleSitzung) {
            clearInterval(pollingInterval);
            return;
        }
        try {
            const requestBody = {
                session_id: session_id,
                query: "",          // Kein neuer Input, nur Statusabfrage
                exit_session: false // Nicht beenden
            };
            const response = await fetch('http://localhost:8000/interact_think_tank/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            if (!response.ok) {
                console.error(`Fehler beim Polling: HTTP-Status ${response.status}`);
                return;
            }
            const data = await response.json();
            // Aktualisiere den Antwortbereich mit dem aktuellen Verlauf
            displayAntwort(data, document.getElementById('antwort'));
            // Prüfe, ob die Sitzung beendet wurde (Backend gibt evtl. eine Nachricht zurück)
            if (data.message && data.message.indexOf("Sitzung beendet") !== -1) {
                clearInterval(pollingInterval);
                pollingInterval = null;
                aktuelleSitzung = null;
                console.log("Sitzung abgeschlossen (Polling gestoppt).");
            }
        } catch (error) {
            console.error("Fehler beim Polling:", error);
        }
    }, 2000); // Alle 2 Sekunden
    console.log(`Polling für Sitzung ${session_id} gestartet.`);
}

// Funktion zur Anzeige des Diskussionsverlaufs
function displayAntwort(data, antwortDiv) {
    let discussionText = "<strong>Diskussionsverlauf:</strong><br><br>";
    data.history.forEach((entry) => {
        if (entry.role === "user") {
            discussionText += `<b>👤 Du:</b> ${entry.response}<br><br>`;
        } else if (entry.agent_id) {
            // Hier wird der agent_id angezeigt. Falls du zusätzlich agent_name vom Server erhältst, kannst du diesen nutzen.
            discussionText += `🔹 <b>Agent ${entry.agent_id}:</b> ${entry.response}<br><br>`;
        }
    });
    if (data.error) {
        discussionText += `<hr><strong style="color:red;">⚠️ Fehler:</strong> ${data.error}`;
    }
    antwortDiv.innerHTML = discussionText;
    antwortDiv.scrollTop = antwortDiv.scrollHeight;
}
