document.addEventListener('DOMContentLoaded', function() {
  // Get all forms that should be protected
  const forms = document.querySelectorAll('form');
  
  forms.forEach(form => {
    // Track if form has been submitted
    let isSubmitted = false;
    
    form.addEventListener('submit', function(e) {
      // Find submit button in this form
      const submitButton = form.querySelector('button[type="submit"]');
      if (!submitButton) return true; // No submit button found
      
      // Prevent multiple submissions
      if (isSubmitted) {
        e.preventDefault();
        return false;
      }
      
      // Mark as submitted and disable button
      isSubmitted = true;
      submitButton.disabled = true;
      
      // Store original button content
      const originalContent = submitButton.innerHTML;
      
      // Replace with spinner and "Processing..." text
      submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing...';
      
      // If form submission fails or gets stuck, re-enable after 30 seconds as fallback
      setTimeout(function() {
        if (isSubmitted) {
          submitButton.disabled = false;
          submitButton.innerHTML = originalContent;
          isSubmitted = false;
        }
      }, 30000);
      
      // Allow the form to submit
      return true;
    });
  });
});