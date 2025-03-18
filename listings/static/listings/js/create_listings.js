let map;
let marker;
let locationData = {
  address: "",
  lat: "",
  lng: "",
};

// Initialize the map when the document is ready
document.addEventListener("DOMContentLoaded", function () {
  console.log("Initializing map");

  // Make sure the map div exists
  const mapDiv = document.getElementById("map");
  if (!mapDiv) {
    console.error(
      "Map container not found! Make sure a div with id 'map' exists."
    );
    return;
  }

  // Initialize the map
  map = L.map("map").setView([40.69441, -73.98653], 13); // Default to NYU tandon
  console.log("Map initialized");

  // Add OpenStreetMap tiles
  L.tileLayer("https://tile.openstreetmap.bzh/ca/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors",
  }).addTo(map);

  // Add click event to map
  map.on("click", onMapClick);

  // Set up search functionality
  setupSearch();

  // Load existing location if available
  loadExistingLocation();
});

function updateLocationField(address, lat, lng) {
  // Update the hidden location field with formatted data
  const locationString = `${address} [${lat}, ${lng}]`;
  const locationField = document.getElementById("id_location");
  if (locationField) {
    locationField.value = locationString;
  }

  // Store the data for later use
  locationData.address = address;
  locationData.lat = lat;
  locationData.lng = lng;
}

// Function to handle location selection
function onMapClick(e) {
  console.log("onMapClick", e);
  if (marker) {
    map.removeLayer(marker);
  }

  marker = L.marker(e.latlng).addTo(map);

  fetch(
    `https://nominatim.openstreetmap.org/reverse?format=json&lat=${e.latlng.lat}&lon=${e.latlng.lng}`
  )
    .then((response) => response.json())
    .then((data) => {
      const address = data.display_name;
      updateLocationField(address, e.latlng.lat, e.latlng.lng);
      marker.bindPopup(address).openPopup();
    })
    .catch((error) => console.error("Error:", error));
}

// Set up search functionality
function setupSearch() {
  console.log("setupSearch");
  const searchInput = document.getElementById("location-search");
  const searchButton = document.getElementById("search-location");

  if (!searchInput || !searchButton) {
    console.warn("Search elements not found");
    return;
  }

  // Add event listeners
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

function searchLocation() {
  console.log("searchLocation");
  const searchInput = document.getElementById("location-search");
  if (!searchInput) return;

  const query = searchInput.value;
  if (!query) return;

  fetch(
    `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
      query
    )}`
  )
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
    .catch((error) => console.error("Error:", error));
}

// Load existing location from the form if available
function loadExistingLocation() {
  const locationField = document.getElementById("id_location");
  if (!locationField || !locationField.value) return;

  const existingLocation = locationField.value;

  // Try to parse coordinates if they exist
  const match = existingLocation.match(/\[([-\d.]+),\s*([-\d.]+)\]/);
  if (match) {
    const lat = parseFloat(match[1]);
    const lng = parseFloat(match[2]);
    map.setView([lat, lng], 16);
    marker = L.marker([lat, lng]).addTo(map);
    marker.bindPopup(existingLocation.split("[")[0].trim()).openPopup();
  }
}

    // (Optional) You can add frontend overlap checking here if desired.
    // For now, we rely on backend validation and an alert on form submit.

    document.addEventListener("DOMContentLoaded", function() {
      console.log("Create Listing JS loaded.");

      // Simple frontend check for overlapping intervals before submission.
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
                  // Check overlap with existing intervals.
                  for (const interval of intervals) {
                      if (!(end <= interval.start || start >= interval.end)) {
                          alert("Availability slots cannot overlap.");
                          return false;
                      }
                  }
                  intervals.push({
                      start: start,
                      end: end
                  });
              }
          }
          return true;
      }

      // Attach submit handler to the form.
      document.getElementById("create-listing-form").addEventListener("submit", function(event) {
          if (!checkOverlappingSlots()) {
              event.preventDefault();
          }
      });

      // Function to update indices after deletion
      function updateFormIndices() {
          const formDivs = document.querySelectorAll('.slot-form');
          const totalFormsInput = document.querySelector('[name$="-TOTAL_FORMS"]');

          // Update form count
          totalFormsInput.value = formDivs.length.toString();

          // Update each form's index
          formDivs.forEach((div, idx) => {
              // Update data-index attribute
              div.setAttribute('data-index', idx.toString());

              // Update heading text
              const heading = div.querySelector('h5');
              if (heading) {
                  heading.innerHTML = `<i class="fas fa-clock text-secondary me-2"></i>Time Slot ${idx + 1}`;
              }

              // Update input names and IDs
              div.querySelectorAll('input, select, textarea, label').forEach(el => {
                  if (el.name) {
                      el.name = el.name.replace(/-\d+-/, `-${idx}-`);
                  }
                  if (el.id) {
                      el.id = el.id.replace(/_\d+_/, `_${idx}_`);
                  }
              });

              // Add delete button to all but the first form
              if (idx > 0) {
                  if (!div.querySelector('.delete-slot')) {
                      const deleteBtn = document.createElement('button');
                      deleteBtn.className = 'delete-slot';
                      deleteBtn.title = 'Delete this slot';
                      deleteBtn.type = 'button';
                      deleteBtn.innerHTML = '<i class="fas fa-times"></i>';
                      deleteBtn.addEventListener('click', handleDelete);
                      div.appendChild(deleteBtn);
                  }
              } else {
                  // Remove delete button from first form if it exists
                  const deleteBtn = div.querySelector('.delete-slot');
                  if (deleteBtn) {
                      deleteBtn.remove();
                  }
              }
          });
      }

      // Function to handle delete button click
      function handleDelete(e) {
          const slotForm = e.target.closest('.slot-form');
          if (slotForm) {
              slotForm.remove();
              updateFormIndices();
          }
      }

      // Add event listeners to delete buttons
      document.querySelectorAll('.delete-slot').forEach(btn => {
          btn.addEventListener('click', handleDelete);
      });

      // Dynamic form addition logic.
      const addSlotBtn = document.getElementById("add-slot-btn");
      const slotFormsContainer = document.getElementById("slot-forms-container");
      const totalFormsInput = document.querySelector('[name$="-TOTAL_FORMS"]');
      if (!addSlotBtn || !slotFormsContainer || !totalFormsInput) {
          console.error("Required elements for adding new slot not found.");
          return;
      }
      const formDivs = slotFormsContainer.getElementsByClassName("slot-form");
      if (formDivs.length === 0) {
          console.error("No slot form found to clone.");
          return;
      }
      const blankForm = formDivs[0].cloneNode(true);
      blankForm.querySelectorAll("input, select, textarea").forEach(el => el.value = "");
      const blankHeading = blankForm.querySelector("h5");
      if (blankHeading) blankHeading.textContent = "Time Slot ???";

      addSlotBtn.addEventListener("click", function() {
          let formCount = parseInt(totalFormsInput.value);
          let newForm = blankForm.cloneNode(true);
          newForm.querySelectorAll("input, select, textarea, label").forEach(function(el) {
              if (el.name) {
                  el.name = el.name.replace(/-\d+-/, `-${formCount}-`);
              }
              if (el.id) {
                  el.id = el.id.replace(/_\d+_/, `_${formCount}_`);
              }
          });

          // Set data-index attribute
          newForm.setAttribute('data-index', formCount.toString());

          // Update form heading
          const newHeading = newForm.querySelector("h5");
          if (newHeading) {
              newHeading.innerHTML = `<i class="fas fa-clock text-secondary me-2"></i>Time Slot ${formCount + 1}`;
          }

          // Add delete button to new form
          const deleteBtn = document.createElement('button');
          deleteBtn.className = 'delete-slot';
          deleteBtn.title = 'Remove this time slot';
          deleteBtn.type = 'button';
          deleteBtn.innerHTML = '<i class="fas fa-times"></i>';
          deleteBtn.addEventListener('click', handleDelete);
          newForm.appendChild(deleteBtn);

          slotFormsContainer.appendChild(newForm);
          formCount++;
          totalFormsInput.value = formCount.toString();
      });
  });