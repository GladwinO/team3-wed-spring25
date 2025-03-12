let map;
let marker;
let locationData = {
  address: "",
  lat: "",
  lng: ""
};

// Initialize the map when the document is ready
document.addEventListener('DOMContentLoaded', function() {
  console.log("Initializing map");
  
  // Make sure the map div exists
  const mapDiv = document.getElementById("map");
  if (!mapDiv) {
    console.error("Map container not found! Make sure a div with id 'map' exists.");
    return;
  }
  
  // Initialize the map
  map = L.map("map").setView([40.69441, -73.98653], 13); // Default to NYU tandon
  console.log("Map initialized");
  
  // Add OpenStreetMap tiles
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
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
        updateLocationField(
          location.display_name,
          location.lat,
          location.lon
        );
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