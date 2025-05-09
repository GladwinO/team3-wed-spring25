document.addEventListener('DOMContentLoaded', function() {
  // Bookmark click handler
  document.addEventListener('click', function(event) {
    const bookmarkIcon = event.target.closest('.bookmark-icon');
    if (bookmarkIcon) {
      event.preventDefault();
      
      const url = bookmarkIcon.getAttribute('href');
      const listingId = bookmarkIcon.getAttribute('data-listing-id');
      const isCurrentlyActive = bookmarkIcon.classList.contains('active');
      
      // Toggle active class
      bookmarkIcon.classList.toggle('active');
      
      // Toggle icon class
      const iconElement = bookmarkIcon.querySelector('i');
      if (iconElement) {
        if (iconElement.classList.contains('far')) {
          iconElement.classList.replace('far', 'fas');
        } else {
          iconElement.classList.replace('fas', 'far');
        }
      }
      
      // Find all other bookmark icons for this same listing and update them too
      document.querySelectorAll(`.bookmark-icon[data-listing-id="${listingId}"]`).forEach(otherIcon => {
        if (otherIcon !== bookmarkIcon) {
          otherIcon.classList.toggle('active');
          
          const otherIconElement = otherIcon.querySelector('i');
          if (otherIconElement) {
            if (otherIconElement.classList.contains('far')) {
              otherIconElement.classList.replace('far', 'fas');
            } else {
              otherIconElement.classList.replace('fas', 'far');
            }
          }
        }
      });
      
      // NEW CODE: Check if we're on bookmarks page and removing a bookmark
      const isBookmarksPage = window.location.pathname.includes('/bookmarks/');
      if (isBookmarksPage && isCurrentlyActive) {
        // Find the card containing this bookmark icon
        const card = bookmarkIcon.closest('.card');
        if (card) {
          // Add fade-out animation
          card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
          card.style.opacity = '0';
          card.style.transform = 'scale(0.95)';
          
          // Remove the card after animation completes
          setTimeout(() => {
            card.remove();
            
            // Check if any cards are left
            if (document.querySelectorAll('.listings-container .card').length === 0) {
              // Show empty state message
              const container = document.querySelector('.listings-container');
              container.innerHTML = `
                <div class="alert alert-info text-center py-4">
                  <i class="fas fa-bookmark fa-2x mb-3 text-secondary"></i>
                  <h4>You haven't bookmarked any listings yet</h4>
                  <p class="mb-3">When you find spots you're interested in, bookmark them to view later!</p>
                  <a href="/listings/view_listings/" class="btn btn-primary">Browse Listings</a>
                </div>
              `;
            }
          }, 500); // Wait 500ms for animation to complete
        }
      }
      
      // Make AJAX request
      fetch(url, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          console.error(data.error);
          // Revert UI changes on error
        }
      })
      .catch(error => {
        console.error('Error:', error);
        // Revert UI changes on error
      });
    }
  });
  
  // SEPARATE Load More function
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', loadMoreListings);
  }

  function loadMoreListings() {
    const btn = this;
    const nextPage = btn.getAttribute('data-next-page');
    
    // Show loading state
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
    btn.disabled = true;
    
    // Fetch next page - Make sure bookmarks only runs on bookmarks page
    const currentPath = window.location.pathname;
    if (currentPath.includes('/bookmarks/')) {
      fetch(`/listings/bookmarks/?page=${nextPage}&ajax=1`)
        .then(response => response.json())
        .then(data => {
          if (data.html) {
            // Add new content
            const container = document.getElementById('listingsContainer');
            if (container) {
              const tempDiv = document.createElement('div');
              tempDiv.innerHTML = data.html;
              
              // Append all cards
              tempDiv.querySelectorAll('.card').forEach(card => {
                container.appendChild(card);
              });
              
              // Update button or remove if no more pages
              if (data.has_next) {
                btn.innerHTML = '<i class="fas fa-plus-circle me-1"></i>Load More Bookmarks';
                btn.disabled = false;
                btn.setAttribute('data-next-page', data.next_page);
              } else if (btn.parentNode) {
                btn.parentNode.removeChild(btn);
              }
            }
          }
        })
        .catch(error => {
          console.error('Error loading bookmarks:', error);
          btn.innerHTML = 'Try Again';
          btn.disabled = false;
        });
    }
  }
});