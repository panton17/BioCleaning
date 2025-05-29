document.addEventListener('DOMContentLoaded', function() {
  const contentDiv = document.querySelector('.content-div');
  const wrapper = document.querySelector('.content-wrapper');

  function setupHeightTransition() {
    // Set initial height
    wrapper.style.height = `${contentDiv.scrollHeight}px`;

    // MutationObserver to watch for content changes
    const observer = new MutationObserver(function(mutations) {
      wrapper.style.height = `${contentDiv.scrollHeight}px`;
      setTimeout(() => {
        wrapper.style.height = 'auto';
      }, 500);
    });

    // Observe content changes
    observer.observe(contentDiv, {
      childList: true,
      subtree: true,
      characterData: true
    });
  }

  setupHeightTransition();
});