document.addEventListener('DOMContentLoaded', function() {
  // Mark all original cards
  document.querySelectorAll('.card').forEach(card => {
    card.setAttribute('data-debug', 'original');
  });
  
  // Override appendChild method for the container to prevent duplicates
  const container = document.getElementById('listingsContainer');
  if (container) {
    const originalAppendChild = container.appendChild;
    container.appendChild = function(newNode) {
      console.log('Append attempt:', newNode);
      
      // If it's a card, check if it's a duplicate by listing ID
      if (newNode.classList && newNode.classList.contains('card')) {
        const listingId = newNode.getAttribute('data-listing-id');
        
        // Check if this ID already exists
        if (listingId && document.getElementById(`card-${listingId}`)) {
          console.warn('PREVENTED DUPLICATE APPEND for listing ID:', listingId);
          return null; // Don't append duplicate
        }
        
        // Mark as dynamically added
        newNode.setAttribute('data-debug', 'dynamically-added');
      }
      
      return originalAppendChild.call(this, newNode);
    };
  }
  
  // Add duplicate detection when bookmark is clicked
  document.addEventListener('click', function(event) {
    if (event.target.closest('.bookmark-icon')) {
      console.log('Bookmark clicked');
      
      // Check for duplicates after a short delay
      setTimeout(() => {
        // Get all listing IDs
        const cardIds = {};
        const duplicates = [];
        
        document.querySelectorAll('.card[data-listing-id]').forEach(card => {
          const id = card.getAttribute('data-listing-id');
          if (cardIds[id]) {
            duplicates.push(id);
          } else {
            cardIds[id] = true;
          }
        });
        
        if (duplicates.length) {
          console.error('DUPLICATES FOUND:', duplicates);
        } else {
          console.log('No duplicates found');
        }
      }, 500);
    }
  });
});