const timer = document.querySelector("[data-rest-seconds]");
const end = Date.now() + Number(timer.dataset.restSeconds) * 1000;

function showTime() {
  const remaining = Math.max(0, Math.ceil((end - Date.now()) / 1000));
  const minutes = Math.floor(remaining / 60);
  const seconds = String(remaining % 60).padStart(2, "0");
  document.querySelector("#rest-time").textContent = minutes + ":" + seconds;
  if (remaining === 0) {
    timer.hidden = true;
  }
}

if (!timer.hidden) {
  showTime();
  const interval = setInterval(() => {
    showTime();
    if (timer.hidden) {
      clearInterval(interval);
    }
  }, 250);
}
