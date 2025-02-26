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
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Aktuellen Wert des Radius-Range-Inputs anzeigen
function updateRadiusValue() {
    var radius = document.getElementById('radius').value;
    document.getElementById('radiusValue').textContent = radius;
}

// Globale Variablen für Marker (Ping) und Circle (Radius)
var currentPing = null;
var radiusCircle = null;
var stationMarkers = [];

// Eigenes Icon für den Pin
var customIcon = L.icon({
    iconUrl: 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi2_hdpi.png',
    iconSize: [15, 25],
    iconAnchor: [7, 25],
    popupAnchor: [0, -12]
});

// Klick-Event auf der Karte
map.on('click', function (e) {
    if (currentPing !== null) {
        map.removeLayer(currentPing);
    }
    if (radiusCircle !== null) {
        map.removeLayer(radiusCircle);
        radiusCircle = null;
    }

    currentPing = L.marker(e.latlng, { icon: customIcon })
        .addTo(map)
        .bindPopup(
            generatePopupContent(e.latlng.lat, e.latlng.lng),
            {
                autoPan: true,
                keepInView: true,
                autoPanPaddingTopLeft: L.point(50, 50),
                autoPanPaddingBottomRight: L.point(50, 50),
                maxWidth: Infinity
            }
        )
        .openPopup();

    document.getElementById('latitude').value = e.latlng.lat.toFixed(4);
    document.getElementById('longitude').value = e.latlng.lng.toFixed(4);
});

// Funktion zum Anzeigen des Kreises
function findStationsInRadius() {
    var lat = parseFloat(document.getElementById("latitude").value);
    var lon = parseFloat(document.getElementById("longitude").value);
    var radius = parseFloat(document.getElementById("radius").value);
    var maxStations = parseInt(document.getElementById("maxStations").value, 10);

    if (isNaN(lat) || isNaN(lon) || isNaN(radius) || isNaN(maxStations)) {
        alert("Bitte gültige Werte für Breite, Länge, Radius und Anzahl eingeben!");
        return;
    }

    if (radiusCircle !== null) {
        map.removeLayer(radiusCircle);
        radiusCircle = null;
    }
    stationMarkers.forEach(marker => map.removeLayer(marker));
    stationMarkers = [];

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

            data.forEach(station => {
                var marker = L.marker([station.latitude, station.longitude])
                    .addTo(map)
                    .bindPopup(`
                        <b>${station.station_id}</b><br>
                        ${station.name || "No Name"}<br>
                        Lat: ${station.latitude}, Lon: ${station.longitude}
                    `);
                stationMarkers.push(marker);
            });
        })
        .catch(error => {
            console.error("Fehler beim Abrufen der Stationsdaten:", error);
        });
}

// Popup-Inhalt generieren
function generatePopupContent(lat, lon) {
    return `
        <div class="popup-content">
            <h3>
                Position:<br>
                Lat ${lat.toFixed(4)}, Lon ${lon.toFixed(4)}
            </h3>
            </div>
            <div class="tab-container">
                <button class="tab-button active" onclick="showTab('table')">Tabelle</button>
                <button class="tab-button" onclick="showTab('chart')">Grafik</button>
            </div>
            <div id="table" class="tab-content active table-container">
                <table>
                    <tr>
                        <th>Jahr</th>
                        <th>Mittelwert</th>
                        <th>Frühling</th>
                        <th>Sommer</th>
                        <th>Herbst</th>
                        <th>Winter</th>
                    </tr>
                    <tr>
                        <td>2022</td>
                        <td>10°C</td>
                        <td>min: 8°C<br>max: 18°C</td>
                        <td>min: 20°C<br>max: 30°C</td>
                        <td>min: 9°C<br>max: 15°C</td>
                        <td>min: -2°C<br>max: 8°C</td>
                    </tr>
                    <tr>
                        <td>2023</td>
                        <td>12°C</td>
                        <td>min: 10°C<br>max: 20°C</td>
                        <td>min: 22°C<br>max: 32°C</td>
                        <td>min: 10°C<br>max: 16°C</td>
                        <td>min: 0°C<br>max: 9°C</td>
                    </tr>
                </table>
            </div>
            <div id="chart" class="tab-content" style="display:none;">
                <p>Grafik anzeigen!</p>
            </div>
        </div>
    `;
}

// Tabs wechseln (Tabelle / Grafik)
function showTab(tabId) {
    var tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(function (tab) {
        tab.style.display = 'none';
    });
    document.getElementById(tabId).style.display = 'block';
}

// Dropdowns für Jahresauswahl befüllen
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

populateYearDropdowns();
