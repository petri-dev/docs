(() => {
  function disposeScrollSpy() {
    bootstrap.ScrollSpy.getInstance(document.body)?.dispose();
  }
  disposeScrollSpy();
  document.addEventListener("DOMContentLoaded", disposeScrollSpy);

  const sidebar = document.querySelector(".bs-sidebar");
  if (!sidebar) return;

  const sections = Array.from(sidebar.querySelectorAll('a[href^="#"]'), link => ({
    link,
    heading: document.getElementById(decodeURIComponent(link.hash.slice(1))),
  })).filter(section => section.heading);
  if (!sections.length) return;

  const header = document.querySelector("body > .navbar");
  let active = null;
  let scheduled = false;

  function update() {
    scheduled = false;
    const anchorOffset = parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0;
    const boundary = Math.max((header?.getBoundingClientRect().bottom || 0) + 16, anchorOffset) + 1;
    let current = sections[0];
    for (const section of sections) {
      if (section.heading.getBoundingClientRect().top > boundary) break;
      current = section;
    }
    if (window.scrollY > 0 && window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2) {
      current = sections[sections.length - 1];
    }
    if (current === active) return;
    active = current;
    for (const { link } of sections) {
      link.classList.toggle("active", link === current.link);
      if (link === current.link) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(update);
  }

  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", schedule);
  window.addEventListener("hashchange", schedule);
  window.addEventListener("load", schedule);
  new ResizeObserver(schedule).observe(document.querySelector("main"));
  schedule();
})();

