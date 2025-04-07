document.addEventListener("DOMContentLoaded", function() {
  // ------------------------------
  // Function to display error as red alert bar
  // ------------------------------
  function showClientError(message) {
    var clientAlert = document.getElementById("client-alert");
    if (!clientAlert) {
      clientAlert = document.createElement("div");
      clientAlert.id = "client-alert";
      clientAlert.className = "alert alert-danger";
      clientAlert.innerHTML = '<i class="fas fa-exclamation-circle me-2"></i>' + message;
      // Insert at the top of the card body if available
      var cardBody = document.querySelector(".card-body.p-4");
      if (cardBody) {
        cardBody.insertBefore(clientAlert, cardBody.firstChild);
      } else {
        // Fallback: prepend to the form
        var editListingForm = document.getElementById("edit-listing-form");
        if (editListingForm) {
          editListingForm.prepend(clientAlert);
        }
      }
    } else {
      clientAlert.innerHTML = '<i class="fas fa-exclamation-circle me-2"></i>' + message;
    }
  }
  
  // ------------------------------
  // Add/Remove Slot Form Logic
  // ------------------------------
  var addSlotBtn = document.getElementById("add-slot-btn");
  var slotFormsContainer = document.getElementById("slot-forms-container");
  var emptyTemplate = document.getElementById("empty-slot-template").innerHTML;
  var totalFormsInput = document.querySelector('[name="form-TOTAL_FORMS"]');

  // Update form indices after adding or removing slots.
  function updateFormIndices() {
    var slotDivs = slotFormsContainer.querySelectorAll(".slot-form");
    slotDivs.forEach(function(div, idx) {
      div.setAttribute("data-index", idx);
      // Update heading text
      var heading = div.querySelector("h5");
      if (heading) {
        heading.innerHTML = '<i class="fas fa-clock text-secondary me-2"></i>Time Slot ' + (idx + 1);
      }
      // Update names and ids for inputs, selects, and labels WITHOUT resetting their values.
      var elements = div.querySelectorAll("input, select, label");
      elements.forEach(function(el) {
        if (el.name) {
          el.name = el.name.replace(/form-\d+-/, "form-" + idx + "-");
        }
        if (el.id) {
          el.id = el.id.replace(/id_form-\d+-/, "id_form-" + idx + "-");
        }
      });
    });
    totalFormsInput.value = slotDivs.length;
  }

  // Attach delete handler to a slot form
  function attachDeleteHandler(slotDiv) {
    var deleteBtn = slotDiv.querySelector(".delete-slot");
    if (deleteBtn) {
      deleteBtn.addEventListener("click", function() {
        var deleteCheckbox = slotDiv.querySelector('input[type="checkbox"][name$="-DELETE"]');
        if (deleteCheckbox) {
          deleteCheckbox.checked = true;
          slotDiv.style.display = "none";
        } else {
          slotDiv.remove();
          updateFormIndices();
        }
      });
    }
  }

  // Attach delete handler to all existing slot forms
  document.querySelectorAll(".slot-form").forEach(function(div) {
    attachDeleteHandler(div);
  });

  // Add new slot form on button click
  if (addSlotBtn) {
    addSlotBtn.addEventListener("click", function() {
      var currentCount = parseInt(totalFormsInput.value);
      var newHtml = emptyTemplate
        .replace(/__prefix__/g, currentCount)
        .replace(/__num__/g, currentCount + 1);
      var tempDiv = document.createElement("div");
      tempDiv.innerHTML = newHtml.trim();
      var newSlot = tempDiv.firstChild;
      slotFormsContainer.appendChild(newSlot);
      updateFormIndices();
      attachDeleteHandler(newSlot);
    });
  }

  // ------------------------------
  // Overlapping Slot Validation
  // ------------------------------
  function checkOverlappingSlots() {
    // Remove any existing client alert
    var existingAlert = document.getElementById("client-alert");
    if (existingAlert) {
      existingAlert.remove();
    }
    var slotDivs = document.querySelectorAll(".slot-form");
    var intervals = [];
    for (var i = 0; i < slotDivs.length; i++) {
      if (slotDivs[i].style.display === "none") continue;
      var startDate = slotDivs[i].querySelector('input[name$="start_date"]').value;
      var endDate = slotDivs[i].querySelector('input[name$="end_date"]').value;
      var startTime = slotDivs[i].querySelector('select[name$="start_time"]').value;
      var endTime = slotDivs[i].querySelector('select[name$="end_time"]').value;
      if (startDate && endDate && startTime && endTime) {
        var start = new Date(startDate + "T" + startTime);
        var end = new Date(endDate + "T" + endTime);
        if (end <= start) {
          showClientError("Each slot's start time must be before its end time.");
          return false;
        }
        for (var j = 0; j < intervals.length; j++) {
          var iv = intervals[j];
          if (!(end <= iv.start || start >= iv.end)) {
            showClientError("Availability slots cannot overlap.");
            return false;
          }
        }
        intervals.push({ start: start, end: end });
      }
    }
    return true;
  }

  var editListingForm = document.getElementById("edit-listing-form");
  if (editListingForm) {
    editListingForm.addEventListener("submit", function(e) {
      if (!checkOverlappingSlots()) {
        e.preventDefault();
      }
    });
  }

  // Initialize EV charger fields if utility is available
  if (typeof ListingFormUtils !== 'undefined') {
    ListingFormUtils.initializeEvChargerFields();
  }
});
