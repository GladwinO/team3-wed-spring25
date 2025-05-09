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

// Add this new function for the multiple days toggle
function initializeMultipleDaysToggle() {
  const multipleDaysToggle = document.getElementById('multipleDaysToggle');
  const singleDateContainer = document.getElementById('single-date-container');
  const multipleDaysContainer = document.getElementById('multiple-days-container');
  
  // Get all date inputs
  const singleStartDate = document.getElementById('single_start_date');
  const multiStartDate = document.getElementById('multi_start_date');
  const multiEndDate = document.getElementById('multi_end_date');
  const realStartDate = document.getElementById('real_start_date');
  const realEndDate = document.getElementById('real_end_date');
  
  // Function to update the hidden inputs
  function updateHiddenInputs() {
    if (multipleDaysToggle.checked) {
      // Multiple days mode
      realStartDate.value = multiStartDate.value;
      realEndDate.value = multiEndDate.value;
    } else {
      // Single day mode
      realStartDate.value = singleStartDate.value;
      realEndDate.value = singleStartDate.value; // End date equals start date in single mode
    }
  }
  
  // Set up toggle event
  multipleDaysToggle.addEventListener('change', function() {
    if (this.checked) {
      // Multiple days selected
      singleDateContainer.style.display = 'none';
      multipleDaysContainer.style.display = 'flex';
    } else {
      // Single day selected
      singleDateContainer.style.display = 'block';
      multipleDaysContainer.style.display = 'none';
    }
    updateHiddenInputs();
  });
  
  // Update hidden inputs when any date changes
  singleStartDate.addEventListener('change', updateHiddenInputs);
  multiStartDate.addEventListener('change', updateHiddenInputs);
  multiEndDate.addEventListener('change', updateHiddenInputs);
  
  // Initialize on page load
  updateHiddenInputs();
}

function toggleFilterPanel() {
  const filterPanel = document.getElementById("filter-panel");
  if (filterPanel.classList.contains("collapsed")) {
    filterPanel.classList.remove("collapsed");
    filterPanel.classList.add("expanded");
  } else {
    filterPanel.classList.remove("expanded");
    filterPanel.classList.add("collapsed");
  }

  // Resize map after animation completes
  setTimeout(() => {
    if (searchMap) {
      searchMap.invalidateSize(true);
    }
  }, 300);
}

function setupAdvancedFilters() {
  // Advanced filters modal functionality
  const advancedFiltersBtn = document.getElementById("advanced-filters-btn");
  const advancedFiltersModal = new bootstrap.Modal(
    document.getElementById("advanced-filters-modal")
  );

  if (advancedFiltersBtn) {
    advancedFiltersBtn.addEventListener("click", function () {
      advancedFiltersModal.show();
    });
  }

  // Apply advanced filters button - transfer values from modal to hidden form fields
  const applyAdvancedFiltersBtn = document.getElementById(
    "apply-advanced-filters"
  );
  if (applyAdvancedFiltersBtn) {
    applyAdvancedFiltersBtn.addEventListener("click", function () {
      // Booking type
      const filterType =
        document.querySelector('input[name="filter_type_modal"]:checked')
          ?.value || "single";
      document.getElementById("filter_type_hidden").value = filterType;

      // EV Charger options
      const hasEvCharger = document.getElementById("ev_charger").checked
        ? "on"
        : "";
      document.getElementById("has_ev_charger_hidden").value = hasEvCharger;

      if (hasEvCharger) {
        const chargerLevel = document.getElementById("charger_level").value;
        const connectorType = document.getElementById("connector_type").value;
        document.getElementById("charger_level_hidden").value = chargerLevel;
        document.getElementById("connector_type_hidden").value = connectorType;
      }

      // POSSIBLE BUG
      // Date and time for single booking
      if (filterType === "single") {
        const startDate = document.getElementById("single_start_date").value;
        const endDate = document.getElementById("single_end_date").value;
        const startTime = document.getElementById("start_time_select").value;
        const endTime = document.getElementById("end_time_select").value;

        document.getElementById("start_date_hidden").value = startDate;
        document.getElementById("end_date_hidden").value = endDate;
        document.getElementById("start_time_hidden").value = startTime;
        document.getElementById("end_time_hidden").value = endTime;
      }
      // Recurring booking details
      else if (filterType === "recurring") {
        const recurringStartDate = document.getElementById(
          "recurring_start_date"
        ).value;
        const recurringStartTime = document.getElementById(
          "recurring_start_time"
        ).value;
        const recurringEndTime =
          document.getElementById("recurring_end_time").value;
        const recurringPattern =
          document.querySelector(
            'input[name="recurring_pattern_modal"]:checked'
          )?.value || "daily";

        document.getElementById("recurring_start_date_hidden").value =
          recurringStartDate;
        document.getElementById("recurring_start_time_hidden").value =
          recurringStartTime;
        document.getElementById("recurring_end_time_hidden").value =
          recurringEndTime;
        document.getElementById("recurring_pattern_hidden").value =
          recurringPattern;

        if (recurringPattern === "daily") {
          const recurringEndDate =
            document.getElementById("recurring_end_date").value;
          document.getElementById("recurring_end_date_hidden").value =
            recurringEndDate;
        } else if (recurringPattern === "weekly") {
          const recurringWeeks =
            document.getElementById("recurring_weeks").value;
          document.getElementById("recurring_weeks_hidden").value =
            recurringWeeks;
        }

        const recurringOvernight = document.getElementById(
          "recurring_overnight"
        ).checked
          ? "on"
          : "";
        document.getElementById("recurring_overnight_hidden").value =
          recurringOvernight;
      }

      // Close the modal
      advancedFiltersModal.hide();
    });
  }
}

function setupRadiusToggle() {
  // Existing code for radius toggle functionality
  const enableRadiusCheckbox = document.getElementById("enable-radius");
  const radiusInputGroup = document.getElementById("radius-input-group");
  const radiusHint = document.getElementById("radius-hint");

  if (enableRadiusCheckbox && radiusInputGroup && radiusHint) {
    enableRadiusCheckbox.addEventListener("change", function () {
      radiusInputGroup.style.display = this.checked ? "flex" : "none";
      radiusHint.style.display = this.checked ? "none" : "block";
    });
  }
}

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

function initializeDateRangeToggle() {
  // Date range toggle
  const dateRangeToggle = document.getElementById("date-range-toggle");
  const endDateContainer = document.getElementById("end-date-container");

  if (dateRangeToggle && endDateContainer) {
    dateRangeToggle.addEventListener("click", function () {
      if (endDateContainer.style.display === "none") {
        endDateContainer.style.display = "block";
        this.classList.add("active");
      } else {
        endDateContainer.style.display = "none";
        this.classList.remove("active");
      }
    });
  }
}

function initializeEvChargerToggle() {
  // EV charger toggle
  const evChargerCheckbox = document.getElementById("ev_charger");
  const evOptionsContainer = document.getElementById("ev-options-container");

  if (evChargerCheckbox && evOptionsContainer) {
    evChargerCheckbox.addEventListener("change", function () {
      evOptionsContainer.style.display = this.checked ? "block" : "none";
    });
  }
}

function initializeRecurringPatternToggle() {
  // Recurring pattern toggle functionality
  const patternDailyRadio = document.getElementById("pattern_daily");
  const patternWeeklyRadio = document.getElementById("pattern_weekly");
  const dailyPatternFields = document.getElementById("daily-pattern-fields");
  const weeklyPatternFields = document.getElementById("weekly-pattern-fields");

  if (
    patternDailyRadio &&
    patternWeeklyRadio &&
    dailyPatternFields &&
    weeklyPatternFields
  ) {
    patternDailyRadio.addEventListener("change", function () {
      if (this.checked) {
        dailyPatternFields.style.display = "block";
        weeklyPatternFields.style.display = "none";
      }
    });

    patternWeeklyRadio.addEventListener("change", function () {
      if (this.checked) {
        dailyPatternFields.style.display = "none";
        weeklyPatternFields.style.display = "block";
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

// Function to apply advanced filters from modal
function applyAdvancedFilters() {
  // Get the main filter form
  const filterForm = document.getElementById("filter-form");

  // Basic validation for recurring booking
  const recurringStartDate = document.getElementById(
    "recurring_start_date"
  ).value;
  const recurringStartTime = document.getElementById(
    "recurring_start_time"
  ).value;
  const recurringEndTime = document.getElementById("recurring_end_time").value;
  // Transfer values from modal to main form

  // EV Charger options
  const hasEvCharger = document.getElementById("ev_charger").checked;
  const chargerLevel = document.getElementById("charger_level").value;
  const connectorType = document.getElementById("connector_type").value;

  // Create or update hidden inputs in the main form
  updateOrCreateHiddenInput(
    filterForm,
    "has_ev_charger",
    hasEvCharger ? "on" : ""
  );
  updateOrCreateHiddenInput(filterForm, "charger_level", chargerLevel);
  updateOrCreateHiddenInput(filterForm, "connector_type", connectorType);

  // Always set filter type to recurring for advanced filters
  updateOrCreateHiddenInput(filterForm, "filter_type", "recurring");

  // Get recurring booking details
  const recurringPattern =
    document.querySelector('input[name="recurring_pattern_modal"]:checked')
      ?.value || "daily";
  const recurringEndDate = document.getElementById("recurring_end_date").value;
  const recurringWeeks = document.getElementById("recurring_weeks").value;
  const recurringOvernight = document.getElementById(
    "recurring_overnight"
  ).checked;

  // Update form with recurring values
  updateOrCreateHiddenInput(
    filterForm,
    "recurring_start_date",
    recurringStartDate
  );
  updateOrCreateHiddenInput(
    filterForm,
    "recurring_start_time",
    recurringStartTime
  );
  updateOrCreateHiddenInput(filterForm, "recurring_end_time", recurringEndTime);
  updateOrCreateHiddenInput(filterForm, "recurring_pattern", recurringPattern);
  updateOrCreateHiddenInput(filterForm, "recurring_end_date", recurringEndDate);
  updateOrCreateHiddenInput(filterForm, "recurring_weeks", recurringWeeks);
  updateOrCreateHiddenInput(
    filterForm,
    "recurring_overnight",
    recurringOvernight ? "on" : ""
  );

  // Clear single booking fields to avoid conflicts
  updateOrCreateHiddenInput(filterForm, "start_date", "");
  updateOrCreateHiddenInput(filterForm, "end_date", "");
  updateOrCreateHiddenInput(filterForm, "start_time", "");
  updateOrCreateHiddenInput(filterForm, "end_time", "");

  // Parking spot size
  const parkingSpotSize = document.getElementById("parking_spot_size").value;
  document.getElementById("parking_spot_size_hidden").value = parkingSpotSize;
  // update or create parking spot size hidden input
  updateOrCreateHiddenInput(filterForm, "parking_spot_size", parkingSpotSize);

  // Close the modal
  const modal = bootstrap.Modal.getInstance(
    document.getElementById("advanced-filters-modal")
  );
  if (modal) {
    modal.hide();
  }

  // Submit the form
  filterForm.submit();
}

// Helper function to update or create hidden input fields
function updateOrCreateHiddenInput(form, name, value) {
  let input = form.querySelector(`input[name="${name}"]`);

  if (!input) {
    input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    form.appendChild(input);
  }

  input.value = value;
}

function initializePopover() {
  // Initialize all popovers
  var popoverTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="popover"]')
  );
  var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl);
  });
}

// Separate function to generate popup HTML
function generateListingPopupContent(listing) {
  // Generate rating HTML
  const ratingHtml = listing.rating
    ? `<div style="margin-bottom: 8px; display: flex; align-items: center;">
          <i class="fas fa-star" style="color: #f1c40f; margin-right: 8px;"></i>
          <span style="color: #34495e; font-size: 13px;">${listing.rating.toFixed(
            1
          )} (${generateStarRating(listing.rating)})</span>
        </div>`
    : `<div style="margin-bottom: 8px; display: flex; align-items: center;">
          <i class="fas fa-star" style="color: #bdc3c7; margin-right: 8px;"></i>
          <span style="color: #7f8c8d; font-size: 13px;">No reviews yet</span>
        </div>`;

  // Return the full popup HTML
  return `
    <div class="listing-popup" style="padding: 8px; min-width: 200px;">
      <div style="margin-bottom: 12px;">
        <h4 style="margin: 0; color: #2c3e50; font-size: 16px;">${
          listing.title
        }</h4>
      </div>
      <div style="margin-bottom: 10px; display: flex; align-items: flex-start;">
        <i class="fas fa-map-marker-alt" style="color: #7f8c8d; margin-right: 8px; margin-top: 3px;"></i>
        <div style="color: #34495e; font-size: 13px;">${
          listing.location_name
        }</div>
      </div>
      <div style="margin-bottom: 8px; display: flex; align-items: center;">
        <i class="fas fa-tag" style="color: #7f8c8d; margin-right: 8px;"></i>
        <span style="color: #34495e; font-size: 13px;">$${Math.abs(
          listing.price
        ).toFixed(2)}/hour</span>
      </div>
      ${ratingHtml}
      <div style="margin-top: 12px; text-align: center;">
        <a href="/booking/book/${
          listing.id
        }/" class="btn btn-primary btn-sm" style="width: 100%;">Book Now</a>
      </div>
    </div>
  `;
}

// Helper function to generate marker icon HTML
function createMarkerIconHtml(options = {}) {
  const {
    backgroundColor = "#ff3b30",
    width = "20px",
    height = "20px",
    borderRadius = "50%",
    border = "2px solid white",
  } = options;

  return `<div style="background-color: ${backgroundColor}; width: ${width}; height: ${height}; border-radius: ${borderRadius}; border: ${border};"></div>`;
}
