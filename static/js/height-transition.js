document.addEventListener('DOMContentLoaded', function() {
  const contentDiv = document.querySelector('.content-div');
  const wrapper = document.querySelector('.content-wrapper');
  
  function updateHeight() {
    // Set explicit height before measurement
    wrapper.style.height = `${contentDiv.scrollHeight}px`;
    
    // Force reflow
    void wrapper.offsetHeight;
    
    // Set to auto after transition
    setTimeout(() => {
      wrapper.style.height = 'auto';
    }, 500);
  }
  
  // Initialize height
  updateHeight();
  
  // Set up MutationObserver for dynamic content
  const observer = new MutationObserver(function(mutations) {
    updateHeight();
  });
  
  observer.observe(contentDiv, {
    childList: true,
    subtree: true,
    characterData: true
  });
  
  // For AJAX content changes (if you use them)
  document.addEventListener('ajaxComplete', updateHeight);
});