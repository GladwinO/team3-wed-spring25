console.log("view_listings.js loaded");

// Helper function to generate star HTML - extract it so it can be used anywhere
function generateStarRating(rating) {
  let starsHtml = "";

  if (!rating) {
    // Show 5 empty stars if no rating
    for (let i = 0; i < 5; i++) {
      starsHtml += '<i class="far fa-star text-warning"></i>';
    }
  } else {
    // Full stars
    for (let i = 0; i < Math.floor(rating); i++) {
      starsHtml += '<i class="fas fa-star text-warning"></i>';
    }
    // Half star
    if (rating % 1 >= 0.5) {
      starsHtml += '<i class="fas fa-star-half-alt text-warning"></i>';
    }
    // Empty stars
    for (let i = Math.ceil(rating); i < 5; i++) {
      starsHtml += '<i class="far fa-star text-warning"></i>';
    }
  }

  return starsHtml;
}

// Global variables
let searchMap;
let searchMarker;
let mapInitialized = false;

// Map-related functions (outside DOMContentLoaded)
function initializeMap() {
  if (!mapInitialized) {
    // Use our NYC-bounded map initialization instead of the original code
    searchMap = initializeNYCMap("search-map");

    // Add click event to map
    searchMap.on("click", onMapClick);
    mapInitialized = true;
  }
}

function onMapClick(e) {
  placeMarker(e.latlng);
  updateCoordinates(e.latlng.lat, e.latlng.lng);

  // Reverse geocode to get location name
  reverseGeocode(e.latlng.lat, e.latlng.lng, {
    onSuccess: (result) => {
      document.getElementById("location-search").value = result.displayName;
    },
  });
}

function placeMarker(latlng) {
  if (searchMarker) {
    searchMap.removeLayer(searchMarker);
  }
  searchMarker = L.marker(latlng, { draggable: true }).addTo(searchMap);

  // Update coordinates when marker is dragged
  searchMarker.on("dragend", function (event) {
    const marker = event.target;
    const position = marker.getLatLng();
    updateCoordinates(position.lat, position.lng);

    // Reverse geocode to get location name
    reverseGeocode(position.lat, position.lng, {
      onSuccess: (result) => {
        document.getElementById("location-search").value = result.displayName;
        marker.bindPopup(result.displayName);
      },
    });

    // Optional: Update map view to center on new position
    searchMap.setView(position, searchMap.getZoom());
  });
}

function updateCoordinates(lat, lng) {
  document.getElementById("search-lat").value = lat;
  document.getElementById("search-lng").value = lng;

  // Update coordinate display
  const coordDisplay = document.getElementById("coordinates-display");
  if (coordDisplay) {
    coordDisplay.style.display = "block";
    document.getElementById("lat-display").textContent = lat.toFixed(6);
    document.getElementById("lng-display").textContent = lng.toFixed(6);
  }
}

function setupLocationMap() {
  const toggleMapBtn = document.getElementById("toggle-map");
  const mapContainer = document.getElementById("search-map-container");

  if (!toggleMapBtn || !mapContainer) return;

  toggleMapBtn.addEventListener("click", function () {
    const isMapHidden = mapContainer.style.display === "none";

    if (isMapHidden) {
      mapContainer.style.display = "block";
      toggleMapBtn.classList.remove("btn-outline-secondary");
      toggleMapBtn.classList.add("btn-secondary");

      if (!mapInitialized) {
        initializeMap();
      }
      setTimeout(() => {
        if (searchMap) {
          searchMap.invalidateSize();
        }
      }, 100);
    } else {
      mapContainer.style.display = "none";
      toggleMapBtn.classList.remove("btn-secondary");
      toggleMapBtn.classList.add("btn-outline-secondary");
    }
  });
}

// Single DOMContentLoaded event listener for all functionality
document.addEventListener("DOMContentLoaded", function () {
  // ---- FILTER SECTION ----
  // Filter type toggle handlers (single/recurring)
  const filterSingle = document.getElementById("filter_single");
  const filterRecurring = document.getElementById("filter_recurring");
  const singleFilter = document.getElementById("single-filter");
  const recurringFilter = document.getElementById("recurring-filter");

  // Initialize filter visibility based on selected option
  function initializeFilters() {
    if (filterSingle && filterRecurring) {
      if (filterSingle.checked) {
        singleFilter.style.display = "block";
        recurringFilter.style.display = "none";
      } else if (filterRecurring.checked) {
        singleFilter.style.display = "none";
        recurringFilter.style.display = "block";
      }

      // Add event listeners for filter type changes
      filterSingle.addEventListener("change", function () {
        if (this.checked) {
          singleFilter.style.display = "block";
          recurringFilter.style.display = "none";
        }
      });

      filterRecurring.addEventListener("change", function () {
        if (this.checked) {
          singleFilter.style.display = "none";
          recurringFilter.style.display = "block";
        }
      });
    }
  }

  function initializeFilterTypeDropdown() {
    const filterTypeSelect = document.getElementById('filter-type-select');
    const singleFilter = document.getElementById('single-filter');
    const recurringFilter = document.getElementById('recurring-filter');
  
    if (filterTypeSelect) {
      // Set initial state
      if (filterTypeSelect.value === 'single') {
        singleFilter.style.display = "block";
        recurringFilter.style.display = "none";
      } else if (filterTypeSelect.value === 'recurring') {
        singleFilter.style.display = "none";
        recurringFilter.style.display = "block";
      }
  
      // Add change event listener
      filterTypeSelect.addEventListener('change', function() {
        if (this.value === 'single') {
          singleFilter.style.display = "block";
          recurringFilter.style.display = "none";
        } else if (this.value === 'recurring') {
          singleFilter.style.display = "none";
          recurringFilter.style.display = "block";
        }
      });
    }
  }

  // Recurring pattern toggle (daily/weekly)
  function initializeRecurringPatterns() {
    const patternDaily = document.getElementById("pattern_daily");
    const patternWeekly = document.getElementById("pattern_weekly");
    const dailyFields = document.getElementById("daily-pattern-fields");
    const weeklyFields = document.getElementById("weekly-pattern-fields");

    if (patternDaily && patternWeekly && dailyFields && weeklyFields) {
      // Initialize visibility
      if (patternDaily.checked) {
        dailyFields.style.display = "block";
        weeklyFields.style.display = "none";
      } else if (patternWeekly.checked) {
        dailyFields.style.display = "none";
        weeklyFields.style.display = "block";
      }

      // Add event listeners
      patternDaily.addEventListener("change", function () {
        if (this.checked) {
          dailyFields.style.display = "block";
          weeklyFields.style.display = "none";
        }
      });

      patternWeekly.addEventListener("change", function () {
        if (this.checked) {
          dailyFields.style.display = "none";
          weeklyFields.style.display = "block";
        }
      });
    }
  }

  // Set minimum date to today for all date inputs
  function setMinDates() {
    const today = new Date().toISOString().split("T")[0];
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach((input) => {
      input.min = today;
    });
  }

  // ---- STAR RATING FUNCTIONALITY ----
  const ratingElements = document.querySelectorAll(".rating-stars");
  ratingElements.forEach(function (ratingElement) {
    const rating = parseFloat(ratingElement.getAttribute("data-rating"));
    ratingElement.innerHTML = generateStarRating(rating);
  });

  // ---- LOAD MORE FUNCTIONALITY ----
  function setupLoadMoreButton() {
    const loadMoreBtn = document.getElementById("load-more-btn");
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener("click", function () {
        const nextPage = this.getAttribute("data-next-page");
        const listingsContainer = document.querySelector(".listings-container");

        loadMoreBtn.innerHTML =
          '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
        loadMoreBtn.disabled = true;

        // Build URL with existing filters
        let url = new URL(window.location.href);
        url.searchParams.set("page", nextPage);
        url.searchParams.set("ajax", "1");

        fetch(url)
          .then((response) => response.text())
          .then((html) => {
            // Find and remove the existing load more button container
            const existingButtonContainer =
              document.querySelector(".text-center.my-4");
            if (existingButtonContainer) {
              existingButtonContainer.remove();
            }

            // Parse the HTML response
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, "text/html");

            // Add new listings to container
            const newListings = doc.querySelectorAll(".card");
            newListings.forEach((listing) => {
              const listingClone = listing.cloneNode(true);
              listingsContainer.appendChild(listingClone);

              // Find and update the star ratings in the newly added listing
              const ratingStars = listingClone.querySelector(".rating-stars");
              if (ratingStars) {
                const rating = parseFloat(listingClone.dataset.rating || 0);
                ratingStars.innerHTML = generateStarRating(rating);
              }
            });

            // Add new load more button if available
            const loadMoreContainer = doc.querySelector(".text-center.my-4");
            if (loadMoreContainer) {
              listingsContainer.appendChild(loadMoreContainer.cloneNode(true));

              // Re-attach event listener
              const newLoadMoreBtn = document.getElementById("load-more-btn");
              if (newLoadMoreBtn) {
                newLoadMoreBtn.innerHTML = "Load More Listings"; // Consistent - no icon
                newLoadMoreBtn.addEventListener("click", arguments.callee);
              }
            }
          })
          .catch((error) => {
            console.error("Error loading more listings:", error);
            loadMoreBtn.innerHTML = "Error Loading"; // Consistent - no icon
            loadMoreBtn.disabled = false;
          });
      });
    }
  }

  function setupFilterButton() {
    const filterButton = document.querySelector(
      'form.filter-box button[type="submit"]'
    );

    if (filterButton) {
      filterButton.addEventListener("click", function (event) {
        event.preventDefault();
        const form = this.closest("form");
        if (form) {
          form.submit();
        }
      });
    }
  }

  // ---- MAP VIEW FUNCTIONALITY ----
  function setupMapView() {
    const listViewBtn = document.getElementById("list-view-btn");
    const mapViewBtn = document.getElementById("map-view-btn");
    const listView = document.getElementById("list-view");
    const mapView = document.getElementById("map-view");
    let map;

    if (!listViewBtn || !mapViewBtn || !listView || !mapView) return;

    function parseLocation(locationString) {
      try {
        const match = locationString.match(/\[([-\d.]+),\s*([-\d.]+)\]/);
        if (match) {
          return {
            lat: parseFloat(match[1]),
            lng: parseFloat(match[2]),
            address: locationString.split("[")[0].trim(),
            location_name: locationString.split("[")[0].trim(),
          };
        }
      } catch (error) {
        console.log("Error parsing location:", error);
      }
      return {
        lat: NYC_CENTER[0], // Use NYC_CENTER from nyc-map-bounds.js
        lng: NYC_CENTER[1],
        address: locationString || "Location not specified",
      };
    }

    function initMap() {
      if (!map) {
        // Use our NYC-bounded map initialization
        map = initializeNYCMap("map-view");

        // Add markers for all listings
        const listings = document.querySelectorAll(".card");
        const bounds = [];

        listings.forEach((listing) => {
          const location = parseLocation(listing.dataset.location);
          const locationName = listing.dataset.locationName;
          const title = listing.dataset.title;
          const price = listing.dataset.price;
          const rating = parseFloat(listing.dataset.rating) || 0;

          // Only add markers within NYC bounds
          if (
            location.lat >= NYC_BOUNDS.min_lat &&
            location.lat <= NYC_BOUNDS.max_lat &&
            location.lng >= NYC_BOUNDS.min_lng &&
            location.lng <= NYC_BOUNDS.max_lng
          ) {
            const marker = L.marker([location.lat, location.lng]).addTo(map);
            bounds.push([location.lat, location.lng]);

            // Create popup content
            const ratingHtml = rating
              ? `<br><strong>Rating:</strong> ${generateStarRating(
                  rating
                )} (${rating.toFixed(1)})`
              : `<br><span class="text-muted">No reviews yet ${generateStarRating(
                  0
                )}</span>`;

            const popupContent = `
              <strong>${title}</strong><br>
              ${locationName}<br>
              $${price}/hour
              ${ratingHtml}
            `;

            marker.bindPopup(popupContent);
          }
        });

        // Fit map to show all markers, or use NYC center if no markers
        if (bounds.length > 0) {
          map.fitBounds(bounds);
        }
      }
    }

    function showListView() {
      mapView.classList.remove("active-view");
      listView.classList.add("active-view");
      listViewBtn.classList.add("btn-primary");
      listViewBtn.classList.remove("btn-outline-primary");
      mapViewBtn.classList.add("btn-outline-primary");
      mapViewBtn.classList.remove("btn-primary");
    }

    function showMapView() {
      listView.classList.remove("active-view");
      mapView.classList.add("active-view");
      mapViewBtn.classList.add("btn-primary");
      mapViewBtn.classList.remove("btn-outline-primary");
      listViewBtn.classList.remove("btn-primary");
      listViewBtn.classList.add("btn-outline-primary");
      listViewBtn.classList.remove("active");

      initMap();
      if (map) {
        map.invalidateSize();
      }
    }

    // Add event listeners
    listViewBtn.addEventListener("click", showListView);
    mapViewBtn.addEventListener("click", showMapView);

    // Initialize with list view
    showListView();
  }

  // Radius toggle functionality
  function setupRadiusToggle() {
    const enableRadiusCheckbox = document.getElementById("enable-radius");
    const radiusInputGroup = document.getElementById("radius-input-group");
    const radiusInput = document.getElementById("radius-input");
    const radiusHint = document.getElementById("radius-hint");

    if (enableRadiusCheckbox && radiusInputGroup && radiusInput && radiusHint) {
      // Initialize state based on checkbox
      if (enableRadiusCheckbox.checked) {
        radiusInputGroup.style.display = "flex";
        radiusHint.style.display = "none";
      } else {
        radiusInputGroup.style.display = "none";
        radiusHint.style.display = "block";
      }

      // Toggle radius input visibility
      enableRadiusCheckbox.addEventListener("change", function () {
        if (this.checked) {
          radiusInputGroup.style.display = "flex";
          radiusHint.style.display = "none";
          radiusInput.focus();
        } else {
          radiusInputGroup.style.display = "none";
          radiusHint.style.display = "block";
          radiusInput.value = ""; // Clear the radius value when disabled
        }
      });
    }
  }

  function initializeEvFilters() {
    // Try multiple selectors to find the checkbox
    const evChargerCheckbox =
      document.querySelector('input[name="has_ev_charger"]') ||
      document.querySelector('input[name="ev_charger"]') ||
      document.querySelector("#ev_charger");

    // Log what we found to help debug
    if (evChargerCheckbox) {
      console.log(
        "Found EV checkbox with name:",
        evChargerCheckbox.name,
        "and id:",
        evChargerCheckbox.id
      );
    } else {
      console.error("EV charger checkbox not found with any known selector");
      // List all checkboxes to help debug
      console.log(
        "All checkboxes:",
        document.querySelectorAll('input[type="checkbox"]')
      );
      return;
    }

    // Similarly, be robust with container selection
    const evContainers = document.querySelectorAll(".ev-charger-container");
    console.log("Found", evContainers.length, "EV container elements");

    if (evContainers.length === 0) {
      console.error("No EV container elements found");
      return;
    }

    function toggleEvFields() {
      const isChecked = evChargerCheckbox.checked;
      console.log("EV checkbox state:", isChecked);

      // Toggle visibility
      evContainers.forEach((container) => {
        container.style.display = isChecked ? "block" : "none";
      });

      // Handle field values and disabled state
      const chargerLevelField = document.querySelector(
        '[name="charger_level"]'
      );
      const connectorTypeField = document.querySelector(
        '[name="connector_type"]'
      );

      if (chargerLevelField) {
        chargerLevelField.disabled = !isChecked;
        if (!isChecked) chargerLevelField.value = "";
      }

      if (connectorTypeField) {
        connectorTypeField.disabled = !isChecked;
        if (!isChecked) connectorTypeField.value = "";
      }
    }

    // Run the function initially
    toggleEvFields();

    // Add event listener for changes
    evChargerCheckbox.addEventListener("change", toggleEvFields);
  }

  // Initialize all components
  initializeFilters();
  initializeFilterTypeDropdown();
  initializeRecurringPatterns();
  initializeDateRangeToggle();
  setMinDates();
  setupLoadMoreButton();
  setupMapView();
  setupFilterButton();
  setupRadiusToggle();
  setupLocationMap();
  setupSearch();

  // Initialize location name if coordinates exist
  const searchLat = document.getElementById("search-lat").value;
  const searchLng = document.getElementById("search-lng").value;

  if (searchLat && searchLng && searchLat !== "None" && searchLng !== "None") {
    // Show map container and update toggle button state
    const mapContainer = document.getElementById("search-map-container");
    const toggleMapBtn = document.getElementById("toggle-map");
    mapContainer.style.display = "block";
    toggleMapBtn.classList.remove("btn-outline-secondary");
    toggleMapBtn.classList.add("btn-secondary");

    // Initialize map and place marker
    initializeMap();

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
          document.getElementById("location-search").value = result.displayName;

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
  initializeEvFilters(); // Use this instead of the shared utility

  // Initialize all popovers
  var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
  var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl)
  });
});

function setupSearch() {
  const searchInput = document.getElementById("location-search");
  const searchButton = document.getElementById("search-location");

  if (!searchButton || !searchInput) return;

  searchButton.addEventListener("click", performSearch);
  searchInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      performSearch();
    }
  });
}

function performSearch() {
  const searchInput = document.getElementById("location-search");
  const mapContainer = document.getElementById("search-map-container");
  const query = searchInput.value;

  if (!query) return;

  // Use the utility function
  searchLocation(query, {
    restrictToNYC: true,
    onSuccess: (result) => {
      const latlng = L.latLng(result.lat, result.lng);

      // Show map when location is found
      mapContainer.style.display = "block";
      if (!mapInitialized) {
        initializeMap();
      }

      searchMap.setView(latlng, 15);
      placeMarker(latlng);

      // Add the location name to the marker popup
      if (searchMarker) {
        searchMarker.bindPopup(result.displayName).openPopup();
      }

      // Update the coordinate spans
      document.getElementById("coordinates-display").style.display = "block";
      document.getElementById("lat-display").textContent =
        result.lat.toFixed(6);
      document.getElementById("lng-display").textContent =
        result.lng.toFixed(6);

      // Update hidden inputs
      document.getElementById("search-lat").value = result.lat;
      document.getElementById("search-lng").value = result.lng;

      // Fix map rendering
      setTimeout(() => {
        searchMap.invalidateSize();
      }, 100);

      // Update toggle button state
      const toggleMapBtn = document.getElementById("toggle-map");
      toggleMapBtn.classList.remove("btn-outline-secondary");
      toggleMapBtn.classList.add("btn-secondary");
    },
  });
}

function initializeDateRangeToggle() {
  const enableDateRange = document.getElementById('enable_date_range');
  const endDateContainer = document.getElementById('end-date-container');
  const startDateInput = document.getElementById('single_start_date');
  const endDateInput = document.getElementById('single_end_date');
  
  if (enableDateRange && endDateContainer && startDateInput && endDateInput) {
    // Set initial state
    if (enableDateRange.checked) {
      endDateContainer.style.display = 'block';
    } else {
      endDateContainer.style.display = 'none';
      endDateInput.value = startDateInput.value; // Default end date to start date
    }
    
    // Add change event listeners
    enableDateRange.addEventListener('change', function() {
      if (this.checked) {
        endDateContainer.style.display = 'block';
        if (!endDateInput.value) {
          endDateInput.value = startDateInput.value;
        }
      } else {
        endDateContainer.style.display = 'none';
        endDateInput.value = startDateInput.value; // Set end date equal to start date
      }
    });
    
    // Keep end date in sync with start date when range is disabled
    startDateInput.addEventListener('change', function() {
      if (!enableDateRange.checked) {
        endDateInput.value = this.value;
      } else if (endDateInput.value && new Date(endDateInput.value) < new Date(this.value)) {
        // If end date is now before start date, update it
        endDateInput.value = this.value;
      }
    });
  }
}
