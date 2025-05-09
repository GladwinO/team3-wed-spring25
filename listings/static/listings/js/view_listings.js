console.log("view_listings.js loaded");

// Global variables
let searchMap;
let searchMarker;
let mapInitialized = false;
let listingMarkers = {}; // Keep track of all listing markers
let currentMapView = null;
let listingLayerGroup;
let currentMap;
let garageLayerGroup;
let meterLayerGroup;

// Map-related functions (outside DOMContentLoaded)
function initializeMap() {
  if (!mapInitialized) {
    console.log("Initializing search map...");

    // Ensure map container is visible
    const mapContainer = document.getElementById("map-view");
    if (mapContainer) {
      mapContainer.style.display = "block";
      mapContainer.style.height = "100%";
      mapContainer.style.width = "100%";
    }

    // Use our NYC-bounded map initialization instead of the original code
    searchMap = initializeNYCMap("map-view", {
      center: NYC_CENTER,
      zoom: 12,
      minZoom: 10,
    });

    currentMapView = searchMap; // Store map reference

    // Initialize layer groups
    listingLayerGroup = L.layerGroup().addTo(searchMap);
    garageLayerGroup = L.layerGroup();
    meterLayerGroup = L.layerGroup();

    // Add click event to map
    searchMap.on("click", onMapClick);

    // Add the legend to the search map
    searchMap.addControl(createMapLegend());

    // Add garages and meters to the map
    addGaragesDirectly(searchMap);
    addParkingMeters(searchMap);

    // Force map resize
    setTimeout(() => {
      searchMap.invalidateSize(true);
      console.log("Map size invalidated");
    }, 100);

    mapInitialized = true;
    console.log("Map initialized successfully");
  }
}

function setupLoadMoreButton() {
  const loadMoreBtn = document.getElementById("load-more-btn");
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener("click", loadMoreListings);
  }
}

// Helper function to remove all load more buttons
function removeLoadMoreButtons() {
  // Remove button containers
  document.querySelectorAll(".text-center.my-4").forEach((container) => {
    if (container.querySelector("#load-more-btn")) {
      container.remove();
    }
  });

  // Remove any orphaned buttons
  document.querySelectorAll("#load-more-btn").forEach((button) => {
    const container =
      button.closest(".text-center.my-4") || button.parentElement;
    if (container) container.remove();
    else button.remove();
  });
}

// Simplified loadMoreListings function
function loadMoreListings() {
  const loadMoreBtn = this;
  const nextPage = loadMoreBtn.getAttribute("data-next-page");
  const listingsContainer = document.querySelector(".listings-container");

  // Show loading state
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
      // Parse the HTML response
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");

      // Remove any existing load more buttons
      document
        .querySelectorAll("#load-more-btn, .text-center.my-4")
        .forEach((el) => el.remove());

      // Add new listings to container
      const newListings = doc.querySelectorAll(".card");

      // Track new listings for map update
      const newListingData = [];

      newListings.forEach((listing) => {
        // Add listing to DOM
        const listingClone = listing.cloneNode(true);
        listingsContainer.appendChild(listingClone);

        // Collect data for map markers
        const lat = parseFloat(listing.dataset.lat);
        const lng = parseFloat(listing.dataset.lng);
        if (!isNaN(lat) && !isNaN(lng)) {
          newListingData.push({
            id: listing.dataset.id,
            title: listing.dataset.title,
            lat: lat,
            lng: lng,
            price: listing.dataset.price,
            rating: parseFloat(listing.dataset.rating || 0),
            locationName: listing.dataset.location || "",
          });
        }
      });

      // Update map with new markers if map is initialized
      if (mapInitialized && newListingData.length > 0) {
        // Add new markers to the map
        newListingData.forEach((listing) => {
          addListingMarker(listing);
        });
      }

      // Check if there are more listings
      const newLoadMoreBtn = doc.querySelector("#load-more-btn");

      if (newLoadMoreBtn) {
        // Create a new button container
        const buttonContainer = document.createElement("div");
        buttonContainer.className = "text-center my-4";

        // Clone the button from the response
        const buttonClone = newLoadMoreBtn.cloneNode(true);
        buttonClone.innerHTML = "Load More Listings";
        buttonClone.disabled = false;

        // Add the button to the container and the container to the page
        buttonContainer.appendChild(buttonClone);
        listingsContainer.appendChild(buttonContainer);

        // Add event listener to the new button
        buttonClone.addEventListener("click", loadMoreListings);
      } else {
        // No more listings to load
        const endMessage = document.createElement("div");
        endMessage.className = "text-center my-4";
        endMessage.innerHTML = "<p>No more listings to display</p>";
        listingsContainer.appendChild(endMessage);
      }

      // After adding new listings, update the event listeners
      setTimeout(() => {
        setupListingHighlighting();
      }, 100);
    })
    .catch((error) => {
      console.error("Error loading more listings:", error);

      // Create a retry button
      const retryContainer = document.createElement("div");
      retryContainer.className = "text-center my-4";

      const retryButton = document.createElement("button");
      retryButton.id = "load-more-btn";
      retryButton.className = "btn btn-primary";
      retryButton.setAttribute("data-next-page", nextPage);
      retryButton.textContent = "Try Again";
      retryButton.addEventListener("click", loadMoreListings);

      retryContainer.appendChild(retryButton);
      listingsContainer.appendChild(retryContainer);
    });
}

// Helper function to add a listing marker to the map
function addListingMarker(listing) {
  if (!mapInitialized) return;

  try {
    // Create the marker but add it to the layer group instead of the map
    const marker = L.marker([listing.lat, listing.lng], {
      zIndexOffset: 1000, // Higher z-index to appear above garage markers
    });

    listingLayerGroup.addLayer(marker);
    listingMarkers[listing.id] = marker;

    // Generate popup content using a dedicated function
    const popupContent = generateListingPopupContent(listing);
    marker.bindPopup(popupContent);
  } catch (error) {
    console.error("Error adding listing marker:", error);
  }
}

function onMapClick(e) {
  // Only update if the location picker is enabled
  const locationPickerToggle = document.getElementById(
    "location-picker-toggle"
  );
  if (!locationPickerToggle || !locationPickerToggle.checked) {
    return; // Exit if toggle doesn't exist or isn't checked
  }

  placeMarker(e.latlng);
  updateCoordinates(e.latlng.lat, e.latlng.lng);

  // Reverse geocode to get location name
  reverseGeocode(e.latlng.lat, e.latlng.lng, {
    onSuccess: (result) => {
      document.getElementById("location-search").value = result.displayName;
      clearFilterLocationError();
    },
    onError: () => {
      showFilterLocationError(
        "Could not retrieve address. Try searching by name instead."
      );
    },
  });
}

function placeMarker(latlng) {
  if (searchMarker) {
    searchMap.removeLayer(searchMarker);
  }

  // Create a special search marker that stands out from listing markers
  searchMarker = L.marker(latlng, {
    draggable: true,
    icon: L.divIcon({
      className: "search-marker-icon",
      html: createMarkerIconHtml(),
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    }),
  }).addTo(searchMap);

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

    // Draw search radius if enabled
    drawSearchRadius(position);
  });

  // Draw search radius if enabled
  drawSearchRadius(latlng);
}

// Add search radius visualization
let radiusCircle = null;

function drawSearchRadius(center) {
  // Remove existing radius circle if it exists
  if (radiusCircle) {
    searchMap.removeLayer(radiusCircle);
    radiusCircle = null;
  }

  // Check if radius filtering is enabled
  const enableRadiusCheckbox = document.getElementById("enable-radius");
  const radiusInput = document.getElementById("radius-input");

  if (
    enableRadiusCheckbox &&
    enableRadiusCheckbox.checked &&
    radiusInput &&
    radiusInput.value
  ) {
    const radiusKm = parseFloat(radiusInput.value);
    if (!isNaN(radiusKm) && radiusKm > 0) {
      // Convert km to meters for the circle radius
      const radiusMeters = radiusKm * 1000;

      // Create a circle with styling
      radiusCircle = L.circle(center, {
        radius: radiusMeters,
        color: "#007bff",
        fillColor: "#007bff",
        fillOpacity: 0.1,
        weight: 2,
        dashArray: "5, 5",
      }).addTo(searchMap);

      // Fit map to show the entire circle
      searchMap.fitBounds(radiusCircle.getBounds());
    }
  }
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

document.addEventListener("DOMContentLoaded", function () {
  // Initialize both views to be active simultaneously
  const listView = document.getElementById("list-view");
  const mapView = document.getElementById("map-view");

  if (listView) listView.classList.add("active-view");
  if (mapView) mapView.classList.add("active-view");

  if (listView) listView.classList.add("active-view");
  if (mapView) {
    mapView.classList.add("active-view");
    // Ensure map container is visible and properly sized
    mapView.style.display = "block";
    mapView.style.height = "100%";
    mapView.style.width = "100%";
    mapView.style.position = "absolute";
    mapView.style.top = "0";
    mapView.style.left = "0";
    mapView.style.right = "0";
    mapView.style.bottom = "0";
  }

  const filterHeader = document.querySelector(".filter-header");
  const toggleFiltersBtn = document.getElementById("toggle-filters");

  // Add click event to both header and toggle button
  if (filterHeader) {
    filterHeader.addEventListener("click", function (e) {
      // Prevent click if they clicked the toggle button directly
      if (
        e.target !== toggleFiltersBtn &&
        !toggleFiltersBtn.contains(e.target)
      ) {
        toggleFilterPanel();
      }
    });
  }

  if (toggleFiltersBtn) {
    toggleFiltersBtn.addEventListener("click", function (e) {
      e.stopPropagation(); // Prevent double toggle from header click
      toggleFilterPanel();
    });
  }

  setupAdvancedFilters();
  setupRadiusToggle();
  initializeDateRangeToggle();
  initializeEvChargerToggle();
  initializeRecurringPatternToggle();
  initializeMultipleDaysToggle();

  // Initialize map first
  initializeMap();

  // Then add listings to map
  setTimeout(() => {
    fetchAllListingMarkers();
  }, 200);

  setMinDates();
  initializeLocationName();
  setupSearch();
  setupLoadMoreButton();
  initializePopover();

  // Force map resize immediately AND after a short delay
  setTimeout(() => {
    if (searchMap) {
      searchMap.invalidateSize(true);
    }

    // Fix any initial spacing issues with the layout
    const mainContent = document.getElementById("main-content");
    if (mainContent) {
      mainContent.style.position = "absolute";
      mainContent.style.top = "56px"; // Match navbar height
      mainContent.style.left = "0";
      mainContent.style.right = "0";
      mainContent.style.bottom = "0";
    }
  }, 100);

  // Add window resize handler to ensure map fills space correctly
  window.addEventListener("resize", function () {
    if (searchMap) {
      searchMap.invalidateSize(true);
    }
  });

  // Handle advanced filters modal
  const applyAdvancedFiltersBtn = document.getElementById(
    "apply-advanced-filters"
  );
  if (applyAdvancedFiltersBtn) {
    applyAdvancedFiltersBtn.addEventListener("click", applyAdvancedFilters);
  }

  // After other initialization, call setupListingHighlighting
  setTimeout(() => {
    setupListingHighlighting();
  }, 1000); // Give time for map and listings to initialize
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
  const mapContainer = document.getElementById("map-view");
  const query = searchInput.value;

  if (!query) return;

  // Clear any existing error messages before search
  clearFilterLocationError();

  // Show loading indicator on search button
  const searchButton = document.getElementById("search-location");
  if (searchButton) {
    searchButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    searchButton.disabled = true;
  }

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

      // Update the location search input value
      searchInput.value = result.displayName;

      // Fix map rendering
      setTimeout(() => {
        searchMap.invalidateSize();
      }, 100);

      // Reset search button
      if (searchButton) {
        searchButton.innerHTML = '<i class="fas fa-map-pin"></i>';
        searchButton.disabled = false;
      }
    },
    onOutOfBounds: () => {
      showFilterLocationError(
        "Location is outside of New York City. Please search for a location within NYC."
      );

      // Reset search button
      if (searchButton) {
        searchButton.innerHTML = '<i class="fas fa-map-pin"></i>';
        searchButton.disabled = false;
      }
    },
    onNotFound: () => {
      showFilterLocationError(
        "Location not found. Please try a different search term."
      );

      // Reset search button
      if (searchButton) {
        searchButton.innerHTML = '<i class="fas fa-map-pin"></i>';
        searchButton.disabled = false;
      }
    },
    onError: (error) => {
      showFilterLocationError(
        "Error searching for location. Please try again."
      );
      console.error("Search error:", error);

      // Reset search button
      if (searchButton) {
        searchButton.innerHTML = '<i class="fas fa-map-pin"></i>';
        searchButton.disabled = false;
      }
    },
  });
}

function fetchAllListingMarkers() {
  if (!mapInitialized) return;

  // Clear existing markers
  listingLayerGroup.clearLayers();

  // Get current URL parameters for filtering
  const currentUrl = new URL(window.location.href);
  const filterParams = currentUrl.searchParams;
  console.log("filterParams", filterParams, "lol");

  // Convert URLSearchParams to a proper query string
  const queryString = filterParams.toString()
    ? `?${filterParams.toString()}`
    : "";
  console.log("queryString", queryString, "lol");

  fetch(`/listings/map-view-listings/${queryString}`, {
    method: "GET", // or your actual method, e.g., POST
    mode: "cors", // explicitly allow CORS
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "User-Agent": "ParkEasy NYC Application (https://parkeasy.example.com)",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      console.log(`Loaded ${data.markers.length} markers for map`);

      // Add each marker to the map
      data.markers.forEach((listing) => {
        addListingMarker(listing);
      });

      // Fit map to show all markers if there are any
      if (Object.keys(listingMarkers).length > 0) {
        const markerGroup = L.featureGroup(Object.values(listingMarkers));
        searchMap.fitBounds(markerGroup.getBounds());
      }

      // Call setupListingHighlighting after all markers are loaded
      setTimeout(() => {
        setupListingHighlighting();
        console.log("Highlighting setup completed after markers loaded");
      }, 100);
    })
    .catch((error) => {
      console.error("Error loading listing markers:", error);
    });
}

// Functions to handle highlighting
function highlightMarkerFromListing(listingId) {
  console.log("Highlighting marker for listing:", listingId);
  const marker = listingMarkers[listingId];
  if (marker) {
    marker.setZIndexOffset(2000); // Bring to front
    marker.openPopup();
    console.log("Marker highlighted successfully");
  } else {
    console.warn("Marker not found for listing:", listingId);
    console.log("Available marker IDs:", Object.keys(listingMarkers));
  }
}

function unhighlightMarkerFromListing(listingId) {
  console.log("Unhighlighting marker for listing:", listingId);
  const marker = listingMarkers[listingId];
  if (marker) {
    marker.setZIndexOffset(1000);
    marker.closePopup();
    console.log("Marker unhighlighted successfully");
  } else {
    console.warn("Marker not found for listing:", listingId);
  }
}

function setupListingHighlighting() {
  console.log("Setting up listing highlighting");
  const cards = document.querySelectorAll(".card");
  console.log(`Found ${cards.length} listing cards`);

  cards.forEach((card) => {
    const listingId = card.dataset.id;
    console.log(`Setting up highlighting for card ID: ${listingId}`);

    // Remove any existing event listeners
    if (card._mouseenterHandler) {
      card.removeEventListener("mouseenter", card._mouseenterHandler);
    }
    if (card._mouseleaveHandler) {
      card.removeEventListener("mouseleave", card._mouseleaveHandler);
    }

    // Create new event handlers
    card._mouseenterHandler = function () {
      console.log("Card mouseenter for listing:", listingId);
      highlightMarkerFromListing(listingId);
    };

    card._mouseleaveHandler = function () {
      console.log("Card mouseleave for listing:", listingId);
      // To Do: Migh add later
      // unhighlightMarkerFromListing(listingId);
    };

    // Add the event listeners
    card.addEventListener("mouseenter", card._mouseenterHandler);
    card.addEventListener("mouseleave", card._mouseleaveHandler);
  });
}

// Helper function to show location error in the filter form
function showFilterLocationError(message) {
  const locationField = document.getElementById("location-search");
  if (!locationField) return;

  // Find or create error element
  let errorElement = document.getElementById("filter-location-error");
  if (!errorElement) {
    errorElement = document.createElement("div");
    errorElement.id = "filter-location-error";
    errorElement.className = "invalid-feedback d-block";
    errorElement.innerHTML = `<i class="fas fa-exclamation-circle me-1"></i> ${message}`;

    // Insert after the input group
    const inputGroup = locationField.closest(".input-group");
    if (inputGroup && inputGroup.parentNode) {
      inputGroup.parentNode.insertBefore(errorElement, inputGroup.nextSibling);
    }
  } else {
    errorElement.innerHTML = `<i class="fas fa-exclamation-circle me-1"></i> ${message}`;
    errorElement.style.display = "block";
  }

  // Add error styling to input
  locationField.classList.add("is-invalid");
}

// Helper function to clear location error
function clearFilterLocationError() {
  const errorElement = document.getElementById("filter-location-error");
  if (errorElement) {
    errorElement.style.display = "none";
  }

  const locationField = document.getElementById("location-search");
  if (locationField) {
    locationField.classList.remove("is-invalid");
  }
}
