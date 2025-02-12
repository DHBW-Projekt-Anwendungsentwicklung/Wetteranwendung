var map = L.map('map', {
    center: [0, 0],
    zoom: 3,
    maxZoom: 18,
    minZoom: 2,
    worldCopyJump: true
});

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
