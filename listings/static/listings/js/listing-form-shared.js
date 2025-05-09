(function(global) {
  const ListingFormUtils = {
    initializeEvChargerFields: function () {
        const hasEvChargerCheckbox = document.querySelector('[name="has_ev_charger"]');
        if (!hasEvChargerCheckbox) {
            console.log('EV charger checkbox not found - skipping initialization');
            return;
        }

        const chargerLevelContainer = document.querySelector('.charger-level-container');
        const connectorTypeContainer = document.querySelector('.connector-type-container');
        const chargerLevelField = document.querySelector('[name="charger_level"]');
        const connectorTypeField = document.querySelector('[name="connector_type"]');

        function toggleEvFields() {
            const isChecked = hasEvChargerCheckbox.checked;
            console.log('EV Charger Checkbox Checked:', isChecked);

            if (chargerLevelContainer) {
                console.log('Charger Level Container Found:', chargerLevelContainer);
                chargerLevelContainer.style.display = isChecked ? 'block' : 'none';
            }

            if (connectorTypeContainer) {
                console.log('Connector Type Container Found:', connectorTypeContainer);
                connectorTypeContainer.style.display = isChecked ? 'block' : 'none';
            }

            if (chargerLevelField) {
                console.log('Charger Level Field Found:', chargerLevelField);
                chargerLevelField.disabled = !isChecked;
                if (isChecked) {
                    chargerLevelField.style.opacity = '1';
                    chargerLevelField.style.pointerEvents = 'auto';
                } else {
                    chargerLevelField.style.opacity = '0.6';
                    chargerLevelField.style.pointerEvents = 'none';
                    chargerLevelField.value = '';
                }
            }

            if (connectorTypeField) {
                console.log('Connector Type Field Found:', connectorTypeField);
                connectorTypeField.disabled = !isChecked;
                if (isChecked) {
                    connectorTypeField.style.opacity = '1';
                    connectorTypeField.style.pointerEvents = 'auto';
                } else {
                    connectorTypeField.style.opacity = '0.6';
                    connectorTypeField.style.pointerEvents = 'none';
                    connectorTypeField.value = '';
                }
            }
        }

        // Run on page load
        toggleEvFields();

        // Run when checkbox changes
        hasEvChargerCheckbox.addEventListener('change', () => {
            console.log('EV Charger Checkbox Changed');
            toggleEvFields();
        });
    }
  };

  // Expose the utilities to the global scope
  global.ListingFormUtils = ListingFormUtils;
})(window);