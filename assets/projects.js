const previews = document.querySelectorAll(".project-preview");
let playing;

for (const preview of previews) {
  preview.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;

    const video = document.createElement("video");
    if (!video.canPlayType("video/mp4")) return;

    event.preventDefault();
    video.controls = true;
    video.playsInline = true;
    video.poster = preview.querySelector("img").src;
    video.setAttribute("aria-label", preview.getAttribute("aria-label"));
    video.addEventListener("play", () => {
      if (playing !== video) playing?.pause();
      playing = video;
    });
    video.addEventListener("error", () => {
      const hadFocus = document.activeElement === video;
      video.remove();
      preview.hidden = false;
      if (hadFocus) preview.focus();
    }, { once: true });

    preview.after(video);
    preview.hidden = true;
    video.src = preview.href;
    video.focus({ preventScroll: true });
    video.play().catch(() => {
      // Native controls remain available if the browser blocks play().
    });
  });
}
