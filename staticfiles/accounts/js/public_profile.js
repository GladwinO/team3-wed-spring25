// public_profile.js - Star rating functionality for profile pages

// Helper function to generate star HTML
function generateStarRating(rating) {
  let starsHtml = "";

  if (!rating) {
    // Show 5 empty stars if no rating
    for (let i = 0; i < 5; i++) {
      starsHtml += '<i class="far fa-star text-warning"></i>';
    }
  } else {
    // Full stars
    for (let i = 0; i < Math.floor(rating); i++) {
      starsHtml += '<i class="fas fa-star text-warning"></i>';
    }
    // Half star
    if (rating % 1 >= 0.5) {
      starsHtml += '<i class="fas fa-star-half-alt text-warning"></i>';
    }
    // Empty stars
    for (let i = Math.ceil(rating); i < 5; i++) {
      starsHtml += '<i class="far fa-star text-warning"></i>';
    }
  }

  return starsHtml;
}

// Apply ratings to all elements with rating-stars class
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.rating-stars').forEach(function(element) {
    const rating = parseFloat(element.getAttribute('data-rating')) || 0;
    element.innerHTML = generateStarRating(rating);
  });
});