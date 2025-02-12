var map = L.map('map', {
    center: [0, 0],
    zoom: 3,
    maxZoom: 18,
    minZoom: 2,
    worldCopyJump: true
});
map.zoomControl.setPosition('bottomright');  // Verschiebt die Zoom-Steuerung nach rechts unten

var bounds = [
    [-85, -Infinity],
    [85, Infinity]
];
map.setMaxBounds(bounds);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

function updateRadiusValue() {
    var radius = document.getElementById('radius').value;
    document.getElementById('radiusValue').textContent = "Radius: " + radius + " km";
}

function findStationsInRadius() {
    var lat = document.getElementById('latitude').value;
    var lon = document.getElementById('longitude').value;
    var radius = document.getElementById('radius').value;
    var maxStations = document.getElementById('maxStations').value;
    alert('Suche Wetterstationen mit:\nLat: ' + lat + '\nLon: ' + lon + '\nRadius: ' + radius + ' km\nMax. Stationen: ' + maxStations);
}

var currentPing = null;

var customIcon = L.icon({
    iconUrl: 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi2_hdpi.png',
    iconSize: [30, 40],
    iconAnchor: [15, 40],
    popupAnchor: [0, -40]
});

map.on('click', function(e) {
    if (currentPing !== null) {
        map.removeLayer(currentPing);
    }

    currentPing = L.marker(e.latlng, { icon: customIcon }).addTo(map)
        .bindPopup("<b>Position:</b><br>Lat: " + e.latlng.lat.toFixed(4) + "<br>Lon: " + e.latlng.lng.toFixed(4))
        .openPopup();

    document.getElementById('latitude').value = e.latlng.lat.toFixed(4);
    document.getElementById('longitude').value = e.latlng.lng.toFixed(4);
});

function findStationsInRadius() {
    var lat = parseFloat(document.getElementById('latitude').value);
    var lon = parseFloat(document.getElementById('longitude').value);
    var radius = document.getElementById('radius').value;
    var maxStations = document.getElementById('maxStations').value;

    if (isNaN(lat) || isNaN(lon)) {
        alert("Bitte gültige Breiten- und Längengrade eingeben.");
        return;
    }

    // Entferne den vorherigen Marker, falls vorhanden
    if (currentPing !== null) {
        map.removeLayer(currentPing);
    }

    // Setze neuen Ping-Marker mit dem benutzerdefinierten Icon
    currentPing = L.marker([lat, lon], { icon: customIcon }).addTo(map)
        .bindPopup("<b>Position:</b><br>Lat: " + lat.toFixed(4) + "<br>Lon: " + lon.toFixed(4))
        .openPopup();

    // Karte auf die neue Position zentrieren
    map.setView([lat, lon], 10);
}


var radiusCircle = null;  // Variable für den aktuellen Radiuskreis

function updateRadiusValue() {
    var radius = document.getElementById('radius').value;
    document.getElementById('radiusValue').textContent = "Radius: " + radius + " km";

    var lat = parseFloat(document.getElementById('latitude').value);
    var lon = parseFloat(document.getElementById('longitude').value);

    // Entferne den vorherigen Kreis, falls vorhanden
    if (radiusCircle !== null) {
        map.removeLayer(radiusCircle);
    }

    // Falls gültige Koordinaten eingegeben sind, zeichne den Radiuskreis
    if (!isNaN(lat) && !isNaN(lon)) {
        radiusCircle = L.circle([lat, lon], {
            color: 'blue',      // Randfarbe
            fillColor: 'rgba(0, 0, 255, 0.3)',  // Füllfarbe (halbtransparent)
            fillOpacity: 0.3,   // Transparenz der Füllung
            radius: radius * 1000  // Radius in Metern (Schieberegler gibt km an)
        }).addTo(map);
    }
}


// Funktion, um die Dropdown-Menüs mit Jahren zu füllen
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

    // Standardwerte setzen (z.B. 2000–2025)
    yearFrom.value = 2000;
    yearTo.value = 2025;
}

// Rufe die Funktion beim Laden der Seite auf
populateYearDropdowns();
