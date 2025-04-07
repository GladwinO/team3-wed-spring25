(function(global) {
  const ListingFormUtils = {
    // EV Charger Fields Management
    initializeEvChargerFields: function() {
      const hasEvChargerCheckbox = document.querySelector('[name="has_ev_charger"]');
      if (!hasEvChargerCheckbox) {
        console.log('EV charger checkbox not found - skipping initialization');
        return;
      }
      
      // Find the parent containers that we'll show/hide
      const chargerLevelContainer = document.querySelector('.charger-level-container');
      const connectorTypeContainer = document.querySelector('.connector-type-container');
      
      function toggleEvFields() {
        const isChecked = hasEvChargerCheckbox.checked;
        
        // Show/hide the container divs
        if (chargerLevelContainer) {
          chargerLevelContainer.style.display = isChecked ? 'block' : 'none';
        }
        
        if (connectorTypeContainer) {
          connectorTypeContainer.style.display = isChecked ? 'block' : 'none';
        }
        
        // Also handle the field enabling/disabling for form submission
        const chargerLevelField = document.querySelector('[name="charger_level"]');
        const connectorTypeField = document.querySelector('[name="connector_type"]');
        
        if (chargerLevelField) {
          if (!isChecked) {
            chargerLevelField.value = '';
          }
          chargerLevelField.disabled = !isChecked;
        }
        
        if (connectorTypeField) {
          if (!isChecked) {
            connectorTypeField.value = '';
          }
          connectorTypeField.disabled = !isChecked;
        }
      }
      
      // Run on page load
      toggleEvFields();
      
      // Run when checkbox changes
      hasEvChargerCheckbox.addEventListener('change', toggleEvFields);
      
      // Check form submission for required fields
      const form = document.querySelector(hasEvChargerCheckbox.closest('form'));
      if (form) {
        form.addEventListener('submit', function(e) {
          if (hasEvChargerCheckbox.checked) {
            const chargerLevelField = document.querySelector('[name="charger_level"]');
            const connectorTypeField = document.querySelector('[name="connector_type"]');
            
            let isValid = true;
            
            if (chargerLevelField && !chargerLevelField.value) {
              // Show error
              const errorMsg = document.createElement('div');
              errorMsg.className = 'invalid-feedback d-block';
              errorMsg.textContent = 'Please select a charger level';
              chargerLevelField.classList.add('is-invalid');
              
              // Remove existing error messages before adding new one
              const existingError = chargerLevelField.parentNode.querySelector('.invalid-feedback');
              if (existingError) existingError.remove();
              
              chargerLevelField.parentNode.appendChild(errorMsg);
              isValid = false;
            }
            
            if (connectorTypeField && !connectorTypeField.value) {
              // Show error
              const errorMsg = document.createElement('div');
              errorMsg.className = 'invalid-feedback d-block';
              errorMsg.textContent = 'Please select a connector type';
              connectorTypeField.classList.add('is-invalid');
              
              // Remove existing error messages before adding new one
              const existingError = connectorTypeField.parentNode.querySelector('.invalid-feedback');
              if (existingError) existingError.remove();
              
              connectorTypeField.parentNode.appendChild(errorMsg);
              isValid = false;
            }
            
            if (!isValid) {
              e.preventDefault();
              e.stopPropagation();
            }
          }
        });
      }
      
      console.log('EV charger field controls initialized');
    }
  };

  // Expose the utilities to the global scope
  global.ListingFormUtils = ListingFormUtils;
})(window);