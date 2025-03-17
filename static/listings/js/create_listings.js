let map;
let marker;
let locationData = {
    address: "",
    lat: "",
    lng: "",
};

// Initialize the map when the document is ready
document.addEventListener("DOMContentLoaded", function() {
    console.log("Create Listing JS loaded.");

    // Make sure the map div exists
    const mapDiv = document.getElementById("map");
    if (!mapDiv) {
        console.error("Map container not found! Make sure a div with id 'map' exists.");
        return;
    }
    console.log("Map container found:", mapDiv);

    try {
        // Initialize the map
        map = L.map("map").setView([40.69441, -73.98653], 13); // Default to NYU tandon
        console.log("Map object created:", map);

        // Add OpenStreetMap tiles
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "© OpenStreetMap contributors",
        }).addTo(map);
        console.log("Map tiles added");

        // Add click event to map
        map.on("click", function(e) {
            console.log("Map clicked at:", e.latlng);

            // Remove existing marker if any
            if (marker) {
                map.removeLayer(marker);
            }

            // Add new marker
            marker = L.marker(e.latlng).addTo(map);

            // Reverse geocode the coordinates
            fetch(
                    `https://nominatim.openstreetmap.org/reverse?format=json&lat=${e.latlng.lat}&lon=${e.latlng.lng}`
                )
                .then((response) => response.json())
                .then((data) => {
                    console.log("Geocoding response:", data);
                    const address = data.display_name;
                    updateLocationField(address, e.latlng.lat, e.latlng.lng);
                    marker.bindPopup(address).openPopup();
                })
                .catch((error) => {
                    console.error("Geocoding error:", error);
                    // Still update with coordinates even if geocoding fails
                    updateLocationField("Selected location", e.latlng.lat, e.latlng.lng);
                });
        });
        console.log("Click event handler added to map");

        // Set up search functionality
        setupSearch();
        console.log("Search functionality set up");

        // Load existing location if available
        loadExistingLocation();
        console.log("Existing location loaded (if any)");
    } catch (error) {
        console.error("Error initializing map:", error);
    }

    // Function to update the location field with formatted data
    function updateLocationField(address, lat, lng) {
        console.log("Updating location field with:", { address, lat, lng });
        // Update the hidden location field with formatted data
        const locationString = `${address} [${lat}, ${lng}]`;
        const locationField = document.getElementById("id_location");
        if (locationField) {
            locationField.value = locationString;
            console.log("Location field updated:", locationString);
        } else {
            console.error("Location field not found");
        }

        // Store the data for later use
        locationData.address = address;
        locationData.lat = lat;
        locationData.lng = lng;
    }

    // Function to set up location search
    function setupSearch() {
        console.log("Setting up search functionality");
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

    // Function to handle location search
    function searchLocation() {
        console.log("Searching for location");
        const searchInput = document.getElementById("location-search");
        if (!searchInput) return;

        const query = searchInput.value;
        if (!query) return;

        console.log("Search query:", query);
        fetch(
                `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`
            )
            .then((response) => response.json())
            .then((data) => {
                console.log("Search results:", data);
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

    // Function to load existing location
    function loadExistingLocation() {
        console.log("Loading existing location");
        const locationField = document.getElementById("id_location");
        if (!locationField || !locationField.value) return;

        const existingLocation = locationField.value;
        console.log("Existing location value:", existingLocation);

        // Try to parse coordinates if they exist
        const match = existingLocation.match(/\[([-\d.]+),\s*([-\d.]+)\]/);
        if (match) {
            const lat = parseFloat(match[1]);
            const lng = parseFloat(match[2]);
            console.log("Parsed coordinates:", { lat, lng });
            map.setView([lat, lng], 16);
            marker = L.marker([lat, lng]).addTo(map);
            marker.bindPopup(existingLocation.split("[")[0].trim()).openPopup();
        }
    }

    // Function to filter time options for today's date
    function filterTimeOptionsForToday(timeSelect) {
        const now = new Date();
        const currentHour = now.getHours();
        const currentMinute = now.getMinutes();

        // Get all options
        const options = timeSelect.options;

        // Loop through options and disable past times
        for (let i = 0; i < options.length; i++) {
            const timeValue = options[i].value;
            if (!timeValue) continue; // Skip empty option

            const [hours, minutes] = timeValue.split(':').map(Number);

            if (hours < currentHour || (hours === currentHour && minutes <= currentMinute)) {
                options[i].disabled = true;
                options[i].title = "Cannot select past times";
            } else {
                options[i].disabled = false;
                options[i].title = "Available time slot";
            }
        }

        // Only show error if there's a selected time and it's disabled
        if (timeSelect.value && timeSelect.selectedIndex > -1 && timeSelect.options[timeSelect.selectedIndex].disabled) {
            // Show error message
            const formGroup = timeSelect.closest('.mb-3');
            let errorDiv = formGroup.querySelector('.invalid-feedback');
            if (!errorDiv) {
                errorDiv = document.createElement('div');
                errorDiv.className = 'invalid-feedback d-block';
                formGroup.appendChild(errorDiv);
            }
            errorDiv.textContent = "Selected time is in the past. Please choose a future time.";
            timeSelect.classList.add('is-invalid');

            // Select next available time
            for (let i = 0; i < options.length; i++) {
                if (!options[i].disabled) {
                    timeSelect.selectedIndex = i;
                    break;
                }
            }
        } else {
            // Clear error if selection is valid or no selection
            const formGroup = timeSelect.closest('.mb-3');
            const errorDiv = formGroup.querySelector('.invalid-feedback');
            if (errorDiv) {
                errorDiv.remove();
            }
            timeSelect.classList.remove('is-invalid');
        }
    }

    // Function to handle date input changes
    function handleDateChange(dateInput) {
        const formDiv = dateInput.closest('.slot-form');
        if (!formDiv) return;

        const startTimeSelect = formDiv.querySelector('select[name$="start_time"]');
        const endTimeSelect = formDiv.querySelector('select[name$="end_time"]');

        const selectedDate = dateInput.value;
        const today = new Date().toISOString().split('T')[0];

        // If selected date is today, filter time options but don't show messages yet
        if (selectedDate === today) {
            if (startTimeSelect) {
                filterTimeOptionsForToday(startTimeSelect);
                // Clear any existing error messages
                const startErrorDiv = startTimeSelect.closest('.mb-3').querySelector('.invalid-feedback');
                if (startErrorDiv) startErrorDiv.remove();
                startTimeSelect.classList.remove('is-invalid');
            }
            if (endTimeSelect) {
                filterTimeOptionsForToday(endTimeSelect);
                // Clear any existing error messages
                const endErrorDiv = endTimeSelect.closest('.mb-3').querySelector('.invalid-feedback');
                if (endErrorDiv) endErrorDiv.remove();
                endTimeSelect.classList.remove('is-invalid');
            }
        } else {
            // Enable all options for future dates
            if (startTimeSelect) {
                Array.from(startTimeSelect.options).forEach(opt => {
                    opt.disabled = false;
                    opt.title = "";
                });
                startTimeSelect.classList.remove('is-invalid');
                const startErrorDiv = startTimeSelect.closest('.mb-3').querySelector('.invalid-feedback');
                if (startErrorDiv) startErrorDiv.remove();
            }
            if (endTimeSelect) {
                Array.from(endTimeSelect.options).forEach(opt => {
                    opt.disabled = false;
                    opt.title = "";
                });
                endTimeSelect.classList.remove('is-invalid');
                const endErrorDiv = endTimeSelect.closest('.mb-3').querySelector('.invalid-feedback');
                if (endErrorDiv) endErrorDiv.remove();
            }
        }
    }

    // Also handle time select changes directly
    function handleTimeChange(timeSelect) {
        const formDiv = timeSelect.closest('.slot-form');
        if (!formDiv) return;

        const dateInput = formDiv.querySelector('input[type="date"]');
        if (dateInput && dateInput.value === new Date().toISOString().split('T')[0]) {
            filterTimeOptionsForToday(timeSelect);

            // If the selected time is disabled (past time), prevent the change
            if (timeSelect.options[timeSelect.selectedIndex].disabled) {
                event.preventDefault();
                event.stopPropagation();
                return false;
            }
        }
    }

    // Function to validate end time is after start time
    function validateEndTime(formDiv) {
        const startDate = formDiv.querySelector('input[name$="start_date"]').value;
        const endDate = formDiv.querySelector('input[name$="end_date"]').value;
        const startTime = formDiv.querySelector('select[name$="start_time"]').value;
        const endTime = formDiv.querySelector('select[name$="end_time"]').value;
        const endTimeSelect = formDiv.querySelector('select[name$="end_time"]');

        if (startDate && endDate && startTime && endTime) {
            const startDateTime = new Date(startDate + 'T' + startTime);
            const endDateTime = new Date(endDate + 'T' + endTime);

            const formGroup = endTimeSelect.closest('.mb-3');
            let errorDiv = formGroup.querySelector('.invalid-feedback');

            if (endDateTime <= startDateTime) {
                if (!errorDiv) {
                    errorDiv = document.createElement('div');
                    errorDiv.className = 'invalid-feedback d-block';
                    formGroup.appendChild(errorDiv);
                }
                errorDiv.textContent = "End time must be after start time";
                endTimeSelect.classList.add('is-invalid');
                return false;
            } else {
                if (errorDiv) {
                    errorDiv.remove();
                }
                endTimeSelect.classList.remove('is-invalid');
                return true;
            }
        }
        return true;
    }

    // Attach date change listeners to all date inputs
    function attachDateListeners() {
        document.querySelectorAll('input[type="date"]').forEach(dateInput => {
            dateInput.addEventListener('change', () => {
                handleDateChange(dateInput);
                validateEndTime(dateInput.closest('.slot-form'));
            });
            // Also check current value on page load
            handleDateChange(dateInput);
        });

        // Add listeners for time selects with event parameter
        document.querySelectorAll('select[name$="start_time"], select[name$="end_time"]').forEach(timeSelect => {
            timeSelect.addEventListener('change', (event) => {
                handleTimeChange(timeSelect);
                validateEndTime(timeSelect.closest('.slot-form'));

                // If the selected time is disabled, prevent the change
                if (timeSelect.options[timeSelect.selectedIndex].disabled) {
                    event.preventDefault();
                    event.stopPropagation();
                    return false;
                }
            });
        });
    }

    // Initial attachment
    attachDateListeners();

    // Add listener for new forms being added
    const addSlotBtn = document.getElementById("add-slot-btn");
    if (addSlotBtn) {
        const originalAddSlotHandler = addSlotBtn.onclick;
        addSlotBtn.onclick = function(e) {
            if (originalAddSlotHandler) originalAddSlotHandler.call(this, e);
            // After new form is added, attach listeners to its inputs
            setTimeout(() => attachDateListeners(), 0);
        };
    }

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

    // Update the form submission handler
    document.getElementById("create-listing-form").addEventListener("submit", function(event) {
        let isValid = true;

        // Check all slots for valid end times
        document.querySelectorAll('.slot-form').forEach(formDiv => {
            if (!validateEndTime(formDiv)) {
                isValid = false;
            }
        });

        if (!isValid || !checkOverlappingSlots()) {
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
});