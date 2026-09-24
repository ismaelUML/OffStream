/**
 * YT Global DL - Content Script
 * Injects one-click download controls directly into YouTube watch and shorts pages.
 */

const DAEMON_URL = "http://127.0.0.1:8765";

console.log("%c[YT Global DL] Extension loaded and monitoring YouTube pages", "color: #a78bfa; font-weight: bold;");

function isWatchPage() {
  return window.location.pathname === "/watch" || window.location.pathname.startsWith("/shorts");
}

function initButtonInjection() {
  if (!isWatchPage()) {
    return;
  }

  const existing = document.getElementById("yt-gdl-btn-container");
  if (existing && document.body.contains(existing)) {
    return;
  }

  // Target multiple modern YouTube insertion points (subscribe button is most reliable)
  const subscribeBtn =
    document.querySelector("#owner #subscribe-button") ||
    document.querySelector("#subscribe-button") ||
    document.querySelector("ytd-subscribe-button-renderer");

  const ownerContainer = document.querySelector("#owner") || document.querySelector("ytd-video-owner-renderer");

  const targetBar =
    document.querySelector("#top-level-buttons-computed") ||
    document.querySelector("#actions-inner #menu") ||
    document.querySelector(".ytd-watch-metadata #actions") ||
    document.querySelector("#actions.ytd-watch-metadata");

  if (!subscribeBtn && !ownerContainer && !targetBar) {
    return;
  }

  const container = document.createElement("div");
  container.id = "yt-gdl-btn-container";
  container.className = "yt-gdl-btn-container";

  container.innerHTML = `
    <button class="yt-gdl-main-btn" id="yt-gdl-trigger">
      <svg viewBox="0 0 24 24"><path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z"/></svg>
      <span>Download</span>
    </button>
    <div class="yt-gdl-dropdown" id="yt-gdl-menu">
      <div class="yt-gdl-item" data-kind="video" data-quality="best">
        <span>🎬</span>
        <div>
          <div>Video (Best / 1080p+)</div>
          <div class="yt-gdl-item-desc">Lossless muxed MP4</div>
        </div>
      </div>
      <div class="yt-gdl-item" data-kind="audio" data-quality="audio_high">
        <span>🎧</span>
        <div>
          <div>Audio (Clean MP3)</div>
          <div class="yt-gdl-item-desc">High bitrate 192k</div>
        </div>
      </div>
      <div class="yt-gdl-item" data-kind="video" data-quality="720p">
        <span>⚡</span>
        <div>
          <div>Fast Video (720p)</div>
          <div class="yt-gdl-item-desc">Quick single-stream</div>
        </div>
      </div>
    </div>
  `;

  // Insert next to subscribe button or owner
  if (subscribeBtn && subscribeBtn.parentElement) {
    subscribeBtn.parentElement.insertBefore(container, subscribeBtn.nextSibling);
    console.log("[YT Global DL] Download button injected next to Subscribe button!");
  } else if (ownerContainer) {
    ownerContainer.appendChild(container);
    console.log("[YT Global DL] Download button injected inside Owner container!");
  } else if (targetBar) {
    targetBar.appendChild(container);
    console.log("[YT Global DL] Download button injected inside Actions bar!");
  }

  const trigger = container.querySelector("#yt-gdl-trigger");
  const menu = container.querySelector("#yt-gdl-menu");

  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    menu.classList.toggle("show");
  });

  document.addEventListener("click", () => {
    menu.classList.remove("show");
  });

  container.querySelectorAll(".yt-gdl-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.remove("show");
      const kind = item.getAttribute("data-kind");
      const quality = item.getAttribute("data-quality");
      triggerDownload(window.location.href, kind, quality);
    });
  });
}

async function triggerDownload(url, kind, quality) {
  showToast("Queueing download with local daemon...", 0);

  try {
    const res = await fetch(`${DAEMON_URL}/api/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, kind, quality }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Server error");
    }

    const job = await res.json();
    pollJobProgress(job.job_id);
  } catch (err) {
    showToast(`Daemon Offline: Start server first\n(${err.message})`, 0, true);
  }
}

function pollJobProgress(jobId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`${DAEMON_URL}/api/jobs/${jobId}`);
      if (!res.ok) return;

      const job = await res.json();
      const pct = job.progress_percentage || 0;

      if (job.status === "completed") {
        clearInterval(interval);
        showToast("✓ Download Complete!\nSaved to Downloads/yt-global-dl", 100);
      } else if (job.status === "failed") {
        clearInterval(interval);
        showToast(`✗ Failed: ${job.error_message}`, 0, true);
      } else {
        showToast(`[${job.status.toUpperCase()}] ${pct.toFixed(0)}%`, pct);
      }
    } catch {
      clearInterval(interval);
    }
  }, 500);
}

let activeToastTimeout = null;

function showToast(message, progressPct = 0, isError = false) {
  let toast = document.getElementById("yt-gdl-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "yt-gdl-toast";
    toast.className = "yt-gdl-toast";
    document.body.appendChild(toast);
  }

  toast.innerHTML = `
    <div class="yt-gdl-toast-header">
      <span>YT Global DL</span>
      <span class="yt-gdl-toast-status" style="color: ${isError ? "#ef4444" : "#a78bfa"}">
        ${isError ? "Error" : progressPct === 100 ? "Ready" : "Processing"}
      </span>
    </div>
    <div style="font-size: 12px; color: #d4d4d8; white-space: pre-line;">${message}</div>
    ${
      !isError && progressPct < 100
        ? `<div class="yt-gdl-progress-bar"><div class="yt-gdl-progress-fill" style="width: ${progressPct}%"></div></div>`
        : ""
    }
  `;

  if (activeToastTimeout) clearTimeout(activeToastTimeout);

  if (progressPct === 100 || isError) {
    activeToastTimeout = setTimeout(() => {
      if (toast) toast.remove();
    }, 4500);
  }
}

// Watch for YouTube SPA navigation changes
const observer = new MutationObserver(() => initButtonInjection());
observer.observe(document.body, { childList: true, subtree: true });

window.addEventListener("yt-navigate-finish", initButtonInjection);
window.addEventListener("yt-page-data-updated", initButtonInjection);
window.addEventListener("spfdone", initButtonInjection);

// Regular periodic heartbeat to re-check injection
setInterval(() => {
  if (isWatchPage()) {
    initButtonInjection();
  }
}, 1000);

initButtonInjection();
