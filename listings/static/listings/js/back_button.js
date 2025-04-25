document.addEventListener('DOMContentLoaded', function() {
  const backButton = document.getElementById('back-button');
  let buttonClicked = false;
  
  if (backButton) {
    backButton.addEventListener('click', function() {
      if (buttonClicked) return;
      buttonClicked = true;
      backButton.classList.add('disabled');
      
      // Check if there's a previous page in history
      if (document.referrer && document.referrer.includes(window.location.hostname)) {
        // Go back to previous page if it exists and is from our site
        window.history.back();
      } else {
        // Use fallback URL if provided
        const fallbackUrl = backButton.getAttribute('data-fallback');
        if (fallbackUrl) {
          window.location.href = fallbackUrl;
        }
      }
      
      setTimeout(() => {
        buttonClicked = false;
        backButton.classList.remove('disabled');
      }, 1000);
    });
  }
});