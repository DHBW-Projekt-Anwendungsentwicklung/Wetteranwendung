/* script.js*/

// Karte initialisieren
const API_BASE_URL = "http://127.0.0.1:8000";

var map = L.map('map', {
    center: [0, 0],
    zoom: 3,
    maxZoom: 18,
    minZoom: 2,
    worldCopyJump: true
});

map.zoomControl.setPosition('bottomright');

var bounds = [
    [-85, -Infinity],
    [85, Infinity]
];
map.setMaxBounds(bounds);

// OpenStreetMap
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

function updateRadiusValue() {
    var radius = document.getElementById('radius').value;
    document.getElementById('radiusValue').textContent = radius;
}

var currentPing = null;
var radiusCircle = null;
var stationMarkers = [];

var customIcon = L.icon({
    iconUrl: 'https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi2_hdpi.png',
    iconSize: [15, 25],
    iconAnchor: [7, 25],
    popupAnchor: [0, -12]
});

var blueIcon = L.icon({
    iconUrl: 'https://upload.wikimedia.org/wikipedia/commons/8/88/Map_marker.svg',
    iconSize: [20, 30],
    iconAnchor: [10, 30]
});

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

function findStationsInRadius() {
    // ... (bestehender Code zum Einlesen von lat, lon, radius, maxStations)
    const floatRegex = /^-?\d+(\.\d+)?$/;
    const intRegex = /^-?\d+$/;

    let latStr = document.getElementById("latitude").value.trim();
    let lonStr = document.getElementById("longitude").value.trim();
    let radiusStr = document.getElementById("radius").value.trim();
    let maxStationsStr = document.getElementById("maxStations").value.trim();

    if (!floatRegex.test(latStr) || 
        !floatRegex.test(lonStr) || 
        !floatRegex.test(radiusStr) ||
        !intRegex.test(maxStationsStr)) 
    {
        alert("Bitte gültige Werte für Breitengrad, Längengrad und Anzahl eingeben!");
        return;
    }
    
    let lat = parseFloat(latStr);
    let lon = parseFloat(lonStr);
    let radius = parseFloat(radiusStr);
    let maxStations = parseInt(maxStationsStr, 10);

    // Neue Parameter: yearFrom und yearTo aus den Inputfeldern
    let yearFrom = document.getElementById('yearFrom').value;
    let yearTo = document.getElementById('yearTo').value;

    // Bereinige vorher eventuell vorhandene Marker und Pings
    if (currentPing !== null) {
        map.removeLayer(currentPing);
    }
    if (radiusCircle !== null) {
        map.removeLayer(radiusCircle);
        radiusCircle = null;
    }
    stationMarkers.forEach(marker => map.removeLayer(marker));
    stationMarkers = [];

    currentPing = L.marker([lat, lon], { icon: customIcon }).addTo(map);

    radiusCircle = L.circle([lat, lon], {
        color: 'rgba(22, 84, 255, 1)',
        fillColor: 'rgba(22, 84, 255, 0.5)',
        fillOpacity: 0.3,
        radius: radius * 1000
    }).addTo(map);

    map.fitBounds(radiusCircle.getBounds(), { padding: [20, 20] });

    // API-Call inkl. yearFrom und yearTo
    fetch(`${API_BASE_URL}/stations/in_radius/?latitude=${lat}&longitude=${lon}&radius=${radius}&max_stations=${maxStations}&yearFrom=${yearFrom}&yearTo=${yearTo}`)
        .then(response => response.json())
        .then(data => {
            console.log("Gefundene Stationen:", data);

            data.forEach((station, index) => {
                var marker = L.marker([station.latitude, station.longitude], {
                    icon: blueIcon,
                    stationId: station.station_id,
                    stationName: station.name || "Unbekannt",
                    stationDistance: station.distance_km
                }).addTo(map)
                .bindTooltip(
                    `Station ${index + 1}: ${station.name || "No Name"}`,
                    {
                        permanent: false,
                        direction: 'top',
                        offset: [0, -10]
                    }
                );

                marker.on('click', function () {
                    map.flyTo(marker.getLatLng(), 8);
                    loadStationCalculations(station.station_id);
                });

                stationMarkers.push(marker);
            });

            displayStationsInSidebar(data);
        })
        .catch(error => {
            console.error("Fehler beim Abrufen der Stationsdaten:", error);
        });
}


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
            <p><b>Entfernung:</b> ${station.distance_km} km</p>
        `;

        item.addEventListener('click', () => {
    loadStationCalculations(station.station_id); // Wetterdaten laden

    let selectedMarker = stationMarkers.find(m => String(m.options.stationId) === String(station.station_id));

    if (selectedMarker) {
        map.flyTo(selectedMarker.getLatLng(), 8);
    }
});


        stationList.appendChild(item);
    });

    var sidebar = document.getElementById("sidebar");
    sidebar.appendChild(stationList);
}

// Popup
function loadStationCalculations(stationId) {
    let yearFrom = parseInt(document.getElementById('yearFrom').value, 10) || 1800;
    let yearTo   = parseInt(document.getElementById('yearTo').value, 10)   || 2025;

    fetch(`${API_BASE_URL}/station_calculations/?station_id=${stationId}&yearFrom=${yearFrom}&yearTo=${yearTo}`)
        .then(response => response.json())
        .then(data => {
            if (!Array.isArray(data)) {
                if (data.reason === "download_failed") {
                    alert("Daten können nicht abgerufen werden.");
                } else {
                    alert(data.error ? "Fehler: " + data.error : "Unbekannter Fehler");
                }
                return;
            }

            let station = stationMarkers.find(marker => String(marker.options.stationId) === String(stationId));
            let stationName = station && station.options.stationName ? station.options.stationName : "Unbekannt";

            // JSON als String
            let encodedData = encodeURIComponent(JSON.stringify(data));

            let popupHtml = buildCalculationsPopupHtml(encodedData, stationId, stationName);

            if (station) {
                station.bindPopup(popupHtml, {
                    offset: [0, -10],
                    autoPan: true,
                    autoPanPaddingTopLeft: [50, 50],
                    autoPanPaddingBottomRight: [50, 50]
                }).openPopup();
            } else {
                alert("Fehler: Kein Marker für diese Station gefunden.");
            }
        })
        .catch(err => {
            console.error("Fehler beim Laden der Berechnungen:", err);
        });
}

function buildCalculationsPopupHtml(encodedData, stationId, stationName) {
    let statsArray = JSON.parse(decodeURIComponent(encodedData));

    let tableRows = "";
    statsArray.forEach(row => {
        if (row.yearly_min_mean) {  // Nur wenn es Daten gibt
            tableRows += `
              <tr>
                <td>${row.year}</td>
                <td>${row.yearly_min_mean}</td>
                <td>${row.spring}</td>
                <td>${row.summer}</td>
                <td>${row.autumn}</td>
                <td>${row.winter}</td>
              </tr>
            `;
        }
    });

    let page1Content = `
  <div class="popup-header">
    Wetterstation: ${stationName || 'Unbekannt'} (ID: ${stationId})
  </div>
  <div class="popup-table-container page-1" style="max-height: 400px; overflow-y: auto;">
    <table class="popup-table">
      <thead>
        <tr>
          <th>Jahr</th>
          <th>Jährliche Mittelwerte</th>
          <th>Frühling</th>
          <th>Sommer</th>
          <th>Herbst</th>
          <th>Winter</th>
        </tr>
      </thead>
      <tbody>
        ${tableRows}
      </tbody>
    </table>
  </div>
`;

    // Grafik
    let page2Content = `
      <div class="popup-table-container page-2" style="display: none;">
        <div id="chartData" style="display:none;">${encodedData}</div>
        <div class="popup-charts-container">
          <canvas id="chartCombined"></canvas>
        </div>
      </div>
    `;

    let paginationControls = `
  <div class="popup-pagination">
    <button class="prev-page" onclick="switchPopupPage(-1)">←</button>
    <span class="page-indicator"><span id="currentPage">Tabelle</span></span>
    <button class="next-page" onclick="switchPopupPage(1)">→</button>
  </div>
`;

    return page1Content + page2Content + paginationControls;
}


function switchPopupPage(direction) {
    let page1 = document.querySelector(".popup-table-container.page-1");
    let page2 = document.querySelector(".popup-table-container.page-2");
    let pageIndicator = document.getElementById("currentPage");

    if (direction === 1) {
        page1.style.display = "none";
        page2.style.display = "block";
        pageIndicator.textContent = "Grafik";
        buildChartsOnPage2();
        setTimeout(() => {
            if (map._popup) {
              map._popup._adjustPan();
            }
          }, 0);
    } else {
        page1.style.display = "block";
        page2.style.display = "none";
        pageIndicator.textContent = "Tabelle";
        setTimeout(() => {
            if (map._popup) {
              map._popup._adjustPan();
            }
          }, 0);
    }
}

function buildChartsOnPage2() {
    let dataDiv = document.getElementById("chartData");
    if (!dataDiv) return;

    let rawString = dataDiv.textContent.trim();
    let statsArray;
    try {
        statsArray = JSON.parse(decodeURIComponent(rawString));
    } catch (err) {
        console.error("Konnte chartData nicht parsen:", err);
        return;
    }

    let years = [];
    let yearlyMinValues = [];
    let yearlyMaxValues = [];
    let springMinValues = [];
    let springMaxValues = [];
    let summerMinValues = [];
    let summerMaxValues = [];
    let autumnMinValues = [];
    let autumnMaxValues = [];
    let winterMinValues = [];
    let winterMaxValues = [];

    function parseMinMaxString(str) {
        if (!str || !str.includes("min:") || !str.includes("max:")) {
            return { min: null, max: null };
        }
        let regex = /min:\s*([\d.-]+).+max:\s*([\d.-]+)/;
        let match = str.match(regex);
        if (!match) return { min: null, max: null };
        let parsedMin = parseFloat(match[1]);
        let parsedMax = parseFloat(match[2]);
        return { min: parsedMin, max: parsedMax };
    }

    statsArray.forEach(row => {
        years.push(row.year);

        let yData = parseMinMaxString(row.yearly_min_mean);
        yearlyMinValues.push(yData.min);
        yearlyMaxValues.push(yData.max);

        let sp = parseMinMaxString(row.spring);
        springMinValues.push(sp.min);
        springMaxValues.push(sp.max);

        let su = parseMinMaxString(row.summer);
        summerMinValues.push(su.min);
        summerMaxValues.push(su.max);

        let au = parseMinMaxString(row.autumn);
        autumnMinValues.push(au.min);
        autumnMaxValues.push(au.max);

        let wi = parseMinMaxString(row.winter);
        winterMinValues.push(wi.min);
        winterMaxValues.push(wi.max);
    });

    // Chart.js
    let ctx = document.getElementById('chartCombined').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: years,
            datasets: [
                {
                    label: 'Jährlicher Mittelwert Min',
                    data: yearlyMinValues,
                    borderColor: 'red',
                    backgroundColor: 'red',
                    spanGaps: false,
                    segment: {
                        borderColor: ctx => {
                            if (!ctx.p0.parsed || !ctx.p1.parsed) {
                                return 'rgba(0,0,0,0)';
                            }
                            const x0 = Number(ctx.p0.parsed.x);
                            const x1 = Number(ctx.p1.parsed.x);
                            return (x1 - x0 === 1) ? 'red' : 'rgba(0,0,0,0)';
                        }
                    }
                },
                {
                    label: 'Jährlicher Mittelwert Max',
                    data: yearlyMaxValues,
                    borderColor: 'blue',
                    backgroundColor: 'blue',
                    spanGaps: false,
                    segment: {
                        borderColor: ctx => {
                            if (!ctx.p0.parsed || !ctx.p1.parsed) {
                                return 'rgba(0,0,0,0)';
                            }
                            const x0 = Number(ctx.p0.parsed.x);
                            const x1 = Number(ctx.p1.parsed.x);
                            return (x1 - x0 === 1) ? 'blue' : 'rgba(0,0,0,0)';
                        }
                    }
                },
                {
                    label: 'Frühling Min',
                    data: springMinValues,
                    borderColor: 'green',
                    backgroundColor: 'green',
                    spanGaps: false,
                    segment: {
                        borderColor: ctx => {
                            if (!ctx.p0.parsed || !ctx.p1.parsed) {
                                return 'rgba(0,0,0,0)';
                            }
                            const x0 = Number(ctx.p0.parsed.x);
                            const x1 = Number(ctx.p1.parsed.x);
                            return (x1 - x0 === 1) ? 'green' : 'rgba(0,0,0,0)';
                        }
                    },
                    hidden: true
                },
                {
                    label: 'Frühling Max',
                    data: springMaxValues,
                    borderColor: 'lightgreen',
                    backgroundColor: 'lightgreen',
                    spanGaps: false,
                    segment: {
                        borderColor: ctx => {
                            if (!ctx.p0.parsed || !ctx.p1.parsed) {
                                return 'rgba(0,0,0,0)';
                            }
                            const x0 = Number(ctx.p0.parsed.x);
                            const x1 = Number(ctx.p1.parsed.x);
                            return (x1 - x0 === 1) ? 'lightgreen' : 'rgba(0,0,0,0)';
                        }
                    },
                    hidden: true
                },
                {
                    label: 'Sommer Min',
                    data: summerMinValues,
                    borderColor: 'darkorange',
                    backgroundColor: 'darkorange',
                    spanGaps: false,
                    segment: {
                        borderColor: ctx => {
                            if (!ctx.p0.parsed || !ctx.p1.parsed) {
                                return 'rgba(0,0,0,0)';
                            }
                            const x0 = Number(ctx.p0.parsed.x);
                            const x1 = Number(ctx.p1.parsed.x);
                            return (x1 - x0 === 1) ? 'darkorange' : 'rgba(0,0,0,0)';
                        }
                    },
                    hidden: true
                },
                {
                    label: 'Sommer Max',
                    data: summerMaxValues,
                    borderColor: '#FFD700',
                    backgroundColor: '#FFD700',
                    spanGaps: false,
                    segment: {
                        borderColor: ctx => {
                            if (!ctx.p0.parsed || !ctx.p1.parsed) {
                                return 'rgba(0,0,0,0)';
                            }
                            const x0 = Number(ctx.p0.parsed.x);
                            const x1 = Number(ctx.p1.parsed.x);
                            return (x1 - x0 === 1) ? '#FFD700' : 'rgba(0,0,0,0)';
                        }
                    },
                    hidden: true
                },
                {
                    label: 'Herbst Min',
                    data: autumnMinValues,
                    borderColor: 'saddlebrown',
                    backgroundColor: 'saddlebrown',
                    spanGaps: false,
                    segment: {
                        borderColor: ctx => {
                            if (!ctx.p0.parsed || !ctx.p1.parsed) {
                                return 'rgba(0,0,0,0)';
                            }
                            const x0 = Number(ctx.p0.parsed.x);
                            const x1 = Number(ctx.p1.parsed.x);
                            return (x1 - x0 === 1) ? 'saddlebrown' : 'rgba(0,0,0,0)';
                        }
                    },
                    hidden: true
                },
                {
                    label: 'Herbst Max',
                    data: autumnMaxValues,
                    borderColor: 'tan',
                    backgroundColor: 'tan',
                    spanGaps: false,
                    segment: {
                        borderColor: ctx => {
                            if (!ctx.p0.parsed || !ctx.p1.parsed) {
                                return 'rgba(0,0,0,0)';
                            }
                            const x0 = Number(ctx.p0.parsed.x);
                            const x1 = Number(ctx.p1.parsed.x);
                            return (x1 - x0 === 1) ? 'tan' : 'rgba(0,0,0,0)';
                        }
                    },
                    hidden: true
                },
                {
                    label: 'Winter Min',
                    data: winterMinValues,
                    borderColor: 'gray',
                    backgroundColor: 'gray',
                    spanGaps: false,
                    segment: {
                        borderColor: ctx => {
                            if (!ctx.p0.parsed || !ctx.p1.parsed) {
                                return 'rgba(0,0,0,0)';
                            }
                            const x0 = Number(ctx.p0.parsed.x);
                            const x1 = Number(ctx.p1.parsed.x);
                            return (x1 - x0 === 1) ? 'gray' : 'rgba(0,0,0,0)';
                        }
                    },
                    hidden: true
                },
                {
                    label: 'Winter Max',
                    data: winterMaxValues,
                    borderColor: 'lightgray',
                    backgroundColor: 'lightgray',
                    spanGaps: false,
                    segment: {
                        borderColor: ctx => {
                            if (!ctx.p0.parsed || !ctx.p1.parsed) {
                                return 'rgba(0,0,0,0)';
                            }
                            const x0 = Number(ctx.p0.parsed.x);
                            const x1 = Number(ctx.p1.parsed.x);
                            return (x1 - x0 === 1) ? 'lightgray' : 'rgba(0,0,0,0)';
                        }
                    },
                    hidden: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Temperatur (°C)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Jahr'
                    }
                }
            }
        }
    });
}

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
    yearTo.value = 2024;
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
