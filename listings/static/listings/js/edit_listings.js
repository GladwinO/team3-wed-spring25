document.addEventListener("DOMContentLoaded", function() {
  // ============================
  // Add/Remove Slot Form Logic
  // ============================
  var addSlotBtn = document.getElementById("add-slot-btn");
  var slotFormsContainer = document.getElementById("slot-forms-container");
  var emptyTemplate = document.getElementById("empty-slot-template").innerHTML;
  var totalFormsInput = document.querySelector('[name="form-TOTAL_FORMS"]');

  // Update form indices after adding or removing slots.
  // (Modified: Do NOT reset the select's value so that the server-rendered initial remains.)
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
        // DO NOT reset el.value here!
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

  // ============================
  // Overlapping Slot Validation
  // ============================
  function checkOverlappingSlots() {
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
          alert("Each slot's start time must be before its end time.");
          return false;
        }
        for (var j = 0; j < intervals.length; j++) {
          var iv = intervals[j];
          if (!(end <= iv.start || start >= iv.end)) {
            alert("Availability slots cannot overlap.");
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

  // ============================
  // Warning Modal Logic
  // ============================
  var warningModal = document.getElementById("warning-modal");
  var warningMessageElem = document.getElementById("warning-modal-message");
  var warningClose = document.querySelector(".warning-modal-close");

  function showWarning(message) {
    if (warningMessageElem && warningModal) {
      warningMessageElem.textContent = message;
      warningModal.style.display = "block";
    }
  }

  if (warningClose) {
    warningClose.addEventListener("click", function() {
      warningModal.style.display = "none";
    });
  }

  // If a block warning message was passed from the server, show it.
  if (typeof blockWarningMessage !== "undefined" && blockWarningMessage.trim().length > 0) {
    showWarning(blockWarningMessage.trim());
  }
});
