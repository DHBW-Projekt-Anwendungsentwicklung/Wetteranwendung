// Karte initialisieren
var map = L.map('map', {
    center: [0, 0],
    zoom: 3,
    maxZoom: 18,
    minZoom: 2,
    worldCopyJump: true
});

// Zoom-Steuerung nach unten rechts
map.zoomControl.setPosition('bottomright');

// Begrenzung der Karte (bound-fix)
var bounds = [
    [-85, -Infinity],
    [85, Infinity]
];
map.setMaxBounds(bounds);

// TileLayer hinzufügen (OpenStreetMap)
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Aktuellen Wert des Radius-Range-Inputs anzeigen
function updateRadiusValue() {
    var radius = document.getElementById('radius').value;
    document.getElementById('radiusValue').textContent = radius;
}

// Globale Variablen für Marker und Kreis
var currentPing = null;
var radiusCircle = null;
var stationMarkers = [];

// Eigenes Icon für den roten Pin
var customIcon = L.icon({
    iconUrl: 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi2_hdpi.png',
    iconSize: [15, 25],
    iconAnchor: [7, 25],
    popupAnchor: [0, -12]
});

// Eigenes Icon für die blauen Stations-Pins
var blueIcon = L.icon({
    iconUrl: 'https://upload.wikimedia.org/wikipedia/commons/8/88/Map_marker.svg',
    iconSize: [20, 30],
    iconAnchor: [10, 30]
});

// Klick-Event auf der Karte für den roten Pin
map.on('click', function (e) {
    // Entferne den vorherigen roten Pin
    if (currentPing !== null) {
        map.removeLayer(currentPing);
    }

    // Entferne den vorherigen Kreis
    if (radiusCircle !== null) {
        map.removeLayer(radiusCircle);
        radiusCircle = null;
    }

    // Entferne alle vorherigen blauen Marker
    stationMarkers.forEach(marker => map.removeLayer(marker));
    stationMarkers = [];

    // Neuen roten Pin setzen
    currentPing = L.marker(e.latlng, { icon: customIcon }).addTo(map);

    // Eingabefelder aktualisieren
    document.getElementById('latitude').value = e.latlng.lat.toFixed(4);
    document.getElementById('longitude').value = e.latlng.lng.toFixed(4);
});

// Funktion zum Finden und Anzeigen von Stationen im Radius
function findStationsInRadius() {
    var lat = parseFloat(document.getElementById("latitude").value);
    var lon = parseFloat(document.getElementById("longitude").value);
    var radius = parseFloat(document.getElementById("radius").value);
    var maxStations = parseInt(document.getElementById("maxStations").value, 10);

    if (isNaN(lat) || isNaN(lon) || isNaN(radius) || isNaN(maxStations)) {
        alert("Bitte gültige Werte für Breite, Länge, Radius und Anzahl eingeben!");
        return;
    }

    // -- NEU: Roter Pin anhand der Eingabefelder setzen --
    if (currentPing !== null) {
        map.removeLayer(currentPing);
    }
    currentPing = L.marker([lat, lon], { icon: customIcon }).addTo(map);

    // Entferne alten Kreis und alte Marker
    if (radiusCircle !== null) {
        map.removeLayer(radiusCircle);
        radiusCircle = null;
    }
    stationMarkers.forEach(marker => map.removeLayer(marker));
    stationMarkers = [];

    // Kreis zeichnen
    radiusCircle = L.circle([lat, lon], {
        color: 'rgba(22, 84, 255, 1)',
        fillColor: 'rgba(22, 84, 255, 0.5)',
        fillOpacity: 0.3,
        radius: radius * 1000
    }).addTo(map);

    // Karte an den Kreis anpassen
    map.fitBounds(radiusCircle.getBounds(), { padding: [20, 20] });

    // Ajax-Request an Django
    fetch(`/stations/in_radius/?latitude=${lat}&longitude=${lon}&radius=${radius}&max_stations=${maxStations}`)
        .then(response => response.json())
        .then(data => {
            console.log("Gefundene Stationen:", data);

            // Marker setzen
            data.forEach((station, index) => {
                // Blauer Pin
                var marker = L.marker([station.latitude, station.longitude], { icon: blueIcon })
                    .addTo(map)
                    // Tooltip mit "Station X: Name"
                    .bindTooltip(
                        `Station ${index + 1}: ${station.name || "No Name"}`,
                        {
                            permanent: false,
                            direction: 'top',
                            offset: [0, -10]
                        }
                    );
                stationMarkers.push(marker);
            });

            // Stationen in der linken Sidebar anzeigen
            displayStationsInSidebar(data);
        })
        .catch(error => {
            console.error("Fehler beim Abrufen der Stationsdaten:", error);
        });
}

// Zeigt gefundene Stationen in der linken Sidebar an
function displayStationsInSidebar(data) {
    // Vorherige Liste entfernen
    var oldList = document.getElementById("stationList");
    if (oldList) {
        oldList.remove();
    }

    // Neues Container-Element
    var stationList = document.createElement("div");
    stationList.id = "stationList";

    // Überschrift "Ergebnisse:" hinzufügen
    var headingField = document.createElement("div");
    headingField.className = "field results-heading";

    var headingLabel = document.createElement("label");
    headingLabel.textContent = "Ergebnisse:";
    headingField.appendChild(headingLabel);
    stationList.appendChild(headingField);

    // Stationen durchgehen und anzeigen
    data.forEach(function (station, index) {
        var item = document.createElement("div");
        item.className = "station-item";
        item.innerHTML = `
            <h4>Station ${index + 1}:</h4>
            <p><b>Name:</b> ${station.name || 'No Name'}</p>
            <p><b>ID:</b> ${station.station_id}</p>
            <p><b>Breitengrad:</b> ${station.latitude}</p>
            <p><b>Längengrad:</b> ${station.longitude}</p>
        `;
        stationList.appendChild(item);
    });

    // Scrollbar, wenn mehr als 3 Einträge
    if (data.length > 3) {
        stationList.style.maxHeight = "300px";
        stationList.style.overflowY = "auto";
    } else {
        stationList.style.maxHeight = "none";
        stationList.style.overflowY = "visible";
    }

    // In den Sidebar einfügen
    var sidebar = document.getElementById("sidebar");
    sidebar.appendChild(stationList);
}

// Dropdowns für Jahresauswahl befüllen (mit voreingestelltem Zeitraum 2000-2025)
function populateYearDropdowns() {
    var yearFrom = document.getElementById('yearFrom');
    var yearTo = document.getElementById('yearTo');

    for (var year = 1800; year <= 2025; year++) {
        var optionFrom = document.createElement('option');
        optionFrom.value = year;
        optionFrom.textContent = year;
        yearFrom.appendChild(optionFrom);

        var optionTo = document.createElement('option');
        optionTo.value = year;
        optionTo.textContent = year;
        yearTo.appendChild(optionTo);
    }

    // Standardwerte setzen (Zeitraum 2000 - 2025 beibehalten)
    yearFrom.value = 2000;
    yearTo.value = 2025;
}

function validateMaxStations() {
    var input = document.getElementById("maxStations");
    var value = parseInt(input.value, 10);

    if (!isNaN(value)) {
        if (value > 10) {
            input.value = 10;
        } else if (value < 1) {
            input.value = 1;
        }
    }
}

// Beim Laden der Seite das Dropdown befüllen
populateYearDropdowns();
