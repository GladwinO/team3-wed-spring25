document.addEventListener('DOMContentLoaded', function() {
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', loadMoreListings);
  }

  function loadMoreListings() {
    const btn = this;
    const nextPage = btn.getAttribute('data-next-page');
    const username = document.getElementById('listingsContainer').getAttribute('data-username');
    
    // Show loading state
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
    btn.disabled = true;
    
    // Fetch next page
    fetch(`/listings/user/${username}/listings/?page=${nextPage}&ajax=1`)
      .then(response => response.json())
      .then(data => {
        if (data.html) {
          // Add new content
          const container = document.getElementById('listingsContainer');
          const tempDiv = document.createElement('div');
          tempDiv.innerHTML = data.html;
          
          // Append all cards
          tempDiv.querySelectorAll('.card').forEach(card => {
            container.appendChild(card);
          });
          
          // Update button or remove if no more pages
          if (data.has_next) {
            btn.innerHTML = '<i class="fas fa-plus-circle me-1"></i>Load More Listings';
            btn.disabled = false;
            btn.setAttribute('data-next-page', data.next_page);
          } else {
            btn.parentNode.removeChild(btn);
          }
        }
      })
      .catch(error => {
        console.error('Error loading listings:', error);
        btn.innerHTML = 'Try Again';
        btn.disabled = false;
      });
  }
});