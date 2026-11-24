const timer = document.querySelector("[data-rest-until]");

if (timer) {
  const end = Number(timer.dataset.restUntil);
  const clock = document.querySelector("#rest-time");
  const label = document.querySelector("#rest-label");

  function updateTimer() {
    const remaining = Math.max(0, Math.ceil((end - Date.now()) / 1000));
    const minutes = Math.floor(remaining / 60);
    const seconds = String(remaining % 60).padStart(2, "0");
    clock.textContent = minutes + ":" + seconds;
    if (remaining === 0) {
      label.textContent = "Rest complete";
    }
    return remaining;
  }

  if (updateTimer() > 0) {
    const interval = setInterval(() => {
      if (updateTimer() === 0) {
        clearInterval(interval);
      }
    }, 250);
  }
}
