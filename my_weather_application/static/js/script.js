// Initialize the map and set its view to a specific location and zoom level
var map = L.map('map').setView([51.505, -0.09], 13);

// Add a grey tile layer (grayscale OSM tiles)
L.tileLayer('https://tiles.wmflabs.org/bw-mapnik/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Function to add a marker on click
map.on('click', function(e) {
  var lat = e.latlng.lat;
  var lng = e.latlng.lng;
  
  // Add a marker at the clicked location
  L.marker([lat, lng]).addTo(map)
    .bindPopup("Marker at: <br> Latitude: " + lat.toFixed(5) + "<br> Longitude: " + lng.toFixed(5))
    .openPopup();
});