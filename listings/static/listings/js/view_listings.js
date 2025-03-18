console.log("view_listings.js loaded");
document.addEventListener("DOMContentLoaded", function () {
  // Filter type toggle handlers
  const filterSingle = document.getElementById("filter_single");
  const filterMultiple = document.getElementById("filter_multiple");
  const filterRecurring = document.getElementById("filter_recurring");

  const singleFilter = document.getElementById("single-filter");
  const multipleFilter = document.getElementById("multiple-filter");
  const recurringFilter = document.getElementById("recurring-filter");

  // INITIALIZATION: Make sure only the selected filter is visible on page load
  if (filterSingle && filterSingle.checked) {
    singleFilter.style.display = "block";
    multipleFilter.style.display = "none";
    recurringFilter.style.display = "none";
  } else if (filterMultiple && filterMultiple.checked) {
    singleFilter.style.display = "none";
    multipleFilter.style.display = "block";
    recurringFilter.style.display = "none";
  } else if (filterRecurring && filterRecurring.checked) {
    singleFilter.style.display = "none";
    multipleFilter.style.display = "none";
    recurringFilter.style.display = "block";
  }

  // Add event listeners for filter type changes
  if (filterSingle && filterMultiple && filterRecurring) {
    filterSingle.addEventListener("change", function () {
      if (this.checked) {
        singleFilter.style.display = "block";
        multipleFilter.style.display = "none";
        recurringFilter.style.display = "none";
      }
    });

    filterMultiple.addEventListener("change", function () {
      if (this.checked) {
        singleFilter.style.display = "none";
        multipleFilter.style.display = "block";
        recurringFilter.style.display = "none";
      }
    });

    filterRecurring.addEventListener("change", function () {
      if (this.checked) {
        singleFilter.style.display = "none";
        multipleFilter.style.display = "none";
        recurringFilter.style.display = "block";
      }
    });
  }

  // Recurring pattern toggle
  const patternDaily = document.getElementById("pattern_daily");
  const patternWeekly = document.getElementById("pattern_weekly");
  const dailyFields = document.getElementById("daily-pattern-fields");
  const weeklyFields = document.getElementById("weekly-pattern-fields");

  // INITIALIZATION: Make sure the correct pattern fields are visible on page load
  if (patternDaily && patternWeekly) {
    if (patternDaily.checked) {
      dailyFields.style.display = "block";
      weeklyFields.style.display = "none";
    } else if (patternWeekly.checked) {
      dailyFields.style.display = "none";
      weeklyFields.style.display = "block";
    }

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

  // Get today's date in YYYY-MM-DD format
  const today = new Date().toISOString().split("T")[0];

  // Apply minimum date to all date inputs
  const dateInputs = document.querySelectorAll('input[type="date"]');
  dateInputs.forEach((input) => {
    input.min = today;
  });

  // Handle dynamically added intervals
  const addIntervalBtn = document.getElementById("add-interval");
  if (addIntervalBtn) {
    addIntervalBtn.addEventListener("click", function () {
      // Set timeout to allow DOM to update
      setTimeout(() => {
        const newDateInputs = document.querySelectorAll(
          'input[type="date"]:not([min])'
        );
        newDateInputs.forEach((input) => {
          input.min = today;
        });
      }, 100);
    });
  }

  // Load more button functionality
  const loadMoreBtn = document.getElementById("load-more-btn");
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener("click", function () {
      const nextPage = this.getAttribute("data-next-page");
      const listingsContainer = document.querySelector(".listings-container");

      // Show loading state
      loadMoreBtn.innerHTML =
        '<i class="fas fa-circle-notch fa-spin me-2"></i> Loading...';
      loadMoreBtn.disabled = true;

      // Build URL with existing filters
      let url = new URL(window.location.href);
      url.searchParams.set("page", nextPage);

      // Add parameter to indicate this is an AJAX request
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

          // Create a temporary element to parse the HTML
          const parser = new DOMParser();
          const doc = parser.parseFromString(html, "text/html");

          // Get all listing cards from the response (but not the button)
          const newListings = doc.querySelectorAll(".card");

          // Append each new listing to our container
          newListings.forEach((listing) => {
            listingsContainer.appendChild(listing.cloneNode(true));
          });

          // Find the load more button in the response
          const loadMoreContainer = doc.querySelector(".text-center.my-4");
          if (loadMoreContainer) {
            // There are more pages, append the new button
            listingsContainer.appendChild(loadMoreContainer.cloneNode(true));

            // Re-attach the event listener to the new button
            const newLoadMoreBtn = document.getElementById("load-more-btn");
            if (newLoadMoreBtn) {
              // Make sure the button text is correct (no icons)
              newLoadMoreBtn.innerHTML = "Load More Listings";
              newLoadMoreBtn.addEventListener("click", arguments.callee);
            }
          }
        })
        .catch((error) => {
          console.error("Error loading more listings:", error);
          loadMoreBtn.innerHTML =
            '<i class="fas fa-exclamation-triangle me-2"></i> Error Loading';
          loadMoreBtn.disabled = false;
        });
    });
  }
});

document.addEventListener("DOMContentLoaded", function () {
  // View toggle functionality
  const listViewBtn = document.getElementById("list-view-btn");
  const mapViewBtn = document.getElementById("map-view-btn");
  const listView = document.getElementById("list-view");
  const mapView = document.getElementById("map-view");
  let map;

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
      map = L.map("map-view").setView([40.69441, -73.98653], 13); // Default to NYU tandon
      L.tileLayer("https://tile.openstreetmap.bzh/ca/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "© OpenStreetMap contributors",
      }).addTo(map);

      // Fetch traffic data from analytics app
      fetch("/analytics/traffic-data/")
        .then((response) => response.json())
        .then((data) => {
          // Create and add the heatmap layer
          const heat = L.heatLayer(data.data, {
            radius: 25,
            blur: 15,
            maxZoom: 10,
            gradient: { 0.4: "blue", 0.6: "lime", 0.8: "yellow", 1: "red" },
          }).addTo(map);
        })
        .catch((error) => {
          console.error("Error fetching traffic data:", error);
        });

      // Add markers for all listings
      const listings = document.querySelectorAll(".card");
      const bounds = [];

      listings.forEach((listing) => {
        // Get all data from data attributes
        const location = parseLocation(listing.dataset.location);
        const locationName = listing.dataset.locationName;
        const title = listing.dataset.title;
        const price = listing.dataset.price;
        const rating = parseFloat(listing.dataset.rating) || 0;

        // Create marker
        const marker = L.marker([location.lat, location.lng]).addTo(map);
        bounds.push([location.lat, location.lng]);

        // Generate stars HTML
        function generateStars(rating) {
          let starsHtml = '<div class="rating-stars">';

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

          starsHtml += "</div>";
          return starsHtml;
        }

        // Create rating HTML
        const ratingHtml = rating
          ? `<br><strong>Rating:</strong> ${generateStars(
              rating
            )} (${rating.toFixed(1)})`
          : `<br><span class="text-muted">No reviews yet ${generateStars(
              0
            )}</span>`;

        // Create popup content
        const popupContent = `
          <strong>${title}</strong><br>
          ${locationName}<br>
          $${price}/hour
          ${ratingHtml}
        `;

        marker.bindPopup(popupContent);
      });

      // Fit map to show all markers if there are any
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

    // change list view button style since we are switching to map viewfd
    listViewBtn.classList.remove("btn-primary");
    listViewBtn.classList.add("btn-outline-primary");
    // remove active from list view button
    listViewBtn.classList.remove("active");

    initMap();
    if (map) {
      map.invalidateSize(); // Ensures map renders correctly
    }
  }

  // Event Listeners
  listViewBtn.addEventListener("click", showListView);
  mapViewBtn.addEventListener("click", showMapView);

  // Initialize with list view
  showListView();
});

document.addEventListener("DOMContentLoaded", function () {
  const singleRadio = document.getElementById("filter_single");
  const multipleRadio = document.getElementById("filter_multiple");
  const singleSection = document.getElementById("single-filter");
  const multipleSection = document.getElementById("multiple-filter");

  function toggleFilterSections() {
    if (singleRadio.checked) {
      singleSection.style.display = "";
      multipleSection.style.display = "none";
    } else {
      singleSection.style.display = "none";
      multipleSection.style.display = "";
    }
  }

  singleRadio.addEventListener("change", toggleFilterSections);
  multipleRadio.addEventListener("change", toggleFilterSections);
  toggleFilterSections();

  // Multiple intervals: add new interval row
  const addIntervalBtn = document.getElementById("add-interval");
  const intervalsContainer = document.getElementById("intervals-container");
  let intervalCount =
    parseInt(document.getElementById("interval_count").value) || 1;

  addIntervalBtn.addEventListener("click", function () {
    intervalCount += 1;
    document.getElementById("interval_count").value = intervalCount;
    const intervalRow = document.createElement("div");
    intervalRow.classList.add("row", "interval-row");
    intervalRow.setAttribute("data-index", intervalCount);
    intervalRow.innerHTML = `
      <div class="col-md-3">
        <label for="start_date_${intervalCount}" class="form-label">Interval ${intervalCount} Start Date</label>
        <input type="date" class="form-control" id="start_date_${intervalCount}" name="start_date_${intervalCount}">
      </div>
      <div class="col-md-3">
        <label for="end_date_${intervalCount}" class="form-label">Interval ${intervalCount} End Date</label>
        <input type="date" class="form-control" id="end_date_${intervalCount}" name="end_date_${intervalCount}">
      </div>
      <div class="col-md-3">
        <label for="start_time_${intervalCount}" class="form-label">Interval ${intervalCount} Start Time</label>
        <select class="form-select" id="start_time_${intervalCount}" name="start_time_${intervalCount}">
          <option value="">Select start time</option>
          {% for value, label in half_hour_choices %}
            <option value="{{ value }}">{{ label }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-3">
        <label for="end_time_${intervalCount}" class="form-label">Interval ${intervalCount} End Time</label>
        <select class="form-select" id="end_time_${intervalCount}" name="end_time_${intervalCount}">
          <option value="">Select end time</option>
          {% for value, label in half_hour_choices %}
            <option value="{{ value }}">{{ label }}</option>
          {% endfor %}
        </select>
      </div>
    `;
    intervalsContainer.appendChild(intervalRow);
  });
});
