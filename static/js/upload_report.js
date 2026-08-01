(function () {
  const form = document.getElementById('uploadForm');
  const mapElement = document.getElementById('map');
  const locationDataElement = document.getElementById('upload-location-data');

  if (!form || !mapElement || !locationDataElement || typeof L === 'undefined') {
    return;
  }

  const locationData = JSON.parse(locationDataElement.textContent);
  const bounds = locationData.bounds;
  const polygon = locationData.polygon;
  const defaultLat = Number(form.dataset.defaultLat || 33.85);
  const defaultLng = Number(form.dataset.defaultLng || 35.86);
  const defaultZoom = Number(form.dataset.defaultZoom || 9);
  const searchUrl = form.dataset.searchUrl;

  const imageInput = document.getElementById('image');
  const dropZone = document.getElementById('dropZone');
  const imageError = document.getElementById('imageError');
  const gpsStatus = document.getElementById('gpsStatus');
  const previewWrapper = document.getElementById('imagePreviewWrapper');
  const previewName = document.getElementById('previewName');
  const imagePreview = document.getElementById('imagePreview');

  const localitySearch = document.getElementById('localitySearch');
  const localityResults = document.getElementById('localityResults');
  const searchError = document.getElementById('searchError');
  const locationError = document.getElementById('locationError');
  const locationStatus = document.getElementById('locationStatus');
  const useCurrentLocationButton = document.getElementById('useCurrentLocationButton');

  const latInput = document.getElementById('lat');
  const lngInput = document.getElementById('lng');
  const locationSourceInput = document.getElementById('locationSource');
  const selectedCoords = document.getElementById('selectedCoords');
  const selectedLocality = document.getElementById('selectedLocality');
  const selectedSource = document.getElementById('selectedSource');
  const selectedSearchPlace = document.getElementById('selectedSearchPlace');

  const summaryImage = document.getElementById('summaryImage');
  const summaryLocality = document.getElementById('summaryLocality');
  const summaryCoords = document.getElementById('summaryCoords');
  const summarySource = document.getElementById('summarySource');
  const submitButton = document.getElementById('submitButton');
  const clearButton = document.getElementById('clearButton');

  const progressSteps = {
    image: document.querySelector('[data-progress-step="image"]'),
    location: document.querySelector('[data-progress-step="location"]'),
    submit: document.querySelector('[data-progress-step="submit"]')
  };

  const savedImageInput = form.querySelector('input[name="saved_image_path"]');
  const searchCache = new Map();
  let searchTimer = null;
  let searchRequestId = 0;
  let highlightedResultIndex = -1;
  let currentResults = [];
  let marker = null;
  let lastValidLatLng = null;
  let highlightCircle = null;
  let locationFocusTimeout = null;
  let currentLocalityLabel = '';

  function setMessage(element, message, type) {
    if (!element) {
      return;
    }

    element.textContent = message || '';

    if (element.classList.contains('inline-status')) {
      element.classList.remove('is-info', 'is-error', 'is-success');
      element.classList.add(type === 'error' ? 'is-error' : type === 'success' ? 'is-success' : 'is-info');
    }
  }

  function sourceLabel(source) {
    if (source === 'gps') {
      return 'EXIF GPS';
    }
    if (source === 'browser') {
      return 'Browser location';
    }
    if (source === 'search') {
      return 'Search';
    }
    return 'Manual map selection';
  }

  function coordinateLabel(lat, lng) {
    return `${Number(lat).toFixed(6)}, ${Number(lng).toFixed(6)}`;
  }

  function resultMetaLabel(result) {
    return [result.district, result.governorate, result.type]
      .filter(Boolean)
      .join(' - ') || 'Lebanon locality';
  }

  function leafletBoundsFromResult(boundsData) {
    if (!boundsData) {
      return null;
    }

    const south = Number(boundsData.south);
    const north = Number(boundsData.north);
    const west = Number(boundsData.west);
    const east = Number(boundsData.east);
    const values = [south, north, west, east];

    if (!values.every(Number.isFinite) || south > north || west > east) {
      return null;
    }

    return L.latLngBounds([south, west], [north, east]);
  }

  function updateSelectedSearchPlace(result) {
    if (!selectedSearchPlace) {
      return;
    }

    const title = selectedSearchPlace.querySelector('strong');
    const copy = selectedSearchPlace.querySelector('p');

    if (!result) {
      selectedSearchPlace.hidden = true;
      if (title) {
        title.textContent = 'No locality selected';
      }
      return;
    }

    selectedSearchPlace.hidden = false;

    if (title) {
      title.textContent = result.display_name || result.name || 'Selected locality';
    }

    if (copy) {
      copy.textContent = `Placed at the locality center from ${resultMetaLabel(result)}. Zoomed-in map labels show nearby roads, shops, and landmarks; drag the marker center to the exact damaged road point.`;
    }
  }

  function isValidNumber(value) {
    return Number.isFinite(Number(value));
  }

  function isInsideBounds(lat, lng) {
    return (
      lat >= bounds.south &&
      lat <= bounds.north &&
      lng >= bounds.west &&
      lng <= bounds.east
    );
  }

  function isInsidePolygon(lat, lng) {
    let inside = false;
    const pointX = lng;
    const pointY = lat;
    let previous = polygon[polygon.length - 1];

    polygon.forEach((current) => {
      const currentY = current[0];
      const currentX = current[1];
      const previousY = previous[0];
      const previousX = previous[1];
      const intersects = (currentY > pointY) !== (previousY > pointY);

      if (intersects) {
        const slopeX = ((previousX - currentX) * (pointY - currentY)) / (previousY - currentY) + currentX;
        if (pointX < slopeX) {
          inside = !inside;
        }
      }

      previous = current;
    });

    return inside;
  }

  function isInsideLebanon(lat, lng) {
    if (!isValidNumber(lat) || !isValidNumber(lng)) {
      return false;
    }

    const numericLat = Number(lat);
    const numericLng = Number(lng);

    return isInsideBounds(numericLat, numericLng) && isInsidePolygon(numericLat, numericLng);
  }

  function updateProgress() {
    const hasImage = Boolean(savedImageInput) || Boolean(imageInput.files && imageInput.files.length);
    const hasLocation = Boolean(latInput.value && lngInput.value);

    progressSteps.image.classList.toggle('is-complete', hasImage);
    progressSteps.image.classList.toggle('is-active', !hasImage);
    progressSteps.location.classList.toggle('is-complete', hasLocation);
    progressSteps.location.classList.toggle('is-active', hasImage && !hasLocation);
    progressSteps.submit.classList.toggle('is-active', hasImage && hasLocation);
  }

  function updateSummary() {
    const coords = latInput.value && lngInput.value
      ? coordinateLabel(latInput.value, lngInput.value)
      : 'None selected';
    const locality = currentLocalityLabel || 'None selected';
    const source = sourceLabel(locationSourceInput.value);

    selectedCoords.textContent = coords;
    selectedLocality.textContent = locality;
    selectedSource.textContent = source;
    summaryCoords.textContent = coords;
    summaryLocality.textContent = locality;
    summarySource.textContent = source;
    updateProgress();
  }

  function setLocationError(message) {
    locationError.textContent = message || '';
    if (message) {
      setMessage(locationStatus, message, 'error');
    }
  }

  const lebanonBounds = L.latLngBounds(
    [bounds.south, bounds.west],
    [bounds.north, bounds.east]
  );

  const map = L.map('map', {
    maxBounds: lebanonBounds,
    maxBoundsViscosity: 1.0,
    minZoom: 8
  }).setView([defaultLat, defaultLng], defaultZoom);

  const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 20,
    maxNativeZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const satelliteLayer = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    {
      maxZoom: 20,
      attribution: 'Tiles &copy; Esri'
    }
  );

  L.control.layers(
    {
      Streets: streetLayer,
      Satellite: satelliteLayer
    },
    null,
    {
      collapsed: false,
      position: 'topright'
    }
  ).addTo(map);

  let mapSizeFrame = null;

  function syncMapSize() {
    map.invalidateSize({
      pan: false,
      debounceMoveend: true
    });
  }

  function requestMapSizeSync() {
    if (mapSizeFrame) {
      window.cancelAnimationFrame(mapSizeFrame);
    }

    mapSizeFrame = window.requestAnimationFrame(() => {
      syncMapSize();
      mapSizeFrame = null;
    });
  }

  if (typeof ResizeObserver !== 'undefined') {
    const mapResizeObserver = new ResizeObserver(requestMapSizeSync);
    mapResizeObserver.observe(mapElement);

    const mapWrapper = mapElement.closest('.map-wrap');
    if (mapWrapper) {
      mapResizeObserver.observe(mapWrapper);
    }
  }

  ['pointerenter', 'pointerdown', 'touchstart', 'focusin'].forEach((eventName) => {
    mapElement.addEventListener(eventName, requestMapSizeSync, {
      passive: true
    });
  });

  window.addEventListener('resize', requestMapSizeSync);

  const boundary = L.polygon(polygon, {
    color: '#4a7c59',
    weight: 2,
    fillColor: '#4a7c59',
    fillOpacity: 0.06,
    opacity: 0.95
  }).addTo(map);

  const markerIcon = L.divIcon({
    className: 'road-marker',
    html: '<span></span>',
    iconSize: [38, 46],
    iconAnchor: [19, 41]
  });

  function highlightSelectedLocation(lat, lng, boundsData) {
    const numericLat = Number(lat);
    const numericLng = Number(lng);
    const mapWrapper = mapElement.closest('.map-wrap');
    const selectedBounds = leafletBoundsFromResult(boundsData);

    if (!Number.isFinite(numericLat) || !Number.isFinite(numericLng)) {
      return;
    }

    if (locationFocusTimeout) {
      window.clearTimeout(locationFocusTimeout);
      locationFocusTimeout = null;
    }

    if (highlightCircle) {
      map.removeLayer(highlightCircle);
      highlightCircle = null;
    }

    window.requestAnimationFrame(() => {
      const markerElement = marker ? marker.getElement() : null;

      if (markerElement) {
        markerElement.classList.remove('is-location-highlighted');
        void markerElement.offsetWidth;
        markerElement.classList.add('is-location-highlighted');
      }

      if (mapWrapper) {
        mapWrapper.classList.add('is-location-focused');
      }

      if (selectedBounds) {
        highlightCircle = L.rectangle(selectedBounds, {
          color: '#7b0d1e',
          weight: 2,
          opacity: 0.95,
          fillColor: '#4a7c59',
          fillOpacity: 0.10,
          interactive: false,
          className: 'selected-location-ring'
        }).addTo(map);
      } else {
        highlightCircle = L.circle([numericLat, numericLng], {
          radius: 850,
          color: '#7b0d1e',
          weight: 2,
          opacity: 0.95,
          fillColor: '#4a7c59',
          fillOpacity: 0.12,
          interactive: false,
          className: 'selected-location-ring'
        }).addTo(map);
      }

      highlightCircle.bringToFront();

      if (marker) {
        marker.setZIndexOffset(1000);
      }

      locationFocusTimeout = window.setTimeout(() => {
        if (markerElement) {
          markerElement.classList.remove('is-location-highlighted');
        }

        if (mapWrapper) {
          mapWrapper.classList.remove('is-location-focused');
        }

        if (highlightCircle) {
          map.removeLayer(highlightCircle);
          highlightCircle = null;
        }
      }, 4200);
    });
  }

  function moveMarker(lat, lng, source, locality, options) {
    const numericLat = Number(lat);
    const numericLng = Number(lng);
    const markerOptions = options || {};

    if (!isInsideLebanon(numericLat, numericLng)) {
      setLocationError('Please select a location inside Lebanon.');
      return false;
    }

    setLocationError('');

    if (!marker) {
      marker = L.marker([numericLat, numericLng], {
        draggable: true,
        icon: markerIcon
      }).addTo(map);

      marker.on('dragend', () => {
        const position = marker.getLatLng();

        if (!isInsideLebanon(position.lat, position.lng)) {
          if (lastValidLatLng) {
            marker.setLatLng(lastValidLatLng);
          }
          setLocationError('Please select a location inside Lebanon.');
          return;
        }

        latInput.value = position.lat.toFixed(6);
        lngInput.value = position.lng.toFixed(6);
        lastValidLatLng = position;
        setMessage(locationStatus, 'Marker moved exactly to that road point. Zoom in for nearby streets, shops, and landmarks.', 'success');
        updateSelectedSearchPlace(null);
        updateSummary();
      });
    } else {
      marker.setLatLng([numericLat, numericLng]);
    }

    lastValidLatLng = L.latLng(numericLat, numericLng);
    latInput.value = numericLat.toFixed(6);
    lngInput.value = numericLng.toFixed(6);
    locationSourceInput.value = source || 'manual';
    currentLocalityLabel = locality || currentLocalityLabel || 'Selected point in Lebanon';

    if (markerOptions.zoom) {
      const targetZoom = Math.max(map.getZoom(), markerOptions.zoomLevel || 15);
      const resultBounds = leafletBoundsFromResult(markerOptions.bounds);

      if (markerOptions.fitBounds && resultBounds) {
        map.fitBounds(resultBounds, {
          animate: true,
          padding: [34, 34],
          maxZoom: targetZoom
        });
      } else if (markerOptions.flyTo && typeof map.flyTo === 'function') {
        map.flyTo([numericLat, numericLng], targetZoom, {
          animate: true,
          duration: 0.9,
          easeLinearity: 0.25
        });
      } else {
        map.setView([numericLat, numericLng], targetZoom, {
          animate: true
        });
      }
    }

    if (markerOptions.highlight) {
      highlightSelectedLocation(numericLat, numericLng, markerOptions.bounds);
    }

    setMessage(locationStatus, 'Location selected inside Lebanon. The marker center is the submitted point; zoom in for nearby streets, shops, and landmarks.', 'success');
    updateSummary();
    return true;
  }

  map.fitBounds(boundary.getBounds(), { padding: [18, 18] });
  requestMapSizeSync();

  map.on('click', (event) => {
    syncMapSize();

    const clickedLatLng = event.originalEvent
      ? map.mouseEventToLatLng(event.originalEvent)
      : event.latlng;

    const selected = moveMarker(
      clickedLatLng.lat,
      clickedLatLng.lng,
      'manual',
      'Selected point in Lebanon',
      {
        highlight: true
      }
    );

    if (selected) {
      localitySearch.value = '';
      updateSelectedSearchPlace(null);
    }
  });

  function clearPreview() {
    imagePreview.removeAttribute('src');
    previewWrapper.hidden = true;
    previewName.textContent = 'No image selected';
  }

  function validateFile(file) {
    if (!file) {
      return savedImageInput ? '' : 'Please choose an image to upload.';
    }

    const allowedTypes = ['image/jpeg', 'image/png'];
    const allowedExtension = /\.(jpe?g|png)$/i.test(file.name || '');
    const maxSize = 5 * 1024 * 1024;

    if (!allowedTypes.includes(file.type) && !allowedExtension) {
      return 'Invalid file type. Please choose a JPG, JPEG, or PNG image.';
    }

    if (file.size > maxSize) {
      return 'The selected image is larger than 5 MB.';
    }

    return '';
  }

  imageInput.addEventListener('change', () => {
    const file = imageInput.files[0];
    const error = validateFile(file);

    imageError.textContent = error;

    if (error) {
      imageInput.value = '';
      clearPreview();
      setMessage(gpsStatus, error, 'error');
      updateProgress();
      return;
    }

    if (!file) {
      clearPreview();
      setMessage(gpsStatus, 'Choose an image.', 'info');
      updateProgress();
      return;
    }

    imagePreview.src = URL.createObjectURL(file);
    previewName.textContent = file.name;
    previewWrapper.hidden = false;
    summaryImage.textContent = file.name;
    setMessage(gpsStatus, 'Image selected successfully. GPS will be checked after upload.', 'success');
    updateProgress();
  });

  ['dragenter', 'dragover'].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add('is-dragging');
    });
  });

  ['dragleave', 'drop'].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove('is-dragging');
    });
  });

  dropZone.addEventListener('drop', (event) => {
    const files = event.dataTransfer.files;
    if (!files.length) {
      return;
    }

    imageInput.files = files;
    imageInput.dispatchEvent(new Event('change'));
  });

  function hideSearchResults() {
    localityResults.hidden = true;
    localitySearch.setAttribute('aria-expanded', 'false');
    highlightedResultIndex = -1;
    requestMapSizeSync();
  }

  function updateHighlightedResult() {
    Array.from(localityResults.querySelectorAll('.search-option')).forEach((button, index) => {
      button.classList.toggle('is-highlighted', index === highlightedResultIndex);
      if (index === highlightedResultIndex) {
        button.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  function appendResultCopy(parent, titleText, detailText) {
    const title = document.createElement('strong');
    const detail = document.createElement('span');

    title.textContent = titleText;
    detail.textContent = detailText;
    parent.append(title, detail);
  }

  function renderSearchLoading(query) {
    currentResults = [];
    highlightedResultIndex = -1;
    localityResults.innerHTML = '';

    const loading = document.createElement('div');
    loading.className = 'search-empty is-loading';
    appendResultCopy(
      loading,
      'Searching Lebanon...',
      `Looking for "${query}" in cities, towns, villages, municipalities, and localities.`
    );
    localityResults.appendChild(loading);
    localityResults.hidden = false;
    localitySearch.setAttribute('aria-expanded', 'true');
    requestMapSizeSync();
  }

  function renderSearchResults(results, message) {
    currentResults = results || [];
    localityResults.innerHTML = '';

    if (!currentResults.length) {
      const empty = document.createElement('div');
      empty.className = 'search-empty';
      appendResultCopy(
        empty,
        message || 'No Lebanese city or village found.',
        'Try another city, town, or village name.'
      );
      localityResults.appendChild(empty);
      localityResults.hidden = false;
      localitySearch.setAttribute('aria-expanded', 'true');
      requestMapSizeSync();
      return;
    }

    currentResults.forEach((result, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'search-option';
      button.id = `locality-option-${index}`;
      button.setAttribute('role', 'option');
      button.dataset.index = String(index);
      appendResultCopy(
        button,
        result.display_name || result.name || 'Lebanon locality',
        resultMetaLabel(result)
      );
      button.addEventListener('click', () => selectSearchResult(index));
      localityResults.appendChild(button);
    });

    localityResults.hidden = false;
    localitySearch.setAttribute('aria-expanded', 'true');
    requestMapSizeSync();
  }

  async function runSearch(query) {
    const normalizedQuery = query.trim();

    searchError.textContent = '';

    if (normalizedQuery.length < 1) {
      hideSearchResults();
      return;
    }

    if (searchCache.has(normalizedQuery.toLowerCase())) {
      renderSearchResults(searchCache.get(normalizedQuery.toLowerCase()));
      return;
    }

    const requestId = ++searchRequestId;
    renderSearchLoading(normalizedQuery);

    try {
      const response = await fetch(`${searchUrl}?q=${encodeURIComponent(normalizedQuery)}`);
      const data = await response.json();

      if (requestId !== searchRequestId) {
        return;
      }

      if (!response.ok || data.error) {
        throw new Error(data.error || 'Failed geocoder request.');
      }

      const results = data.results || [];
      searchCache.set(normalizedQuery.toLowerCase(), results);
      renderSearchResults(results, data.message);
    } catch (error) {
      searchError.textContent = 'Could not search Lebanese cities right now. Please click the map manually.';
      renderSearchResults([], 'Search is temporarily unavailable.');
    }
  }

  function selectSearchResult(index) {
    const result = currentResults[index];
    if (!result) {
      return;
    }

    const accepted = moveMarker(result.lat, result.lng, 'search', result.display_name, {
      zoom: true,
      zoomLevel: 18,
      flyTo: true,
      fitBounds: true,
      bounds: result.bounding_box,
      highlight: true
    });

    if (!accepted) {
      searchError.textContent = 'Search result outside Lebanon was rejected.';
      return;
    }

    localitySearch.value = result.display_name;
    updateSelectedSearchPlace(result);
    setMessage(
      locationStatus,
      `${result.display_name} selected. The marker was placed at the locality center; zoomed-in OpenStreetMap labels can help you use nearby roads, shops, and landmarks before submitting.`,
      'success'
    );
    hideSearchResults();
  }

  localitySearch.addEventListener('input', () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => {
      runSearch(localitySearch.value);
    }, 380);
  });

  localitySearch.addEventListener('keydown', (event) => {
    if (localityResults.hidden || !currentResults.length) {
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      highlightedResultIndex = Math.min(highlightedResultIndex + 1, currentResults.length - 1);
      updateHighlightedResult();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      highlightedResultIndex = Math.max(highlightedResultIndex - 1, 0);
      updateHighlightedResult();
    } else if (event.key === 'Enter' && highlightedResultIndex >= 0) {
      event.preventDefault();
      selectSearchResult(highlightedResultIndex);
    } else if (event.key === 'Escape') {
      hideSearchResults();
    }
  });

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.search-box')) {
      hideSearchResults();
    }
  });

  useCurrentLocationButton.addEventListener('click', () => {
    if (!navigator.geolocation) {
      setMessage(locationStatus, 'Your browser does not support current-location detection.', 'error');
      return;
    }

    useCurrentLocationButton.disabled = true;
    useCurrentLocationButton.textContent = 'Finding location...';

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;

        if (!isInsideLebanon(lat, lng)) {
          setLocationError('Browser location is outside Lebanon. Please choose the road location manually on the map.');
        } else {
          moveMarker(lat, lng, 'browser', 'Browser GPS location', {
            zoom: true,
            zoomLevel: 18,
            flyTo: true,
            highlight: true
          });
          updateSelectedSearchPlace(null);
        }

        useCurrentLocationButton.disabled = false;
        useCurrentLocationButton.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 2v3"></path><path d="M12 19v3"></path><path d="M2 12h3"></path><path d="M19 12h3"></path><circle cx="12" cy="12" r="7"></circle><circle cx="12" cy="12" r="2"></circle></svg>Use my current location';
      },
      (error) => {
        let message = 'Could not get your current location. Select the road on the map.';

        if (error.code === error.PERMISSION_DENIED) {
          message = 'Location permission was denied. Select the road on the map.';
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          message = 'Current location is unavailable. Select the road on the map.';
        } else if (error.code === error.TIMEOUT) {
          message = 'Location lookup timed out. Select the road on the map.';
        }

        setMessage(locationStatus, message, 'error');
        useCurrentLocationButton.disabled = false;
        useCurrentLocationButton.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 2v3"></path><path d="M12 19v3"></path><path d="M2 12h3"></path><path d="M19 12h3"></path><circle cx="12" cy="12" r="7"></circle><circle cx="12" cy="12" r="2"></circle></svg>Use my current location';
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000
      }
    );
  });

  clearButton.addEventListener('click', () => {
    window.location.href = form.action;
  });

  form.addEventListener('submit', (event) => {
    const file = imageInput.files[0];
    const imageValidationError = validateFile(file);

    imageError.textContent = imageValidationError;

    if (imageValidationError) {
      event.preventDefault();
      setMessage(gpsStatus, imageValidationError, 'error');
      return;
    }

    if (!latInput.value || !lngInput.value) {
      if (savedImageInput) {
        event.preventDefault();
        setLocationError('Please select a location inside Lebanon before submitting.');
        return;
      }

      setMessage(gpsStatus, 'Submitting without manual coordinates. The server will use EXIF GPS if it exists.', 'info');
    } else if (!isInsideLebanon(latInput.value, lngInput.value)) {
      event.preventDefault();
      setLocationError('Please select a location inside Lebanon.');
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = 'Submitting report...';
  });

  window.addEventListener('load', () => {
    setTimeout(requestMapSizeSync, 150);
    setTimeout(requestMapSizeSync, 500);
  });

  updateSelectedSearchPlace(null);
  updateSummary();
  updateProgress();
})();
