/* ============================================================
   Tariq.lb -- map.js
   Initializes the Leaflet map, loads existing reports as
   severity-colored pins, and exposes a small API (window.TariqMap)
   that upload.js uses for manual pin placement.
   ============================================================ */

(function () {
  const cfg = window.TARIQ_CONFIG || { defaultLat: 33.8938, defaultLon: 35.5018 };

  const map = L.map('map', { zoomControl: true }).setView(
    [cfg.defaultLat, cfg.defaultLon], 12
  );

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map);

  const severityClass = {
    Low: 'tariq-pin--low',
    Medium: 'tariq-pin--medium',
    High: 'tariq-pin--high',
    Critical: 'tariq-pin--critical'
  };

  function makeIcon(severityLevel) {
    const cls = severityClass[severityLevel] || 'tariq-pin--medium';
    return L.divIcon({
      className: '',
      html: `<div class="tariq-pin ${cls}"></div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 26],
      popupAnchor: [0, -28]
    });
  }

  function popupHtml(report) {
    return `
      <div class="popup-card">
        <img src="${report.image_url}" alt="${report.damage_type}" />
        <div class="popup-card__type">${report.damage_type}</div>
        <div style="font-size:12.5px;color:#5a5d63;">
          Severity: ${report.severity_level} &middot; ${report.created_at}
        </div>
        <a class="popup-card__link" href="/report/${report.id}">View full report &rarr;</a>
      </div>
    `;
  }

  let markersLayer = L.layerGroup().addTo(map);

  function renderReports(reports) {
    markersLayer.clearLayers();
    reports.forEach((report) => {
      const marker = L.marker([report.latitude, report.longitude], {
        icon: makeIcon(report.severity_level)
      });
      marker.bindPopup(popupHtml(report));
      marker.addTo(markersLayer);
    });

    // Update top-bar stats
    const totalEl = document.getElementById('stat-total');
    const criticalEl = document.getElementById('stat-critical');
    if (totalEl) totalEl.textContent = reports.length;
    if (criticalEl) {
      criticalEl.textContent = reports.filter(r => r.severity_level === 'Critical').length;
    }
  }

  async function loadReports() {
    try {
      const res = await fetch('/api/reports');
      const reports = await res.json();
      renderReports(reports);
      return reports;
    } catch (err) {
      console.error('Failed to load reports', err);
      return [];
    }
  }

  // ---------- Manual pin placement mode ----------
  // upload.js calls TariqMap.enablePinMode(callback) when a photo has
  // no EXIF GPS data, then the user taps the map to place the report.

  let pinModeActive = false;
  let pinModeCallback = null;
  let tempMarker = null;

  function enablePinMode(callback) {
    pinModeActive = true;
    pinModeCallback = callback;
    document.body.classList.add('map-pin-mode');
    document.getElementById('pinBanner').classList.add('active');
  }

  function disablePinMode() {
    pinModeActive = false;
    pinModeCallback = null;
    document.body.classList.remove('map-pin-mode');
    document.getElementById('pinBanner').classList.remove('active');
    if (tempMarker) {
      map.removeLayer(tempMarker);
      tempMarker = null;
    }
  }

  map.on('click', function (e) {
    if (!pinModeActive) return;

    if (tempMarker) map.removeLayer(tempMarker);

    tempMarker = L.marker(e.latlng, {
      icon: makeIcon('Medium')
    }).addTo(map);

    if (pinModeCallback) {
      pinModeCallback(e.latlng.lat, e.latlng.lng);
    }
  });

  document.getElementById('cancelPinMode').addEventListener('click', disablePinMode);

  window.TariqMap = {
    map,
    loadReports,
    enablePinMode,
    disablePinMode,
    flyTo: (lat, lon) => map.flyTo([lat, lon], 15)
  };

  // Initial load
  loadReports();
})();
