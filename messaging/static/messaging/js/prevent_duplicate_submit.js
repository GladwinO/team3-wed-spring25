document.addEventListener('DOMContentLoaded', function() {
  // Get the form and send button
  const messageForm = document.querySelector('form');
  const sendButton = document.querySelector('button[type="submit"]');
  
  if (messageForm && sendButton) {
    // Track if form has been submitted
    let isSubmitted = false;
    
    messageForm.addEventListener('submit', function(e) {
      // Prevent multiple submissions
      if (isSubmitted) {
        e.preventDefault();
        return false;
      }
      
      // Mark as submitted and disable button
      isSubmitted = true;
      sendButton.disabled = true;
      sendButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Sending...';
      
      // Allow the form to submit
      return true;
    });
  }
});