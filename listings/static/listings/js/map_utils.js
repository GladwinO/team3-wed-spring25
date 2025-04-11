// NYC map bounds and configuration
const NYC_BOUNDS = {
  min_lat: 40.477399, // Southernmost point of NYC
  max_lat: 40.917577, // Northernmost point of NYC
  min_lng: -74.25909, // Westernmost point of NYC
  max_lng: -73.700272, // Easternmost point of NYC
};

// Create a Leaflet bounds object from the NYC bounds
const NYC_LEAFLET_BOUNDS = [
  [NYC_BOUNDS.min_lat, NYC_BOUNDS.min_lng], // Southwest corner
  [NYC_BOUNDS.max_lat, NYC_BOUNDS.max_lng], // Northeast corner
];

// NYC center coordinates (approximate)
const NYC_CENTER = [40.7128, -74.006];

// Function to initialize a map with NYC bounds
function initializeNYCMap(mapElementId, options = {}) {
  // Create the map with NYC center
  const map = L.map(mapElementId, {
    center: options.center || NYC_CENTER,
    zoom: options.zoom || 11,
    maxBounds: NYC_LEAFLET_BOUNDS,
    minZoom: options.minZoom || 10,
    ...options,
  });

  // Add the tile layer
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);

  // Set max bounds with padding to prevent scrolling too far outside NYC
  map.setMaxBounds(map.getBounds().pad(0.1));

  return map;
}

// Nominatim API utilities

/**
 * Check if coordinates are within NYC bounds
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @returns {boolean} - True if coordinates are within NYC bounds
 */
function isWithinNYC(lat, lng) {
  return (
    lat >= NYC_BOUNDS.min_lat &&
    lat <= NYC_BOUNDS.max_lat &&
    lng >= NYC_BOUNDS.min_lng &&
    lng <= NYC_BOUNDS.max_lng
  );
}

/**
 * Search for a location using Nominatim
 * @param {string} query - Search query
 * @param {Object} options - Options for the search
 * @param {boolean} options.restrictToNYC - Whether to restrict results to NYC
 * @param {Function} options.onSuccess - Callback for successful search
 * @param {Function} options.onOutOfBounds - Callback for when result is out of NYC bounds
 * @param {Function} options.onNotFound - Callback for when no results are found
 * @param {Function} options.onError - Callback for errors
 */
function searchLocation(query, options = {}) {
  if (!query) {
    if (options.onError) options.onError("No search query provided");
    return;
  }

  const defaultOptions = {
    restrictToNYC: true,
    onSuccess: () => {},
    onOutOfBounds: () =>
      alert(
        "Location is outside of New York City. Please search for a location within NYC."
      ),
    onNotFound: () =>
      alert("Location not found. Please try a different search term."),
    onError: (error) => {
      console.error("Search error:", error);
      alert("Error searching for location. Please try again.");
    },
  };

  const mergedOptions = { ...defaultOptions, ...options };

  // Build the URL
  let url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
    query
  )}`;

  // Add viewbox parameter if restricting to NYC
  if (mergedOptions.restrictToNYC) {
    url += `&viewbox=${NYC_BOUNDS.min_lng},${NYC_BOUNDS.min_lat},${NYC_BOUNDS.max_lng},${NYC_BOUNDS.max_lat}&bounded=1`;
  }

  // Add CORS headers to the request
  fetch(url, {
    headers: {
      Accept: "application/json",
      "User-Agent": "ParkEasy NYC Application (https://parkeasy.example.com)",
    },
    mode: "cors", // Try with explicit CORS mode
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data && data.length > 0) {
        const location = data[0];
        const lat = parseFloat(location.lat);
        const lng = parseFloat(location.lon);

        // Check if within NYC bounds if restriction is enabled
        if (!mergedOptions.restrictToNYC || isWithinNYC(lat, lng)) {
          mergedOptions.onSuccess({
            lat,
            lng,
            displayName: location.display_name,
            raw: location,
          });
        } else {
          mergedOptions.onOutOfBounds();
        }
      } else {
        mergedOptions.onNotFound();
      }
    })
    .catch((error) => {
      console.error("Nominatim API error:", error);

      // Fallback for CORS issues - use a hardcoded NYC location
      if (error.message.includes("CORS") || error.name === "TypeError") {
        console.warn("CORS issue detected, using fallback NYC location");

        // Use a fallback location in NYC (Times Square)
        const fallbackLocation = {
          lat: 40.758,
          lng: -73.9855,
          displayName: "Times Square, Manhattan, NYC",
        };

        alert(
          "Location search is currently unavailable. Using a default NYC location."
        );
        mergedOptions.onSuccess(fallbackLocation);
      } else {
        mergedOptions.onError(error);
      }
    });
}

/**
 * Reverse geocode coordinates to get address
 * @param {number} lat - Latitude
 * @param {number} lng - Longitude
 * @param {Object} options - Options for the reverse geocoding
 * @param {Function} options.onSuccess - Callback for successful reverse geocoding
 * @param {Function} options.onError - Callback for errors
 */
function reverseGeocode(lat, lng, options = {}) {
  const defaultOptions = {
    onSuccess: () => {},
    onError: (error) => {
      console.error("Reverse geocoding error:", error);
    },
  };

  const mergedOptions = { ...defaultOptions, ...options };

  fetch(
    `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`,
    {
      headers: {
        Accept: "application/json",
        "User-Agent": "ParkEasy NYC Application (https://parkeasy.example.com)",
      },
      mode: "cors", // Try with explicit CORS mode
    }
  )
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data && data.display_name) {
        mergedOptions.onSuccess({
          displayName: data.display_name,
          raw: data,
        });
      } else {
        mergedOptions.onError("No address found for these coordinates");
      }
    })
    .catch((error) => {
      console.error("Nominatim API error:", error);

      // Fallback for CORS issues - generate a simple address
      if (error.message.includes("CORS") || error.name === "TypeError") {
        console.warn("CORS issue detected, using fallback address generation");

        // Create a simple address string using the coordinates
        const simplifiedAddress = `Location at ${lat.toFixed(4)}, ${lng.toFixed(
          4
        )}`;

        mergedOptions.onSuccess({
          displayName: simplifiedAddress,
          raw: { display_name: simplifiedAddress },
        });
      } else {
        mergedOptions.onError(error);
      }
    });
}
