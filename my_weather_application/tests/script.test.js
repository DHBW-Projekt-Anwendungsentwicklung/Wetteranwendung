/**
 * @jest-environment jsdom
 */

global.L = {
    map: jest.fn(() => ({
      removeLayer: jest.fn(),
      addTo: jest.fn(),
      setMaxBounds: jest.fn(),
      on: jest.fn(),
      fitBounds: jest.fn(),
      zoomControl: {
        setPosition: jest.fn(),
      },
    })),
    icon: jest.fn(() => ({})),
    marker: jest.fn(() => {
      const markerObj = {
        addTo: jest.fn(() => markerObj),
        bindTooltip: jest.fn(() => markerObj),
        on: jest.fn(),
        getLatLng: jest.fn(() => ({ lat: 50.1, lng: 9.1 }))
      };
      return markerObj;
    }),
    circle: jest.fn(() => ({
      addTo: jest.fn(() => ({
        getBounds: jest.fn(() => ({ dummy: true }))
      })),
    })),
    tileLayer: jest.fn(() => ({
      addTo: jest.fn(),
    })),
  };

  let findStationsInRadius;

  describe("Front-End Tests für script.js", () => {
    beforeEach(() => {
      document.body.innerHTML = `
        <input id="latitude" value=""/>
        <input id="longitude" value=""/>
        <input id="radius" value=""/>
        <input id="maxStations" value=""/>
        <select id="yearFrom"></select>
        <select id="yearTo"></select>
        <div id="loadingAnimation" style="display:none"></div>
        <div id="sidebar"></div>
      `;
      
      jest.resetModules();
      ({ findStationsInRadius } = require('../static/JS/script.js'));
    });
  

  test("Fehler bei ungültigen Eingaben (Regex-Check)", () => {
    // Simulation: falsche Koordinaten
    document.getElementById("latitude").value = "abc"; 
    document.getElementById("longitude").value = "def";
    document.getElementById("radius").value = "zehn";
    document.getElementById("maxStations").value = "xxx";

    global.alert = jest.fn();

    findStationsInRadius();

    expect(global.alert).toHaveBeenCalledWith(
      "Bitte gültige Werte für Breitengrad, Längengrad und Anzahl eingeben!"
    );
  });

  test("Korrektes Setzen von Marker + Radius, wenn Eingaben gültig", () => {
    // Gültige Eingaben
    document.getElementById("latitude").value = "50.0";
    document.getElementById("longitude").value = "9.0";
    document.getElementById("radius").value = "10";
    document.getElementById("maxStations").value = "3";

    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve([
          { station_id: "S123", latitude: 50.1, longitude: 9.1, name: "TestStation", distance_km: 5 }
        ])
      })
    );

    findStationsInRadius();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/stations/in_radius/?latitude=50&longitude=9&radius=10&max_stations=3")
    );

    const loadingDiv = document.getElementById("loadingAnimation");
    expect(loadingDiv.style.display).toBe("block");
  });
});