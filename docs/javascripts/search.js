document.addEventListener("DOMContentLoaded", () => {
  const trigger = document.querySelector('[data-bs-target="#mkdocs_search_modal"]');
  const modal = document.getElementById("mkdocs_search_modal");
  if (!trigger || !modal) return;

  const platform = navigator.userAgentData?.platform || navigator.platform;
  trigger.querySelector("kbd").textContent = /Mac|iPhone|iPad/.test(platform) ? "Cmd K" : "Ctrl K";

  document.addEventListener("keydown", event => {
    if (event.isComposing || event.altKey || event.shiftKey ||
        !(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "k") return;
    event.preventDefault();
    if (event.repeat) return;
    if (modal.classList.contains("show")) {
      document.getElementById("mkdocs-search-query").focus();
    } else {
      trigger.click();
    }
  });
});
