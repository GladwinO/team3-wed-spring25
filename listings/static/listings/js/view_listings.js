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
let garageMarkers = [];
let listingMarkers = [];
let currentMapView = null;
let garageLayerGroup;
let listingLayerGroup;
let currentMap;

// Map-related functions (outside DOMContentLoaded)
function initializeMap() {
    if (!mapInitialized) {
        console.log("Initializing search map...");
        // Use our NYC-bounded map initialization instead of the original code
        searchMap = initializeNYCMap("search-map");
        currentMapView = searchMap; // Store map reference

        // Add click event to map
        searchMap.on("click", onMapClick);

        // Add the legend to the search map
        searchMap.addControl(createMapLegend());

        // Add garage markers to the search map
        addGaragesDirectly(searchMap);

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
    searchMarker.on("dragend", function(event) {
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

    toggleMapBtn.addEventListener("click", function() {
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
document.addEventListener("DOMContentLoaded", function() {
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
                    filterSingle.addEventListener("change", function() {
                        if (this.checked) {
                            singleFilter.style.display = "block";
                            recurringFilter.style.display = "none";
                        }
                    });

                    filterRecurring.addEventListener("change", function() {
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
                    patternDaily.addEventListener("change", function() {
                        if (this.checked) {
                            dailyFields.style.display = "block";
                            weeklyFields.style.display = "none";
                        }
                    });

                    patternWeekly.addEventListener("change", function() {
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
            ratingElements.forEach(function(ratingElement) {
                const rating = parseFloat(ratingElement.getAttribute("data-rating"));
                ratingElement.innerHTML = generateStarRating(rating);
            });

            // ---- LOAD MORE FUNCTIONALITY ----
            function setupLoadMoreButton() {
                const loadMoreBtn = document.getElementById("load-more-btn");
                if (loadMoreBtn) {
                    loadMoreBtn.addEventListener("click", function() {
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
                    filterButton.addEventListener("click", function(event) {
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
                        console.log("Initializing map view...");

                        // Create map centered on NYC
                        map = L.map("map-view").setView([40.7128, -74.0060], 18);
                        currentMap = map;

                        // Create layer groups
                        garageLayerGroup = L.layerGroup().addTo(map);
                        listingLayerGroup = L.layerGroup().addTo(map);

                        // Add the tile layer
                        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                        }).addTo(map);

                        console.log("Map created - now fetching NYC garages from API");

                        // Create a red marker icon for garages
                        const garageIcon = L.divIcon({
                            html: `<div style="
                                background-color: #2c3e50; 
                                width: 22px;   /* Reduced from 28px */
                                height: 22px;  /* Reduced from 28px */
                                border-radius: 5px;
                                display: flex; 
                                justify-content: center; 
                                align-items: center; 
                                border: 1px solid white; /* Thinner border */
                                box-shadow: 0 1px 3px rgba(0,0,0,0.4);
                            ">
                                <i class="fas fa-car" style="
                                    color: white; 
                                    font-size: 11px;  /* Reduced from 14px */
                                    transform: rotate(-45deg);
                                "></i>
                            </div>`,
                            className: 'garage-marker',
                            iconSize: [22, 22],
                            /* Reduced from [28, 28] */
                            iconAnchor: [11, 22],
                            /* Adjusted for new size */
                            popupAnchor: [0, -22] /* Adjusted for new size */
                        });

                        // Fetch garages from NYC Open Data API
                        fetch('https://data.cityofnewyork.us/resource/5bhr-pjxt.json?$limit=50')
                            .then(response => {
                                if (!response.ok) {
                                    throw new Error('Network response was not ok');
                                }
                                return response.json();
                            })
                            .then(garages => {
                                    console.log(`Fetched ${garages.length} garages from NYC API`);

                                    // Add markers for each garage
                                    garages.forEach(garage => {
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
                                                            garage.address_zip
                                                        ].filter(Boolean).join(' ');

                                                        // Get capacity info
                                                        let capacity = "";
                                                        if (garage.detail) {
                                                            capacity = garage.detail;
                                                        }

                                                        // Create marker and add to LAYER GROUP instead of map
                                                        const marker = L.marker([lat, lng], {
                                                            icon: garageIcon,
                                                            title: garage.business_name,
                                                            zIndexOffset: 100 // Lower z-index to ensure garages stay behind listings
                                                        });

                                                        garageLayerGroup.addLayer(marker);

                                                        // Add a brief animation effect (simulate bounce)
                                                        const markerElement = marker.getElement();
                                                        if (markerElement) {
                                                            markerElement.style.transition = 'transform 0.3s ease-in-out';
                                                            setTimeout(() => {
                                                                markerElement.style.transform = 'translateY(-10px)';
                                                                setTimeout(() => {
                                                                    markerElement.style.transform = 'translateY(0)';
                                                                }, 300);
                                                            }, 100 * Math.random() * 10); // Stagger the animations
                                                        }

                                                        // Create popup content
                                                        const popupContent = `
                                        <div class="garage-popup">
                                            <h4 class="garage-name">${garage.business_name}</h4>
                                            <div class="garage-address">
                                                <i class="fas fa-map-marker-alt"></i>
                                                <div>${address}</div>
                                            </div>
                                            ${garage.contact_phone ? `
                                            <div class="garage-phone">
                                                <i class="fas fa-phone"></i>
                                                <a href="tel:${garage.contact_phone}">${garage.contact_phone}</a>
                                            </div>` : ''}
                                            ${capacity ? `
                                            <div class="garage-details">
                                                <i class="fas fa-info-circle"></i>
                                                <div>${capacity}</div>
                                            </div>` : ''}
                                        </div>
                                    `;
                                    
                                    // Bind popup to marker
                                    marker.bindPopup(popupContent);
                                    
                                } catch (error) {
                                    console.error(`Error adding garage ${garage.business_name}:`, error);
                                }
                            }
                        });
                        
                        // Center map on NYC after adding garages
                        map.setView([40.7128, -74.0060], 12);
                    })
                    .catch(error => {
                        console.error('Error fetching garage data:', error);
                        
                        // If API fails, add default markers as fallback
                        console.log("API fetch failed, adding default garage markers");
                        
                        // SUTTON 53 PARKING
                        L.marker([40.757700, -73.963900], {
                            icon: garageIcon
                        }).bindPopup("<b>SUTTON 53 PARKING LLC</b><br>410 EAST 54 STREET<br>NEW YORK, NY").addTo(map);
                        
                        // TIMES SQUARE GARAGE
                        L.marker([40.760800, -73.984700], {
                            icon: garageIcon
                        }).bindPopup("<b>TIMES SQUARE GARAGE</b><br>224 WEST 49TH STREET<br>NEW YORK, NY").addTo(map);
                    });

                // Add markers for all listings (as in original code)
                const listings = document.querySelectorAll(".card");
                const bounds = [];

                console.log(`Found ${listings.length} listings to add to map`);

                listings.forEach((listing) => {
                    try {
                    const location = parseLocation(listing.dataset.location);
                        const locationName = listing.dataset.locationName;
                        const title = listing.dataset.title;
                    const price = listing.dataset.price;
                    const rating = parseFloat(listing.dataset.rating) || 0;

                        console.log(`Adding listing: ${title} at ${location.lat}, ${location.lng}`);

                        // Create the marker but add it to the layer group instead of the map
                        const marker = L.marker([location.lat, location.lng], {
                            zIndexOffset: 1000  // Higher z-index to appear above garage markers
                        });
                        listingLayerGroup.addLayer(marker);
                        bounds.push([location.lat, location.lng]);

                        // Create popup content
                        const ratingHtml = rating ?
                            `<br><strong>Rating:</strong> ${generateStarRating(
                    rating
                    )} (${rating.toFixed(1)})` :
                            `<br><span class="text-muted">No reviews yet ${generateStarRating(
                    0
                    )}</span>`;

                        const popupContent = `
                            <strong>${title}</strong><br>
                            ${locationName}<br>
                            $${price}/hour
                            ${ratingHtml}
                        `;

                        marker.bindPopup(popupContent);
                    } catch (error) {
                        console.error("Error adding listing marker:", error);
                    }
                });

                // Add this after all markers are added, before the bounds check
                console.log("Fitting map to include all listings and garages");

                // Make sure we include garages in the initial bounds
                if (garageLayerGroup) {
                    // Add all garage locations to the bounds
                    garageLayerGroup.eachLayer(function(layer) {
                        if (layer.getLatLng) {
                            bounds.push([layer.getLatLng().lat, layer.getLatLng().lng]);
                        }
                    });
                }

                // Fit map to show all markers with padding
                if (bounds.length > 0) {
                    map.fitBounds(bounds, {
                        padding: [5, 5],  // Minimal padding
                        maxZoom: 18,      // Maximum practical zoom
                        minZoom: 17       // Enforce very high zoom level
                    });
                }
                
                // Make sure the map renders properly
                setTimeout(() => {
                    map.invalidateSize();
                    console.log("Map resized");
                }, 300);

                // Add this after the map is initialized in the initMap function
                // Around line 384 after the map is created and the tile layer is added
                map.addControl(createMapLegend());
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

            console.log("Showing map view");

            // Initialize map if not already done
            initMap();

            // Force map to render properly
            if (map) {
                console.log("Forcing map to resize");
                setTimeout(() => {
                    map.invalidateSize();
                    
                    // After invalidating size, make sure we're still showing all markers
                    const allBounds = [];
                    
                    // Add all listings to bounds
                    if (listingLayerGroup) {
                        listingLayerGroup.eachLayer(function(layer) {
                            if (layer.getLatLng) {
                                allBounds.push([layer.getLatLng().lat, layer.getLatLng().lng]);
                            }
                        });
                    }
                    
                    // Add all garages to bounds
                    if (garageLayerGroup) {
                        garageLayerGroup.eachLayer(function(layer) {
                            if (layer.getLatLng) {
                                allBounds.push([layer.getLatLng().lat, layer.getLatLng().lng]);
                            }
                        });
                    }
                    
                    // If we have markers, fit to bounds
                    if (allBounds.length > 0) {
                        map.fitBounds(allBounds, {
                            padding: [5, 5],  // Minimal padding 
                            maxZoom: 18,      // Maximum practical zoom
                            minZoom: 17       // Enforce very high zoom level
                        });
                        console.log("Fit map to include all markers with maximum practical zoom");
                    } else {
                        // Default to maximum practical zoom for NYC
                        map.setView([40.7128, -74.0060], 18);
                    }
                    
                    console.log("Map has been resized");
                }, 500);
            } else {
                console.error("Map object is not initialized!");
            }
        }

        // Add event listeners
        listViewBtn.addEventListener("click", showListView);
        mapViewBtn.addEventListener("click", showMapView);

        // Initialize with list view
        showListView();

        // Add a handler for tab switching - some browsers/devices need this
        window.addEventListener('resize', function() {
            if (mapView.classList.contains("active-view") && map) {
                console.log("Window resized, refreshing map view");
                map.invalidateSize();
            }
        });

        console.log("Map view setup complete");
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
            enableRadiusCheckbox.addEventListener("change", function() {
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
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });
});

function setupSearch() {
    const searchInput = document.getElementById("location-search");
    const searchButton = document.getElementById("search-location");

    if (!searchButton || !searchInput) return;

    searchButton.addEventListener("click", performSearch);
    searchInput.addEventListener("keypress", function(e) {
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

// This is a simpler function that directly adds garages to the map
function addGaragesDirectly(map) {
    console.log("Adding garages directly to map...");
    currentMap = map;
    
    // Create layer group if it doesn't exist
    if (!garageLayerGroup) {
        garageLayerGroup = L.layerGroup().addTo(map);
    }

    // Create marker icon - code remains the same
    const garageIcon = L.divIcon({
        html: `<div style="
            background-color: #2c3e50; 
            width: 22px;   /* Reduced from 28px */
            height: 22px;  /* Reduced from 28px */
            border-radius: 5px;
            display: flex; 
            justify-content: center; 
            align-items: center; 
            border: 1px solid white; /* Thinner border */
            box-shadow: 0 1px 3px rgba(0,0,0,0.4);
        ">
            <i class="fas fa-car" style="
                color: white; 
                font-size: 11px;  /* Reduced from 14px */
                transform: rotate(-45deg);
            "></i>
        </div>`,
        className: 'garage-marker',
        iconSize: [22, 22],     /* Reduced from [28, 28] */
        iconAnchor: [11, 22],   /* Adjusted for new size */
        popupAnchor: [0, -22]   /* Adjusted for new size */
    });

    // Create backup markers to use if API fails
    const backupGarages = [
        {
            name: "SUTTON 53 PARKING LLC",
            address: "410 EAST 54 STREET, NEW YORK, NY 10022",
            phone: "(877) 727-5464",
            lat: 40.757700,
            lng: -73.963900
        },
        {
            name: "TIMES SQUARE GARAGE", 
            address: "224 WEST 49TH STREET, NEW YORK, NY 10019",
            phone: "(212) 333-7275",
            lat: 40.760800,
            lng: -73.984700
        }
    ];

    if (!map) {
        console.error("Map object is null or undefined in addGaragesDirectly!");
        return;
    }

    // Add each garage marker from backup if needed
    function addBackupMarkers() {
        backupGarages.forEach((garage, index) => {
            try {
                console.log(`Adding backup garage ${index+1}/${backupGarages.length}: "${garage.name}" at ${garage.lat}, ${garage.lng}`);

                // Create marker and add to LAYER GROUP instead of map
                const marker = L.marker([garage.lat, garage.lng], {
                    icon: garageIcon,
                    title: garage.name,
                    zIndexOffset: 100  // Lower z-index to ensure garages stay behind listings
                });
                
                garageLayerGroup.addLayer(marker);

                // Create popup content
                const popupContent = `
                    <div class="garage-popup">
                        <h4 class="garage-name">${garage.name}</h4>
                        <div class="garage-address">
                            <i class="fas fa-map-marker-alt"></i>
                            <div>${garage.address}</div>
                        </div>
                        <div class="garage-phone">
                            <i class="fas fa-phone"></i>
                            <a href="tel:${garage.phone}">${garage.phone}</a>
                        </div>
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
    fetch('https://data.cityofnewyork.us/resource/5bhr-pjxt.json?$limit=50')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(garages => {
            console.log(`Fetched ${garages.length} garages from NYC API`);
            
            // Add markers for each garage
            garages.forEach(garage => {
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
                            garage.address_zip
                        ].filter(Boolean).join(' ');
                        
                        // Get capacity info
                        let capacity = "";
                        if (garage.detail) {
                            capacity = garage.detail;
                        }
                        
                        // Create marker and add to LAYER GROUP instead of map
                        const marker = L.marker([lat, lng], {
                            icon: garageIcon,
                            title: garage.business_name,
                            zIndexOffset: 100  // Lower z-index to ensure garages stay behind listings
                        });
                        
                        garageLayerGroup.addLayer(marker);
                        
                        // Create popup content
                        const popupContent = `
                            <div class="garage-popup">
                                <h4 class="garage-name">${garage.business_name}</h4>
                                <div class="garage-address">
                                    <i class="fas fa-map-marker-alt"></i>
                                    <div>${address}</div>
                                </div>
                                ${garage.contact_phone ? `
                                <div class="garage-phone">
                                    <i class="fas fa-phone"></i>
                                    <a href="tel:${garage.contact_phone}">${garage.contact_phone}</a>
                                </div>` : ''}
                                ${capacity ? `
                                <div class="garage-details">
                                    <i class="fas fa-info-circle"></i>
                                    <div>${capacity}</div>
                                </div>` : ''}
                            </div>
                        `;
                        
                        // Bind popup to marker
                        marker.bindPopup(popupContent);
                        
                    } catch (error) {
                        console.error(`Error adding garage ${garage.business_name}:`, error);
                    }
                }
            });
            
            // Center map on NYC after adding garages
            map.setView([40.7128, -74.0060], 12);
        })
        .catch(error => {
            console.error('Error fetching garage data:', error);
            
            // If API fails, add default markers as fallback
            console.log("API fetch failed, adding backup garage markers");
            addBackupMarkers();
        });

    console.log("Garage data request initiated");
}

// Create a new map legend with toggle functionality
function createMapLegend() {
    const legend = L.control({ position: 'bottomright' });

    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'map-legend');
        div.innerHTML = `
            <div style="background: white; padding: 8px; border-radius: 4px; box-shadow: 0 1px 5px rgba(0,0,0,0.4); font-size: 12px;">
                <div style="font-weight: bold; margin-bottom: 5px; text-align: center;">Map Legend</div>
                
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <input type="checkbox" id="toggle-garages" checked style="margin-right: 5px;">
                    <div style="
                        background-color: #2c3e50; 
                        width: 20px; 
                        height: 20px; 
                        border-radius: 5px;
                        display: flex; 
                        justify-content: center; 
                        align-items: center; 
                        border: 2px solid white; 
                        box-shadow: 0 1px 3px rgba(0,0,0,0.4);
                        margin-right: 8px;
                        margin-left: 3px;
                    ">
                        <i class="fas fa-car" style="color: white; font-size: 10px; transform: rotate(-45deg);"></i>
                    </div>
                    <label for="toggle-garages">Parking Garages</label>
                </div>
                
                <div style="display: flex; align-items: center;">
                    <input type="checkbox" id="toggle-listings" checked style="margin-right: 5px;">
                    <div style="
                        background-color: #3388ff; 
                        width: 20px; 
                        height: 20px; 
                        border-radius: 50%;
                        border: 2px solid white; 
                        box-shadow: 0 1px 3px rgba(0,0,0,0.4);
                        margin-right: 8px;
                        margin-left: 3px;
                    "></div>
                    <label for="toggle-listings">Available Listings</label>
                </div>
            </div>
        `;
        
        // Prevent clicks on the legend from propagating to the map
        L.DomEvent.disableClickPropagation(div);
        
        // Add event listeners to the toggle switches after a slight delay to ensure DOM is ready
        setTimeout(() => {
            const toggleGarages = document.getElementById('toggle-garages');
            const toggleListings = document.getElementById('toggle-listings');
            
            if (toggleGarages) {
                toggleGarages.addEventListener('change', function() {
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
            
            if (toggleListings) {
                toggleListings.addEventListener('change', function() {
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
        }, 100);
        
        return div;
    };

    return legend;
}