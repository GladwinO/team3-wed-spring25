let map;
let marker;
let locationData = {
  address: "",
  lat: "",
  lng: "",
};

// Run everything once the DOM is loaded.
document.addEventListener("DOMContentLoaded", function () {
  console.log("Combined Create Listing JS loaded.");

  // ========================
  // Map & Location Functions
  // ========================

  const mapDiv = document.getElementById("map");
  if (!mapDiv) {
    console.error("Map container not found! Make sure a div with id 'map' exists.");
  } else {
    // Initialize the map (choose one tile URL; here we use the OpenStreetMap default)
    map = L.map("map").setView([40.69441, -73.98653], 13); // Default to NYU Tandon
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap contributors",
    }).addTo(map);
    console.log("Map initialized and tiles added.");

    // Map click handler function
    function onMapClick(e) {
      console.log("Map clicked at:", e.latlng);
      if (marker) {
        map.removeLayer(marker);
      }
      marker = L.marker(e.latlng).addTo(map);
      // Reverse geocode with Nominatim
      fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${e.latlng.lat}&lon=${e.latlng.lng}`)
        .then((response) => response.json())
        .then((data) => {
          const address = data.display_name;
          updateLocationField(address, e.latlng.lat, e.latlng.lng);
          marker.bindPopup(address).openPopup();
        })
        .catch((error) => {
          console.error("Geocoding error:", error);
          updateLocationField("Selected location", e.latlng.lat, e.latlng.lng);
        });
    }
    map.on("click", onMapClick);
    console.log("Map click event handler added.");

    // Update the hidden location field and store location data
    function updateLocationField(address, lat, lng) {
      const locationString = `${address} [${lat}, ${lng}]`;
      const locationField = document.getElementById("id_location");
      if (locationField) {
        locationField.value = locationString;
        console.log("Location field updated:", locationString);
      } else {
        console.error("Location field not found");
      }
      locationData.address = address;
      locationData.lat = lat;
      locationData.lng = lng;
    }

    // Set up location search
    function setupSearch() {
      console.log("Setting up search functionality");
      const searchInput = document.getElementById("location-search");
      const searchButton = document.getElementById("search-location");
      if (!searchInput || !searchButton) {
        console.warn("Search elements not found");
        return;
      }
      searchButton.addEventListener("click", (e) => {
        e.preventDefault();
        searchLocation();
      });
      searchInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          searchLocation();
        }
      });
    }
    // Search function using Nominatim
    function searchLocation() {
      console.log("Searching for location");
      const searchInput = document.getElementById("location-search");
      if (!searchInput) return;
      const query = searchInput.value;
      if (!query) return;
      fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`)
        .then((response) => response.json())
        .then((data) => {
          if (data.length > 0) {
            const location = data[0];
            map.setView([location.lat, location.lon], 16);
            if (marker) {
              map.removeLayer(marker);
            }
            marker = L.marker([location.lat, location.lon]).addTo(map);
            updateLocationField(location.display_name, location.lat, location.lon);
            marker.bindPopup(location.display_name).openPopup();
          }
        })
        .catch((error) => console.error("Search error:", error));
    }

    // Load existing location from hidden field if available
    function loadExistingLocation() {
      const locationField = document.getElementById("id_location");
      if (!locationField || !locationField.value) return;
      const existingLocation = locationField.value;
      console.log("Existing location value:", existingLocation);
      const match = existingLocation.match(/\[([-\d.]+),\s*([-\d.]+)\]/);
      if (match) {
        const lat = parseFloat(match[1]);
        const lng = parseFloat(match[2]);
        map.setView([lat, lng], 16);
        marker = L.marker([lat, lng]).addTo(map);
        marker.bindPopup(existingLocation.split("[")[0].trim()).openPopup();
      }
    }

    // Initialize search and load existing location
    setupSearch();
    loadExistingLocation();
  } // end if mapDiv exists

  // =============================
  // Time Slot Form Functionality
  // =============================

  // Filter time options for today (disable past times)
  function filterTimeOptionsForToday(timeSelect) {
    const now = new Date();
    const currentHour = now.getHours();
    const currentMinute = now.getMinutes();
    const options = timeSelect.options;
    for (let i = 0; i < options.length; i++) {
      const timeValue = options[i].value;
      if (!timeValue) continue;
      const [hours, minutes] = timeValue.split(":").map(Number);
      if (hours < currentHour || (hours === currentHour && minutes <= currentMinute)) {
        options[i].disabled = true;
        options[i].title = "Cannot select past times";
      } else {
        options[i].disabled = false;
        options[i].title = "Available time slot";
      }
    }
    if (timeSelect.value && timeSelect.selectedIndex > -1 && timeSelect.options[timeSelect.selectedIndex].disabled) {
      const formGroup = timeSelect.closest(".mb-3");
      let errorDiv = formGroup.querySelector(".invalid-feedback");
      if (!errorDiv) {
        errorDiv = document.createElement("div");
        errorDiv.className = "invalid-feedback d-block";
        formGroup.appendChild(errorDiv);
      }
      errorDiv.textContent = "Selected time is in the past. Please choose a future time.";
      timeSelect.classList.add("is-invalid");
      for (let i = 0; i < options.length; i++) {
        if (!options[i].disabled) {
          timeSelect.selectedIndex = i;
          break;
        }
      }
    } else {
      const formGroup = timeSelect.closest(".mb-3");
      const errorDiv = formGroup.querySelector(".invalid-feedback");
      if (errorDiv) errorDiv.remove();
      timeSelect.classList.remove("is-invalid");
    }
  }

  // Handle date changes for time slot forms
  function handleDateChange(dateInput) {
    const formDiv = dateInput.closest(".slot-form");
    if (!formDiv) return;
    const startTimeSelect = formDiv.querySelector('select[name$="start_time"]');
    const endTimeSelect = formDiv.querySelector('select[name$="end_time"]');
    const selectedDate = dateInput.value;
    const today = new Date().toISOString().split("T")[0];
    if (selectedDate === today) {
      if (startTimeSelect) {
        filterTimeOptionsForToday(startTimeSelect);
        const startErrorDiv = startTimeSelect.closest(".mb-3").querySelector(".invalid-feedback");
        if (startErrorDiv) startErrorDiv.remove();
        startTimeSelect.classList.remove("is-invalid");
      }
      if (endTimeSelect) {
        filterTimeOptionsForToday(endTimeSelect);
        const endErrorDiv = endTimeSelect.closest(".mb-3").querySelector(".invalid-feedback");
        if (endErrorDiv) endErrorDiv.remove();
        endTimeSelect.classList.remove("is-invalid");
      }
    } else {
      if (startTimeSelect) {
        Array.from(startTimeSelect.options).forEach(opt => {
          opt.disabled = false;
          opt.title = "";
        });
        startTimeSelect.classList.remove("is-invalid");
        const startErrorDiv = startTimeSelect.closest(".mb-3").querySelector(".invalid-feedback");
        if (startErrorDiv) startErrorDiv.remove();
      }
      if (endTimeSelect) {
        Array.from(endTimeSelect.options).forEach(opt => {
          opt.disabled = false;
          opt.title = "";
        });
        endTimeSelect.classList.remove("is-invalid");
        const endErrorDiv = endTimeSelect.closest(".mb-3").querySelector(".invalid-feedback");
        if (endErrorDiv) endErrorDiv.remove();
      }
    }
  }

  // Handle time select changes
  function handleTimeChange(timeSelect) {
    const formDiv = timeSelect.closest(".slot-form");
    if (!formDiv) return;
    const dateInput = formDiv.querySelector('input[type="date"]');
    if (dateInput && dateInput.value === new Date().toISOString().split("T")[0]) {
      filterTimeOptionsForToday(timeSelect);
      if (timeSelect.options[timeSelect.selectedIndex].disabled) {
        event.preventDefault();
        event.stopPropagation();
        return false;
      }
    }
  }

  // Validate that end time is after start time for a slot form
  function validateEndTime(formDiv) {
    const startDate = formDiv.querySelector('input[name$="start_date"]').value;
    const endDate = formDiv.querySelector('input[name$="end_date"]').value;
    const startTime = formDiv.querySelector('select[name$="start_time"]').value;
    const endTime = formDiv.querySelector('select[name$="end_time"]').value;
    const endTimeSelect = formDiv.querySelector('select[name$="end_time"]');
    if (startDate && endDate && startTime && endTime) {
      const startDateTime = new Date(startDate + "T" + startTime);
      const endDateTime = new Date(endDate + "T" + endTime);
      const formGroup = endTimeSelect.closest(".mb-3");
      let errorDiv = formGroup.querySelector(".invalid-feedback");
      if (endDateTime <= startDateTime) {
        if (!errorDiv) {
          errorDiv = document.createElement("div");
          errorDiv.className = "invalid-feedback d-block";
          formGroup.appendChild(errorDiv);
        }
        errorDiv.textContent = "End time must be after start time";
        endTimeSelect.classList.add("is-invalid");
        return false;
      } else {
        if (errorDiv) errorDiv.remove();
        endTimeSelect.classList.remove("is-invalid");
        return true;
      }
    }
    return true;
  }

  // Check overlapping time slots before submission
  function checkOverlappingSlots() {
    const forms = document.querySelectorAll(".slot-form");
    const intervals = [];
    for (const formDiv of forms) {
      const startDateVal = formDiv.querySelector("input[name$='start_date']").value;
      const endDateVal = formDiv.querySelector("input[name$='end_date']").value;
      const startTimeVal = formDiv.querySelector("select[name$='start_time']").value;
      const endTimeVal = formDiv.querySelector("select[name$='end_time']").value;
      if (startDateVal && startTimeVal && endDateVal && endTimeVal) {
        const start = new Date(startDateVal + "T" + startTimeVal);
        const end = new Date(endDateVal + "T" + endTimeVal);
        if (start >= end) {
          alert("Each slot's start time must be before its end time.");
          return false;
        }
        for (const interval of intervals) {
          if (!(end <= interval.start || start >= interval.end)) {
            alert("Availability slots cannot overlap.");
            return false;
          }
        }
        intervals.push({ start, end });
      }
    }
    return true;
  }

  // Create a new time slot form element
  function createNewSlotForm(index) {
    const template = `
      <div class="slot-form border p-3 mb-3" data-index="${index}">
          <div class="d-flex justify-content-between align-items-center mb-3">
              <h5 class="mb-0">
                  <i class="fas fa-clock text-secondary me-2"></i>Time Slot ${index + 1}
              </h5>
              <button type="button" class="delete-slot" title="Delete this slot">
                  <i class="fas fa-times"></i>
              </button>
          </div>
          <div class="row">
              <div class="col-md-6 mb-3">
                  <div class="row">
                      <div class="col-md-6 mb-3">
                          <label class="form-label">Start Date</label>
                          <input type="date" name="form-${index}-start_date" id="id_form-${index}-start_date" class="form-control">
                      </div>
                      <div class="col-md-6 mb-3">
                          <label class="form-label">End Date</label>
                          <input type="date" name="form-${index}-end_date" id="id_form-${index}-end_date" class="form-control">
                      </div>
                  </div>
              </div>
              <div class="col-md-6 mb-3">
                  <div class="row">
                      <div class="col-md-6 mb-3">
                          <label class="form-label">Start Time</label>
                          <select name="form-${index}-start_time" id="id_form-${index}-start_time" class="form-select">
                              <option value="">Select start time</option>
                              <!-- Options will be copied from the first form -->
                          </select>
                      </div>
                      <div class="col-md-6 mb-3">
                          <label class="form-label">End Time</label>
                          <select name="form-${index}-end_time" id="id_form-${index}-end_time" class="form-select">
                              <option value="">Select end time</option>
                              <!-- Options will be copied from the first form -->
                          </select>
                      </div>
                  </div>
              </div>
          </div>
          <input type="hidden" name="form-${index}-id" id="id_form-${index}-id">
      </div>
    `;
    const tempDiv = document.createElement("div");
    tempDiv.innerHTML = template.trim();
    return tempDiv.firstChild;
  }

  // Delete slot form handler
  function handleDelete(e) {
    const slotForm = e.target.closest(".slot-form");
    if (slotForm) {
      slotForm.remove();
      updateFormIndices();
    }
  }

  // Update form indices after deletion
  function updateFormIndices() {
    const formDivs = document.querySelectorAll(".slot-form");
    const totalFormsInput = document.querySelector('[name="form-TOTAL_FORMS"]');
    totalFormsInput.value = formDivs.length.toString();
    formDivs.forEach((div, idx) => {
      div.setAttribute("data-index", idx.toString());
      const heading = div.querySelector("h5");
      if (heading) {
        heading.innerHTML = `<i class="fas fa-clock text-secondary me-2"></i>Time Slot ${idx + 1}`;
      }
      div.querySelectorAll("input, select, label").forEach(el => {
        if (el.name) {
          el.name = el.name.replace(/form-\d+-/, `form-${idx}-`);
        }
        if (el.id) {
          el.id = el.id.replace(/id_form-\d+-/, `id_form-${idx}-`);
        }
      });
    });
  }

  // Attach listeners to date and time inputs for slot forms
  function attachDateListeners() {
    document.querySelectorAll('input[type="date"]').forEach(dateInput => {
      dateInput.addEventListener("change", () => {
        handleDateChange(dateInput);
        validateEndTime(dateInput.closest(".slot-form"));
      });
      handleDateChange(dateInput);
    });
    document.querySelectorAll('select[name$="start_time"], select[name$="end_time"]').forEach(timeSelect => {
      timeSelect.addEventListener("change", (event) => {
        handleTimeChange(timeSelect);
        validateEndTime(timeSelect.closest(".slot-form"));
        if (timeSelect.options[timeSelect.selectedIndex].disabled) {
          event.preventDefault();
          event.stopPropagation();
          return false;
        }
      });
    });
  }
  attachDateListeners();

  // Add submit handler to check overlapping slots
  document.getElementById("create-listing-form").addEventListener("submit", function (event) {
    let isValid = true;
    document.querySelectorAll(".slot-form").forEach(formDiv => {
      if (!validateEndTime(formDiv)) isValid = false;
    });
    if (!isValid || !checkOverlappingSlots()) {
      event.preventDefault();
    }
  });

  // Dynamic form addition for time slots
  const addSlotBtn = document.getElementById("add-slot-btn");
  const slotFormsContainer = document.getElementById("slot-forms-container");
  const totalFormsInput = document.querySelector('[name="form-TOTAL_FORMS"]');
  if (!addSlotBtn || !slotFormsContainer || !totalFormsInput) {
    console.error("Required elements for adding new slot not found.");
  } else {
    const formDivs = slotFormsContainer.getElementsByClassName("slot-form");
    if (formDivs.length === 0) {
      console.error("No slot form found to clone.");
    } else {
      // Clone the first form as a blank template.
      const blankForm = formDivs[0].cloneNode(true);
      blankForm.querySelectorAll("input, select, textarea").forEach(el => el.value = "");
      const blankHeading = blankForm.querySelector("h5");
      if (blankHeading) blankHeading.textContent = "Time Slot ???";

      addSlotBtn.addEventListener("click", function () {
        let formCount = parseInt(totalFormsInput.value);
        let newForm = blankForm.cloneNode(true);
        newForm.querySelectorAll("input, select, textarea, label").forEach(function (el) {
          if (el.name) {
            el.name = el.name.replace(/-\d+-/, `-${formCount}-`);
          }
          if (el.id) {
            el.id = el.id.replace(/_\d+_/, `_${formCount}_`);
          }
        });
        newForm.setAttribute("data-index", formCount.toString());
        const newHeading = newForm.querySelector("h5");
        if (newHeading) {
          newHeading.innerHTML = `<i class="fas fa-clock text-secondary me-2"></i>Time Slot ${formCount + 1}`;
        }
        const deleteBtn = document.createElement("button");
        deleteBtn.className = "delete-slot";
        deleteBtn.title = "Remove this time slot";
        deleteBtn.type = "button";
        deleteBtn.innerHTML = '<i class="fas fa-times"></i>';
        deleteBtn.addEventListener("click", handleDelete);
        newForm.appendChild(deleteBtn);
        slotFormsContainer.appendChild(newForm);
        formCount++;
        totalFormsInput.value = formCount.toString();
      });
    }
  }

  // Additional delete button listener for any existing delete buttons.
  document.querySelectorAll(".delete-slot").forEach(btn => {
    btn.addEventListener("click", handleDelete);
  });

  // Initialize EV charger fields if utility is available
  if (typeof ListingFormUtils !== 'undefined') {
    ListingFormUtils.initializeEvChargerFields();
  }

}); // End DOMContentLoaded