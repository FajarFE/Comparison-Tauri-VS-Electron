const electronPageLoadStartTime = performance.now();
window.addEventListener('load', () => {
  // Atau DOMContentLoaded
  const electronPageLoadEndTime = performance.now();
  console.log(
    `Electron Frontend Loaded: ${
      electronPageLoadEndTime - electronPageLoadStartTime
    } ms`,
  );
});
