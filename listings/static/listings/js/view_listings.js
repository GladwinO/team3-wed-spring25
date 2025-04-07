console.log("view_listings.js loaded");

// Helper function to generate star HTML - extract it so it can be used anywhere
function generateStarRating(rating) {
  let starsHtml = '';
  
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
  const ratingElements = document.querySelectorAll('.rating-stars');
  ratingElements.forEach(function(ratingElement) {
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

        loadMoreBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
        loadMoreBtn.disabled = true;

        // Build URL with existing filters
        let url = new URL(window.location.href);
        url.searchParams.set("page", nextPage);
        url.searchParams.set("ajax", "1");

        fetch(url)
          .then((response) => response.text())
          .then((html) => {
            // Find and remove the existing load more button container
            const existingButtonContainer = document.querySelector(".text-center.my-4");
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
            const ratingStars = listingClone.querySelector('.rating-stars');
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
    const filterButton = document.querySelector('form.filter-box button[type="submit"]');
    
    if (filterButton) {
      filterButton.addEventListener('click', function(event) {
        event.preventDefault();
        const form = this.closest('form');
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
        lat: 40.69441, // Default to NYU tandon
        lng: -73.98653,
        address: locationString || "Location not specified",
      };
    }

    function initMap() {
      if (!map) {
        map = L.map("map-view").setView([40.69441, -73.98653], 13);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: "© OpenStreetMap contributors",
        }).addTo(map);

      // Add markers for all listings
      const listings = document.querySelectorAll(".card");
      const bounds = [];

        listings.forEach((listing) => {
          const location = parseLocation(listing.dataset.location);
          const locationName = listing.dataset.locationName;
          const title = listing.dataset.title;
          const price = listing.dataset.price;
          const rating = parseFloat(listing.dataset.rating) || 0;

          const marker = L.marker([location.lat, location.lng]).addTo(map);
          bounds.push([location.lat, location.lng]);

          // Create popup content
          const ratingHtml = rating
            ? `<br><strong>Rating:</strong> ${generateStarRating(rating)} (${rating.toFixed(1)})`
            : `<br><span class="text-muted">No reviews yet ${generateStarRating(0)}</span>`;

          const popupContent = `
            <strong>${title}</strong><br>
            ${locationName}<br>
            $${price}/hour
            ${ratingHtml}
          `;

          marker.bindPopup(popupContent);
        });

        // Fit map to show all markers
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

  // Add this function in your document ready handler
  function initializeEvFilters() {
    // Try multiple selectors to find the checkbox
    const evChargerCheckbox = 
      document.querySelector('input[name="has_ev_charger"]') || 
      document.querySelector('input[name="ev_charger"]') ||
      document.querySelector('#ev_charger');
    
    // Log what we found to help debug
    if (evChargerCheckbox) {
      console.log("Found EV checkbox with name:", evChargerCheckbox.name, "and id:", evChargerCheckbox.id);
    } else {
      console.error("EV charger checkbox not found with any known selector");
      // List all checkboxes to help debug
      console.log("All checkboxes:", document.querySelectorAll('input[type="checkbox"]'));
      return;
    }
    
    // Similarly, be robust with container selection
    const evContainers = document.querySelectorAll('.ev-charger-container');
    console.log("Found", evContainers.length, "EV container elements");
    
    if (evContainers.length === 0) {
      console.error("No EV container elements found");
      return;
    }
    
    function toggleEvFields() {
      const isChecked = evChargerCheckbox.checked;
      console.log("EV checkbox state:", isChecked);
      
      // Toggle visibility
      evContainers.forEach(container => {
        container.style.display = isChecked ? 'block' : 'none';
      });
      
      // Handle field values and disabled state
      const chargerLevelField = document.querySelector('[name="charger_level"]');
      const connectorTypeField = document.querySelector('[name="connector_type"]');
      
      if (chargerLevelField) {
        chargerLevelField.disabled = !isChecked;
        if (!isChecked) chargerLevelField.value = '';
      }
      
      if (connectorTypeField) {
        connectorTypeField.disabled = !isChecked;
        if (!isChecked) connectorTypeField.value = '';
      }
    }
    
    // Run the function initially
    toggleEvFields();
    
    // Add event listener for changes
    evChargerCheckbox.addEventListener('change', toggleEvFields);
  }

  // Initialize all components
  initializeFilters();
  initializeRecurringPatterns();
  setMinDates();
  setupLoadMoreButton();
  setupMapView();
  setupFilterButton();
  initializeEvFilters(); // Use this instead of the shared utility
});
