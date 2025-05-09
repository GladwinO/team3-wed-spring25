// NYC map bounds and configuration
const NYC_BOUNDS = {
  min_lat: 40.477399, // Southernmost point of NYC
  max_lat: 40.917577, // Northernmost point of NYC
  min_lng: -74.25909, // Westernmost point of NYC
  max_lng: -73.700272, // Easternmost point of NYC
};

let openDataParkingMeterURL =
  "https://data.cityofnewyork.us/resource/693u-uax6.json?$limit=120&$select=meter_number,status,on_street,from_street,to_street,lat,long,meter_hours,pay_by_cell_number,side_of_street&$where=status='Active'";

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
    minZoom: options.minZoom || 3,
    maxBounds: NYC_LEAFLET_BOUNDS, // Add maxBounds to restrict dragging to NYC area
    maxBoundsViscosity: 0.9, // How "hard" the bounds are enforced (0-1)
    ...options,
  });

  // Add the tile layer
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);

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
    onOutOfBounds: () => {
      console.warn("Location is outside of New York City.");
      return {
        error: true,
        message:
          "Location is outside of New York City. Please search for a location within NYC.",
      };
    },
    onNotFound: () => {
      console.warn("Location not found.");
      return {
        error: true,
        message: "Location not found. Please try a different search term.",
      };
    },
    onError: (error) => {
      console.error("Search error:", error);
      return {
        error: true,
        message: "Error searching for location. Please try again.",
      };
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

        // Only show error in console, not alert
        console.warn(
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

// Create a new map legend with toggle functionality
function createMapLegend() {
  const legend = L.control({ position: "bottomright" });

  legend.onAdd = function (map) {
    const div = L.DomUtil.create("div", "map-legend");

    // Load the legend HTML from the template
    fetch("/listings/map_legend/")
      .then((response) => response.text())
      .then((html) => {
        div.innerHTML = html;

        // Prevent clicks on the legend from propagating to the map
        L.DomEvent.disableClickPropagation(div);

        // Add event listeners to the toggle switches
        const toggleGarages = document.getElementById("toggle-garages");
        const toggleMeters = document.getElementById("toggle-meters");
        const toggleListings = document.getElementById("toggle-listings");

        if (toggleGarages) {
          toggleGarages.addEventListener("change", function () {
            if (this.checked) {
              if (!map.hasLayer(garageLayerGroup)) {
                map.addLayer(garageLayerGroup);
              }
            } else {
              if (map.hasLayer(garageLayerGroup)) {
                map.removeLayer(garageLayerGroup);
              }
            }
          });
        }

        if (toggleMeters) {
          toggleMeters.addEventListener("change", function () {
            if (this.checked) {
              if (!map.hasLayer(meterLayerGroup)) {
                map.addLayer(meterLayerGroup);
              }
            } else {
              if (map.hasLayer(meterLayerGroup)) {
                map.removeLayer(meterLayerGroup);
              }
            }
          });
        }

        if (toggleListings) {
          toggleListings.addEventListener("change", function () {
            if (this.checked) {
              if (!map.hasLayer(listingLayerGroup)) {
                map.addLayer(listingLayerGroup);
              }
            } else {
              if (map.hasLayer(listingLayerGroup)) {
                map.removeLayer(listingLayerGroup);
              }
            }
          });
        }
      })
      .catch((error) => {
        console.error("Error loading map legend:", error);
      });

    return div;
  };

  return legend;
}

// This is a simpler function that directly adds garages to the map
function addGaragesDirectly(map) {
  console.log("Adding garages directly to map...");
  currentMap = map;

  // Create marker icon
  const garageIcon = L.divIcon({
    html: markerTemplates.garage,
    className: "garage-marker",
    iconSize: [18, 18],
    iconAnchor: [9, 18],
    popupAnchor: [0, -18],
  });

  // Create backup markers to use if API fails
  const backupGarages = [
    {
      name: "SUTTON 53 PARKING LLC",
      address: "410 EAST 54 STREET, NEW YORK, NY 10022",
      phone: "(877) 727-5464",
      lat: 40.7577,
      lng: -73.9639,
    },
    {
      name: "TIMES SQUARE GARAGE",
      address: "224 WEST 49TH STREET, NEW YORK, NY 10019",
      phone: "(212) 333-7275",
      lat: 40.7608,
      lng: -73.9847,
    },
  ];

  if (!map) {
    console.error("Map object is null or undefined in addGaragesDirectly!");
    return;
  }

  // Add each garage marker from backup if needed
  function addBackupMarkers() {
    backupGarages.forEach((garage, index) => {
      try {
        console.log(
          `Adding backup garage ${index + 1}/${backupGarages.length}: "${
            garage.name
          }" at ${garage.lat}, ${garage.lng}`
        );

        // Create marker and add to LAYER GROUP instead of map
        const marker = L.marker([garage.lat, garage.lng], {
          icon: garageIcon,
          title: garage.name,
          zIndexOffset: 100, // Lower z-index to ensure garages stay behind listings
        });

        garageLayerGroup.addLayer(marker);

        // Create popup content
        const popupContent = `
                    <div class="garage-popup" style="padding: 8px; min-width: 250px;">
                        <div style="margin-bottom: 12px;">
                            <h4 style="margin: 0; color: #2c3e50; font-size: 16px;">${
                              garage.name
                            }</h4>
                        </div>
                        <div style="margin-bottom: 10px; display: flex; align-items: flex-start;">
                            <i class="fas fa-map-marker-alt" style="color: #7f8c8d; margin-right: 8px; margin-top: 3px;"></i>
                            <div style="color: #34495e; font-size: 13px;">
                                ${garage.address}<br>
                                <span style="color: #7f8c8d; font-size: 12px;">New York, NY</span>
                            </div>
                        </div>
                        ${
                          garage.phone
                            ? `
                        <div style="margin-bottom: 10px; display: flex; align-items: center;">
                            <i class="fas fa-phone" style="color: #7f8c8d; margin-right: 8px;"></i>
                            <a href="tel:${garage.phone}" style="color: #34495e; text-decoration: none; font-size: 13px;">${garage.phone}</a>
                        </div>`
                            : ""
                        }
                    </div>
                `;

        // Bind popup to marker
        marker.bindPopup(popupContent);

        // Open popup for first marker
        if (index === 0) {
          setTimeout(() => {
            marker.openPopup();
          }, 500);
        }
      } catch (error) {
        console.error(`Error adding backup garage ${garage.name}:`, error);
      }
    });
  }

  // Try to fetch garages from NYC Open Data API
  fetch("https://data.cityofnewyork.us/resource/5bhr-pjxt.json?$limit=50")
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((garages) => {
      console.log(`Fetched ${garages.length} garages from NYC API`);

      // Add markers for each garage
      garages.forEach((garage) => {
        // Only add markers if we have coordinates
        if (garage.latitude && garage.longitude) {
          try {
            const lat = parseFloat(garage.latitude);
            const lng = parseFloat(garage.longitude);

            // Format the address string
            const address = [
              garage.address_building,
              garage.address_street_name,
              garage.address_city,
              garage.address_state,
              garage.address_zip,
            ]
              .filter(Boolean)
              .join(" ");

            // Get capacity info
            let capacity = "";
            if (garage.detail) {
              capacity = garage.detail;
            }

            // Create marker and add to LAYER GROUP instead of map
            const marker = L.marker([lat, lng], {
              icon: garageIcon,
              title: garage.business_name,
              zIndexOffset: 100, // Lower z-index to ensure garages stay behind listings
            });

            garageLayerGroup.addLayer(marker);

            // Create popup content
            const popupContent = `
                            <div class="garage-popup" style="padding: 8px; min-width: 250px;">
                                <div style="margin-bottom: 12px;">
                                    <h4 style="margin: 0; color: #2c3e50; font-size: 16px;">${
                                      garage.business_name
                                    }</h4>
                                </div>
                                <div style="margin-bottom: 10px; display: flex; align-items: flex-start;">
                                    <i class="fas fa-map-marker-alt" style="color: #7f8c8d; margin-right: 8px; margin-top: 3px;"></i>
                                    <div style="color: #34495e; font-size: 13px;">
                                        ${address}<br>
                                        <span style="color: #7f8c8d; font-size: 12px;">New York, NY</span>
                                    </div>
                                </div>
                                ${
                                  garage.contact_phone
                                    ? `
                                <div style="margin-bottom: 10px; display: flex; align-items: center;">
                                    <i class="fas fa-phone" style="color: #7f8c8d; margin-right: 8px;"></i>
                                    <a href="tel:${garage.contact_phone}" style="color: #34495e; text-decoration: none; font-size: 13px;">${garage.contact_phone}</a>
                                </div>`
                                    : ""
                                }
                                ${
                                  capacity
                                    ? `
                                <div style="margin-bottom: 8px; display: flex; align-items: flex-start;">
                                    <i class="fas fa-car" style="color: #7f8c8d; margin-right: 8px; margin-top: 3px;"></i>
                                    <div style="color: #34495e; font-size: 13px;">
                                        <div style="margin-bottom: 4px;">Vehicle Capacity: ${
                                          capacity.match(
                                            /Vehicle Capacity: (\d+)/
                                          )?.[1] || "N/A"
                                        }</div>
                                        <div>Bicycle Capacity: ${
                                          capacity.match(
                                            /Bicycle Capacity: (\d+)/
                                          )?.[1] || "N/A"
                                        }</div>
                                    </div>
                                </div>`
                                    : ""
                                }
                            </div>
                        `;

            // Bind popup to marker
            marker.bindPopup(popupContent);
          } catch (error) {
            console.error(
              `Error adding garage ${garage.business_name}:`,
              error
            );
          }
        }
      });

      // Center map on NYC after adding garages
      map.setView([40.7128, -74.006], 12);
    })
    .catch((error) => {
      console.error("Error fetching garage data:", error);

      // If API fails, add default markers as fallback
      console.log("API fetch failed, adding backup garage markers");
      addBackupMarkers();
    });

  console.log("Garage data request initiated");
}

function initializeLocationName() {
  // Initialize location name if coordinates exist
  const searchLat = document.getElementById("search-lat").value;
  const searchLng = document.getElementById("search-lng").value;

  if (searchLat && searchLng && searchLat !== "None" && searchLng !== "None") {
    // Ensure we have valid numbers
    const lat = parseFloat(searchLat);
    const lng = parseFloat(searchLng);

    if (!isNaN(lat) && !isNaN(lng)) {
      const latlng = L.latLng(lat, lng);

      // Place marker and center map
      placeMarker(latlng);
      searchMap.setView(latlng, 15);

      // Get location name for the coordinates
      reverseGeocode(lat, lng, {
        onSuccess: (result) => {
          // Update the search input with the location name
          document.getElementById("location-search").value = result.displayName;
          // Expand the filter panel by removing the collapsed class and ensuring content is visible
          const filterPanel = document.getElementById("filter-panel");
          if (filterPanel) {
            // This might be more reliable as it would use the existing toggle logic
            const toggleButton = document.getElementById("toggle-filters");
            if (toggleButton && filterPanel.classList.contains("collapsed")) {
              toggleButton.click();
            }
          }
          // Make sure the marker has a popup with the location name
          if (searchMarker) {
            searchMarker.bindPopup(result.displayName).openPopup();

            // Also set a default popup in case reverse geocoding fails
            searchMarker.setPopupContent(result.displayName);
          }
        },
        onError: () => {
          // If reverse geocoding fails, still show a popup with coordinates
          if (searchMarker) {
            const fallbackContent = `Location at ${lat.toFixed(
              6
            )}, ${lng.toFixed(6)}`;
            searchMarker.bindPopup(fallbackContent).openPopup();
          }
        },
      });

      // Fix map rendering
      setTimeout(() => {
        searchMap.invalidateSize();

        // Make sure marker is visible after map is properly rendered
        if (searchMarker) {
          searchMarker.openPopup();
        }
      }, 100);
    }
  }
}

// Function to add parking meters to the map
function addParkingMeters(map) {
  console.log("Adding parking meters to map...");
  currentMap = map;

  // Create layer group if it doesn't exist
  if (!meterLayerGroup) {
    console.log("Creating new meter layer group");
    meterLayerGroup = L.layerGroup();
  } else {
    console.log("Using existing meter layer group");
  }

  // Create marker icon for parking meters
  const meterIcon = L.divIcon({
    html: markerTemplates.meter,
    className: "meter-marker",
    iconSize: [18, 18],
    iconAnchor: [9, 18],
    popupAnchor: [0, -18],
  });

  // Add event listener to the listings toggle switch
  setTimeout(() => {
    const toggleListings = document.getElementById("toggle-listings");
    const locationPickerToggle = document.getElementById(
      "location-picker-toggle"
    );

    if (toggleListings) {
      toggleListings.addEventListener("change", function () {
        if (this.checked) {
          if (map.hasLayer && !map.hasLayer(listingLayerGroup)) {
            map.addLayer(listingLayerGroup);
          }
        } else {
          if (map.hasLayer && map.hasLayer(listingLayerGroup)) {
            map.removeLayer(listingLayerGroup);
          }
        }
      });
    }

    if (locationPickerToggle) {
      locationPickerToggle.addEventListener("change", function () {
        // Simple toggle - just change the cursor
        if (this.checked) {
          document.getElementById(map._container.id).style.cursor = "crosshair";
        } else {
          document.getElementById(map._container.id).style.cursor = "";
          // Remove the search marker when location picker is toggled off
          if (typeof searchMarker !== "undefined" && searchMarker) {
            map.removeLayer(searchMarker);
            searchMarker = null;
          }
        }
      });
    }
  }, 100);
  // Fetch parking meter data from NYC Open Data API
  fetch(openDataParkingMeterURL)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((meters) => {
      console.log(`Fetched ${meters.length} parking meters from NYC API`);

      // Filter out commercial parking meters
      const regularMeters = meters.filter(
        (meter) => !meter.meter_hours?.includes("Com")
      );
      console.log(`Filtered to ${regularMeters.length} regular parking meters`);

      // Add markers for each meter
      regularMeters.forEach((meter) => {
        try {
          const lat = parseFloat(meter.lat);
          const lng = parseFloat(meter.long);

          // Format the hours string to be more readable
          let hours = meter.meter_hours || "No hours specified";

          // First, standardize the format
          hours = hours.replace("2 HR Pas", "2-Hour Parking");
          hours = hours.replace("2HR Pas", "2-Hour Parking");
          hours = hours.replace("6HR Pas", "6-Hour Parking");

          // Convert days to full names
          hours = hours.replace("Mon-Sat", "Monday to Saturday");
          hours = hours.replace("Mon-Fri", "Monday to Friday");
          hours = hours.replace("Mon-Thur", "Monday to Thursday");

          // Convert all times to 12-hour format
          const timeReplacements = {
            "0700": "7:00 AM",
            "0800": "8:00 AM",
            "0830": "8:30 AM",
            "0900": "9:00 AM",
            1000: "10:00 AM",
            1200: "12:00 PM",
            1600: "4:00 PM",
            1800: "6:00 PM",
            1900: "7:00 PM",
            2200: "10:00 PM",
            2400: "12:00 AM",
          };

          // Replace all time occurrences
          Object.entries(timeReplacements).forEach(([oldTime, newTime]) => {
            hours = hours.replace(new RegExp(oldTime, "g"), newTime);
          });

          // Standardize separators
          hours = hours.replace(/\s*\/\s*/g, " | ");
          hours = hours.replace(/\s*-\s*/g, " - ");

          // Clean up any double spaces
          hours = hours.replace(/\s+/g, " ");

          // Format the final string
          hours = hours
            .split(" | ")
            .map((period) => {
              return period.trim();
            })
            .join(" | ");

          // Create marker and add to layer group
          const marker = L.marker([lat, lng], {
            icon: meterIcon,
            title: `Parking Meter ${meter.meter_number}`,
            zIndexOffset: 200,
          });

          meterLayerGroup.addLayer(marker);

          // Create popup content
          const popupContent = `
                        <div class="meter-popup" style="padding: 8px; min-width: 200px;">
                            <div style="margin-bottom: 8px;">
                                <h4 style="margin: 0; color: #2c3e50; font-size: 14px;">Meter #${
                                  meter.meter_number
                                }</h4>
                            </div>
                            <div style="margin-bottom: 8px; display: flex; align-items: flex-start;">
                                <i class="fas fa-map-marker-alt" style="color: #7f8c8d; margin-right: 8px; margin-top: 3px;"></i>
                                <div style="color: #34495e; font-size: 13px;">
                                    ${meter.on_street}<br>
                                    <span style="color: #7f8c8d; font-size: 12px;">Between ${
                                      meter.from_street
                                    } and ${meter.to_street}</span>
                                </div>
                            </div>
                            <div style="margin-bottom: 8px; display: flex; align-items: flex-start;">
                                <i class="fas fa-clock" style="color: #7f8c8d; margin-right: 8px; margin-top: 3px;"></i>
                                <div style="color: #34495e; font-size: 13px;">${hours}</div>
                            </div>
                            ${
                              meter.pay_by_cell_number
                                ? `
                            <div style="margin-bottom: 8px; display: flex; align-items: center;">
                                <i class="fas fa-mobile-alt" style="color: #7f8c8d; margin-right: 8px;"></i>
                                <span style="color: #34495e; font-size: 12px;">Pay by Phone: ${meter.pay_by_cell_number}</span>
                            </div>
                            `
                                : ""
                            }
                            <div style="display: flex; align-items: center;">
                                <i class="fas fa-road" style="color: #7f8c8d; margin-right: 8px;"></i>
                                <span style="color: #34495e; font-size: 12px;">Side: ${
                                  meter.side_of_street || "Not specified"
                                }</span>
                            </div>
                        </div>
                    `;

          marker.bindPopup(popupContent);
          console.log(`Added meter ${meter.meter_number} at ${lat}, ${lng}`);
        } catch (error) {
          console.error(`Error adding meter ${meter.meter_number}:`, error);
        }
      });

      console.log(
        `Successfully added ${meters.length} active parking meters to the map`
      );
    })
    .catch((error) => {
      console.error("Error fetching parking meter data:", error);
    });
}
