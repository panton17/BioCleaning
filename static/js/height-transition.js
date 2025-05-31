function setupHeightTransition() {
  const content = document.getElementById('content-div');
  const wrapper = document.getElementById('content-wrapper');
  
  if (!content || !wrapper) return;
  
  // Initialize
  wrapper.style.height = `${content.scrollHeight}px`;
  
  // Handle page load and resize
  window.addEventListener('load', updateHeight);
  window.addEventListener('resize', updateHeight);
  
  // MutationObserver for dynamic content
  const observer = new MutationObserver(updateHeight);
  observer.observe(content, {
    childList: true,
    subtree: true,
    characterData: true
  });
  
  function updateHeight() {
    // Set current height
    wrapper.style.height = `${content.scrollHeight}px`;
    
    // Force reflow
    void wrapper.offsetHeight;
    
    // Animate to new height
    wrapper.style.height = `${content.scrollHeight}px`;
    
    // Clean up after transition
    setTimeout(() => {
      wrapper.style.height = 'auto';
    }, 500);
  }
}

document.addEventListener('DOMContentLoaded', setupHeightTransition);