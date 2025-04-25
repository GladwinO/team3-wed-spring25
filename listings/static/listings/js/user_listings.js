document.addEventListener('DOMContentLoaded', function() {
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', function() {
      // Show loading indicator
      const spinner = loadMoreBtn.querySelector('.fa-spinner');
      spinner.classList.add('spin');
      loadMoreBtn.disabled = true;
      
      const page = parseInt(loadMoreBtn.dataset.page);
      const username = document.getElementById('listingsContainer').dataset.username;
      
      // Make AJAX request to get more listings
      fetch(`/listings/api/user-listings/${username}/?page=${page}`, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json'
        }
      })
      .then(response => response.json())
      .then(data => {
        // Insert new listings
        const listingsContainer = document.getElementById('listingsContainer');
        listingsContainer.insertAdjacentHTML('beforeend', data.html);
        
        // Update page number
        loadMoreBtn.dataset.page = page + 1;
        
        // Hide button if no more listings
        if (!data.has_more) {
          loadMoreBtn.style.display = 'none';
        }
        
        // Reset button state
        spinner.classList.remove('spin');
        loadMoreBtn.disabled = false;
      })
      .catch(error => {
        console.error('Error loading more listings:', error);
        spinner.classList.remove('spin');
        loadMoreBtn.disabled = false;
      });
    });
  }
});