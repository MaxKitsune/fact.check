console.log("Background-Skript (Firefox) gestartet");

// Nachrichten-Listener mit dem browser-API
browser.runtime.onMessage.addListener((request, sender) => {
    console.log("Nachricht erhalten:", request);

    if (request.action === "getActiveTabUrl") {
        // Verwende Promise-basierte Abfrage, um den aktiven Tab zu erhalten
        return browser.tabs.query({ active: true, currentWindow: true })
            .then((tabs) => {
                if (tabs.length > 0) {
                    return { url: tabs[0].url };
                } else {
                    return { error: "Kein aktiver Tab gefunden." };
                }
            })
            .catch((error) => {
                console.error("Fehler beim Abrufen des Tabs:", error);
                return { error: "Fehler beim Abrufen des Tabs" };
            });
    }

    if (request.action === "logRating") {
        console.log("User hat eine Bewertung abgegeben:", request.data);
        // Beispiel: Du könntest hier einen API-Aufruf starten.
        return Promise.resolve({ status: "Rating empfangen" });
    }

    // Standardantwort, falls keine passende Aktion gefunden wird
    return Promise.resolve({ status: "Unbekannte Aktion" });
});

// Optional: Listener für Tab-Aktualisierungen
browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete') {
        console.log("Tab aktualisiert:", tab.url);
    }
});
