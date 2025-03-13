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
        addTo: jest.fn(() => markerObj),       // gibt markerObj zurück
        bindTooltip: jest.fn(() => markerObj),   // gibt markerObj zurück
        on: jest.fn(),
        getLatLng: jest.fn(() => ({ lat: 50.1, lng: 9.1 }))
      };
      return markerObj;
    }),
    circle: jest.fn(() => ({
      addTo: jest.fn(() => ({
        getBounds: jest.fn(() => ({ dummy: true })) // Dummy-Implementierung
      })),
    })),
    tileLayer: jest.fn(() => ({
      addTo: jest.fn(),
    })),
  };

  let findStationsInRadius;

  describe("Front-End Tests für script.js", () => {
    beforeEach(() => {
      // DOM vorbereiten – hier sind die benötigten Elemente enthalten:
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
      
      // Alle Module neu laden, damit populateYearDropdowns() den vorbereiteten DOM findet
      jest.resetModules();
      ({ findStationsInRadius } = require('../static/JS/script.js'));
    });
  

  test("Fehler bei ungültigen Eingaben (Regex-Check)", () => {
    // Simulation: falsche Koordinaten
    document.getElementById("latitude").value = "abc"; 
    document.getElementById("longitude").value = "def";
    document.getElementById("radius").value = "zehn";
    document.getElementById("maxStations").value = "xxx";

    // Mock für alert()
    global.alert = jest.fn();

    // Aufruf
    findStationsInRadius();

    // Erwartung: alert(...) mit Hinweismeldung
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

    // Wir mocken fetch(), um keinen echten Netzwerkzugriff zu haben
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve([
          { station_id: "S123", latitude: 50.1, longitude: 9.1, name: "TestStation", distance_km: 5 }
        ])
      })
    );

    // Optional: Leaflet-Funktionen mocken
    // z.B. global.L = { map: jest.fn(...), etc. }

    // Aufruf
    findStationsInRadius();

    // Jetzt könnten wir prüfen, ob fetch mit passender URL aufgerufen wurde
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/stations/in_radius/?latitude=50&longitude=9&radius=10&max_stations=3")
    );

    // Weiterer Check: z.B. ob "loadingAnimation" eingeblendet wurde
    const loadingDiv = document.getElementById("loadingAnimation");
    expect(loadingDiv.style.display).toBe("block");
  });
});