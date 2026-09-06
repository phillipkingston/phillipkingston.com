/* phillipkingston.com — click-to-load YouTube players for /videos/.

   Every player on the page starts as a poster frame served from this domain
   wrapped in a plain link to the video on YouTube. Nothing is requested from
   Google until the reader presses play; this file is what turns that press
   into an inline embed instead of a trip to youtube.com. With the file
   blocked, absent or still loading, the links keep working as links, which is
   why the markup is a link and not a button. */
(function () {
  "use strict";

  var EMBED = "https://www.youtube-nocookie.com/embed/";
  /* rel=0 keeps the end screen to this channel; playsinline stops iOS from
     taking the video fullscreen the moment it starts. */
  var PARAMS = "?autoplay=1&rel=0&playsinline=1";

  function play(stage, link) {
    var id = stage.getAttribute("data-video");
    if (!id) return false;

    var frame = document.createElement("iframe");
    frame.src = EMBED + encodeURIComponent(id) + PARAMS;
    frame.title = stage.getAttribute("data-title") || link.textContent.trim();
    frame.allow =
      "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    frame.referrerPolicy = "strict-origin-when-cross-origin";
    frame.allowFullscreen = true;
    frame.setAttribute("loading", "eager");

    stage.innerHTML = "";
    stage.appendChild(frame);
    stage.setAttribute("data-state", "playing");
    frame.focus();
    return true;
  }

  document.addEventListener("click", function (e) {
    var link = e.target.closest ? e.target.closest(".video__link") : null;
    if (!link) return;

    /* Leave the browser's own gestures alone: a modified or middle click means
       the reader wants the YouTube page, in a tab or a window of their own. */
    if (e.defaultPrevented || e.button !== 0) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

    var stage = link.parentNode;
    if (!stage || !stage.classList.contains("video__stage")) return;

    if (play(stage, link)) e.preventDefault();
  });
})();
