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

// Klick auf die Karte => roter Pin
map.on('click', function (e) {
    if (currentPing !== null) {
        map.removeLayer(currentPing);
    }
    if (radiusCircle !== null) {
        map.removeLayer(radiusCircle);
        radiusCircle = null;
    }
    stationMarkers.forEach(marker => map.removeLayer(marker));
    stationMarkers = [];

    currentPing = L.marker(e.latlng, { icon: customIcon }).addTo(map);

    document.getElementById('latitude').value = e.latlng.lat.toFixed(4);
    document.getElementById('longitude').value = e.latlng.lng.toFixed(4);
});

// Stationssuche
function findStationsInRadius() {
    var lat = parseFloat(document.getElementById("latitude").value);
    var lon = parseFloat(document.getElementById("longitude").value);
    var radius = parseFloat(document.getElementById("radius").value);
    var maxStations = parseInt(document.getElementById("maxStations").value, 10);

    if (isNaN(lat) || isNaN(lon) || isNaN(radius) || isNaN(maxStations)) {
        alert("Bitte gültige Werte für Breite, Länge, Radius und Anzahl eingeben!");
        return;
    }

    // Roter Pin auf Eingabewerte
    if (currentPing !== null) {
        map.removeLayer(currentPing);
    }
    currentPing = L.marker([lat, lon], { icon: customIcon }).addTo(map);

    // Alten Kreis und blaue Marker entfernen
    if (radiusCircle !== null) {
        map.removeLayer(radiusCircle);
        radiusCircle = null;
    }
    stationMarkers.forEach(marker => map.removeLayer(marker));
    stationMarkers = [];

    // Neuer Kreis
    radiusCircle = L.circle([lat, lon], {
        color: 'rgba(22, 84, 255, 1)',
        fillColor: 'rgba(22, 84, 255, 0.5)',
        fillOpacity: 0.3,
        radius: radius * 1000
    }).addTo(map);

    map.fitBounds(radiusCircle.getBounds(), { padding: [20, 20] });

    fetch(`/stations/in_radius/?latitude=${lat}&longitude=${lon}&radius=${radius}&max_stations=${maxStations}`)
        .then(response => response.json())
        .then(data => {
            console.log("Gefundene Stationen:", data);

            data.forEach((station, index) => {
                // Blauer Pin
                var marker = L.marker([station.latitude, station.longitude], { icon: blueIcon })
                    .addTo(map)
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

            displayStationsInSidebar(data);
        })
        .catch(error => {
            console.error("Fehler beim Abrufen der Stationsdaten:", error);
        });
}

// Zeige Stationen links in der Sidebar
function displayStationsInSidebar(data) {
    var oldList = document.getElementById("stationList");
    if (oldList) {
        oldList.remove();
    }
    var stationList = document.createElement("div");
    stationList.id = "stationList";

    var headingField = document.createElement("div");
    headingField.className = "field results-heading";
    var headingLabel = document.createElement("label");
    headingLabel.textContent = "Ergebnisse:";
    headingField.appendChild(headingLabel);
    stationList.appendChild(headingField);

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

        // WICHTIG: Klick => Hol Berechnungen + zeig Popup
        item.addEventListener('click', () => {
            loadStationCalculations(station.station_id);
        });

        stationList.appendChild(item);
    });

    if (data.length > 3) {
        stationList.style.maxHeight = "300px";
        stationList.style.overflowY = "auto";
    } else {
        stationList.style.maxHeight = "none";
        stationList.style.overflowY = "visible";
    }

    var sidebar = document.getElementById("sidebar");
    sidebar.appendChild(stationList);
}

// NEU: Holt vom Backend die Jahres-Berechnungen für station_id und zeigt sie in einem Popup
function loadStationCalculations(stationId) {
    let yearFrom = parseInt(document.getElementById('yearFrom').value, 10) || 1800;
    let yearTo   = parseInt(document.getElementById('yearTo').value, 10)   || 2025;

    fetch(`/station_calculations/?station_id=${stationId}&yearFrom=${yearFrom}&yearTo=${yearTo}`)
        .then(response => response.json())
        .then(data => {
            if (!Array.isArray(data)) {
                // Falls das Backend doch ein error-Objekt gibt
                if (data.error) {
                    alert("Fehler: " + data.error);
                } else {
                    alert("Unbekannter Fehler");
                }
                return;
            }
            // Hier data ist ein Array
            if (!data.length) {
                alert("Keine Daten für diese Station (oder Station hat keine .dly-Datei).");
                return;
            }
            console.log("Berechnete Stats:", data);

            let popupHtml = buildCalculationsPopupHtml(data, stationId);
            if (currentPing) {
                currentPing.bindPopup(popupHtml).openPopup();
            }
        })
        .catch(err => {
            console.error("Fehler beim Laden der Berechnungen:", err);
        });
}


// Baut aus dem Berechnungs-Array eine HTML-Tabelle oder Text
function buildCalculationsPopupHtml(statsArray, stationId) {
    // statsArray = [
    //   { year:2021, yearly_mean: 7.8, spring:'min:5, max:15', ... },
    //   { year:2022, yearly_mean: 8.1, spring:'min:4, max:16', ... },
    //   ...
    // ]
    let html = `
        <div style="text-align:center;">
            <h3>Auswertung: ${stationId}</h3>
            <table border="1" style="margin:auto;">
                <tr>
                    <th>Jahr</th>
                    <th>Jahres-Mittel</th>
                    <th>Frühling</th>
                    <th>Sommer</th>
                    <th>Herbst</th>
                    <th>Winter</th>
                </tr>
    `;

    statsArray.forEach(row => {
        html += `
            <tr>
                <td>${row.year}</td>
                <td>${row.yearly_mean || "?"} °C</td>
                <td>${row.spring || "?"}</td>
                <td>${row.summer || "?"}</td>
                <td>${row.autumn || "?"}</td>
                <td>${row.winter || "?"}</td>
            </tr>
        `;
    });

    html += `</table></div>`;
    return html;
}

// Dropdowns vorbesetzen
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

    // Standardwerte
    yearFrom.value = 2000;
    yearTo.value = 2025;
}

function validateMaxStations() {
    var input = document.getElementById("maxStations");
    var value = parseInt(input.value, 10);
    if (!isNaN(value)) {
        if (value > 10) input.value = 10;
        else if (value < 1) input.value = 1;
    }
}

populateYearDropdowns();
