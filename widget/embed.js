(function() {
  const currentScript = document.currentScript;
  const WIDGET_URL = currentScript?.dataset.supportCopilotUrl || window.SUPPORT_COPILOT_URL || 'http://localhost:3000';
  const BUBBLE_SIZE = 56;

  // Inject bubble styles
  const style = document.createElement('style');
  style.textContent = `
    #sc-bubble { position:fixed; bottom:24px; right:24px; width:${BUBBLE_SIZE}px; height:${BUBBLE_SIZE}px;
      background:#4f46e5; border-radius:50%; cursor:pointer; display:flex; align-items:center;
      justify-content:center; box-shadow:0 4px 20px rgba(79,70,229,0.4); z-index:99999;
      transition:transform 0.2s; }
    #sc-bubble:hover { transform:scale(1.1); }
    #sc-bubble svg { color:white; width:24px; height:24px; }
    #sc-iframe-container { position:fixed; bottom:96px; right:24px; width:380px; height:600px;
      border-radius:16px; overflow:hidden; box-shadow:0 20px 60px rgba(0,0,0,0.15);
      z-index:99998; display:none; }
    #sc-iframe-container.open { display:block; }
    #sc-iframe { width:100%; height:100%; border:none; }
    @media(max-width:480px) { #sc-iframe-container { width:calc(100vw - 16px); right:8px; bottom:80px; } }
  `;
  document.head.appendChild(style);

  // Chat bubble button
  const bubble = document.createElement('div');
  bubble.id = 'sc-bubble';
  bubble.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
    <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
  </svg>`;

  // iframe container
  const container = document.createElement('div');
  container.id = 'sc-iframe-container';
  const iframe = document.createElement('iframe');
  iframe.id = 'sc-iframe';
  iframe.src = WIDGET_URL + '/chat';
  iframe.allow = 'microphone';
  container.appendChild(iframe);

  document.body.appendChild(bubble);
  document.body.appendChild(container);

  bubble.addEventListener('click', () => {
    container.classList.toggle('open');
    // Pass host token to iframe if stored
    const token = localStorage.getItem('access_token');
    if (token) {
      iframe.contentWindow.postMessage({ type: 'set_token', token }, WIDGET_URL);
    }
  });
})();
