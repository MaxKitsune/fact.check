console.log("Popup-Skript wird geladen");

document.addEventListener('DOMContentLoaded', () => {
    browser.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
        if (tabs.length > 0) {
            const currentUrl = new URL(tabs[0].url);

            // Extrahiert die Hauptdomain und Subordner
            const domainWithSubfolders = `${currentUrl.hostname}${currentUrl.pathname}`;
            const urlElement = document.getElementById('url');
            urlElement.innerText = domainWithSubfolders;

            const rating_up_text = document.getElementById("rating-up");
            const rating_down_text = document.getElementById("rating-down");

            fetch("https://db-factcheck.kitsunexoo.net/get-votes?url=" + encodeURIComponent(currentUrl.toString()), {
                method: "GET"
            })
                .then(response => response.json())
                .then(data => {
                    console.log(data);
                    console.log("Domain mit Subfoldern: " + domainWithSubfolders);
                    const result = data.find(item => item[0] === currentUrl.hostname && item[1] === currentUrl.pathname);

                    if (result) {
                        const upvotes = result[2];
                        const downvotes = result[3];

                        rating_up_text.innerText = upvotes;
                        rating_up_text.style.color = "#9AE19D";
                        rating_down_text.innerText = downvotes;
                        rating_down_text.style.color = "#c91e1e";
                    } else {
                        rating_up_text.innerText = 0;
                        rating_down_text.innerText = 0;
                    }
                })
                .catch(error => console.error('Fehler beim Abrufen der Daten:', error));


            /* if (domainWithSubfolders === "x.com/elonmusk") {
                rating_up.innerText = "0";
                rating_up.style.color = "#9AE19D";
                rating_down.innerText = "500";
                rating_down.style.color = "#c91e1e";
            } else {
                rating_up.innerText = "None";
                rating_down.innerText = "None";
            } */


            //Rating buttons
            document.getElementById('button-pos').addEventListener('click', () => {
                console.log("button-pos geklickt");
                let text = document.getElementById("feedback");

                text.innerText = "Du hast positiv bewertet";
                text.style.color = "#9AE19D";
            });

            document.getElementById('button-neg').addEventListener('click', () => {
                console.log("button-neg geklickt");
                let text = document.getElementById("feedback");

                text.innerText = "Du hast negativ bewertet";
                text.style.color = "red";
            });
        }

    }).catch((error) => {
        console.error('Fehler beim Abrufen der URL:', error);
    });
});
