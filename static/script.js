let aktuelleSitzung = null;  // Speichert die session_id für weitere Anweisungen

// Funktion zum Anpassen der Breite des Dropdowns
function adjustDropdownWidth(width) {
    const dropdown = document.getElementById('agentenSelect');
    dropdown.style.width = width + 'px'; // Setze die Breite des Dropdowns
}

// Lade Agenten dynamisch beim Start
window.onload = async function() {
    const agentenSelect = document.getElementById('agentenSelect');
    agentenSelect.innerHTML = '<option>Agenten werden geladen...</option>';

    // Hier legen wir die Breite des Dropdowns fest (in px)
    adjustDropdownWidth(300); // Beispiel: Setzt die Breite auf 300px (kann angepasst werden)

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

            // Wenn expertise_fields vorhanden sind, diese anzeigen
            const expertiseFields = agent.expertise_fields && agent.expertise_fields.length > 0 
                ? agent.expertise_fields.join(', ')  // Expertise-Felder zusammenfügen
                : 'Keine Expertise-Felder verfügbar';  // Wenn keine Expertise-Felder existieren

            // Setze den Textinhalt der Option: Name, Beschreibung und Expertise-Felder
            option.textContent = `${agent.name} - ${agent.description} | Expertise: ${expertiseFields}`;
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
        alert("Bitte wähle mindestens ein Agenten!");
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

    if (data.error) {
        discussionText += `<hr><strong style="color:red;">⚠️ Fehler:</strong> ${data.error}`;
    } else {
        discussionText += `<hr><strong>Finale Antwort:</strong> ${data.history[data.history.length - 1].response}`;
    }

    antwortDiv.innerHTML = discussionText;
}
