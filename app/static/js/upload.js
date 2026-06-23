/* ============================================================
   Tariq.lb -- upload.js
   Handles: file selection/drag-drop, preview, submitting to the
   API, and the manual-pin fallback when a photo has no EXIF GPS.
   ============================================================ */

(function () {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const previewWrap = document.getElementById('previewWrap');
  const previewImg = document.getElementById('previewImg');
  const uploadForm = document.getElementById('uploadForm');
  const submitBtn = document.getElementById('submitBtn');
  const statusLine = document.getElementById('statusLine');
  const manualPinHint = document.getElementById('manualPinHint');
  const resultCard = document.getElementById('resultCard');
  const reportAnotherBtn = document.getElementById('reportAnotherBtn');

  const tabs = document.querySelectorAll('.panel__tab');
  const views = {
    upload: document.getElementById('view-upload'),
    list: document.getElementById('view-list')
  };
  const reportsListEl = document.getElementById('reportsList');

  let selectedFile = null;
  let pendingManualCoords = null; // {lat, lon} once user taps the map
  let awaitingManualPin = false;
  let savedImageFilename = null; // set once the server has stored the file

  // ---------- Tab switching ----------
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      tabs.forEach((t) => t.classList.remove('active'));
      tab.classList.add('active');
      Object.values(views).forEach((v) => v.classList.remove('active'));
      views[tab.dataset.view].classList.add('active');

      if (tab.dataset.view === 'list') {
        refreshReportsList();
      }
    });
  });

  // ---------- File selection / preview ----------
  function handleFile(file) {
    if (!file) return;
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      showStatus('Please choose a JPG or PNG image.', 'error');
      return;
    }
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      previewWrap.classList.add('active');
    };
    reader.readAsDataURL(file);
    submitBtn.disabled = false;
    hideStatus();
    resetResultCard();
  }

  fileInput.addEventListener('change', (e) => handleFile(e.target.files[0]));

  ['dragover', 'dragenter'].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });
  ['dragleave', 'drop'].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });
  dropzone.addEventListener('drop', (e) => {
    const file = e.dataTransfer.files[0];
    if (file) {
      fileInput.files = e.dataTransfer.files;
      handleFile(file);
    }
  });

  // ---------- Status helpers ----------
  function showStatus(msg, type) {
    statusLine.textContent = msg;
    statusLine.className = 'status-line active' + (type ? ' ' + type : '');
  }
  function hideStatus() {
    statusLine.className = 'status-line';
  }

  function resetResultCard() {
    resultCard.classList.remove('active');
    manualPinHint.classList.remove('active');
  }

  // ---------- Submit ----------
  uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    await submitReport();
  });

  async function submitReport(manualLat, manualLon) {
    submitBtn.disabled = true;
    showStatus('Analyzing photo and reading location data…', '');

    const formData = new FormData();
    formData.append('image', selectedFile);
    if (savedImageFilename) {
      formData.append('existing_image_filename', savedImageFilename);
    }
    if (manualLat !== undefined && manualLon !== undefined) {
      formData.append('manual_lat', manualLat);
      formData.append('manual_lon', manualLon);
    }

    try {
      const res = await fetch('/api/reports', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      if (res.status === 422 && data.error === 'no_gps') {
        // No GPS in image -- prompt for manual pin placement
        awaitingManualPin = true;
        savedImageFilename = data.image_filename;
        showStatus(data.message, 'error');
        manualPinHint.classList.add('active');
        window.TariqMap.enablePinMode((lat, lon) => {
          pendingManualCoords = { lat, lon };
          showStatus('Location selected. Submitting report…', '');
          submitReport(lat, lon);
        });
        return;
      }

      if (!res.ok) {
        showStatus(data.error || 'Something went wrong. Please try again.', 'error');
        submitBtn.disabled = false;
        return;
      }

      // Success
      awaitingManualPin = false;
      window.TariqMap.disablePinMode();
      hideStatus();
      showResult(data);
      await window.TariqMap.loadReports();
      window.TariqMap.flyTo(data.latitude, data.longitude);

    } catch (err) {
      console.error(err);
      showStatus('Network error -- could not submit report.', 'error');
      submitBtn.disabled = false;
    }
  }

  function showResult(report) {
    document.getElementById('result-type').textContent = report.damage_type;

    const severityEl = document.getElementById('result-severity');
    severityEl.innerHTML = `<span class="badge badge--${report.severity_level.toLowerCase()}">${report.severity_level}</span>`;

    document.getElementById('result-confidence').textContent = Math.round(report.confidence_score * 100) + '%';
    document.getElementById('result-source').textContent = report.location_source === 'exif' ? 'Photo GPS' : 'Manual Pin';

    resultCard.classList.add('active');
    uploadForm.style.display = 'none';
  }

  reportAnotherBtn.addEventListener('click', () => {
    selectedFile = null;
    pendingManualCoords = null;
    savedImageFilename = null;
    fileInput.value = '';
    previewWrap.classList.remove('active');
    resultCard.classList.remove('active');
    manualPinHint.classList.remove('active');
    uploadForm.style.display = 'block';
    submitBtn.disabled = true;
    hideStatus();
  });

  // ---------- Reports list ----------
  async function refreshReportsList() {
    reportsListEl.innerHTML = '<div class="list-empty">Loading reports&hellip;</div>';
    try {
      const res = await fetch('/api/reports');
      const reports = await res.json();
      renderReportsList(reports);
    } catch (err) {
      reportsListEl.innerHTML = '<div class="list-empty">Could not load reports.</div>';
    }
  }

  function renderReportsList(reports) {
    if (!reports.length) {
      reportsListEl.innerHTML = '<div class="list-empty">No reports yet. Be the first to flag a damaged road.</div>';
      return;
    }

    reportsListEl.innerHTML = reports.map((r) => `
      <div class="report-card report-card--${r.severity_level.toLowerCase()}" onclick="window.location.href='/report/${r.id}'">
        <img class="report-card__thumb" src="${r.image_url}" alt="${r.damage_type}" />
        <div class="report-card__body">
          <div class="report-card__top">
            <div class="report-card__type">${r.damage_type}</div>
            <span class="badge badge--${r.severity_level.toLowerCase()}">${r.severity_level}</span>
          </div>
          <div class="report-card__meta">#${r.id} &middot; ${r.created_at} &middot; ${r.location_source === 'exif' ? 'Photo GPS' : 'Manual Pin'}</div>
        </div>
      </div>
    `).join('');
  }
})();
