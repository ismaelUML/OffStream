/**
 * YT Global DL - Content Script
 * Injects one-click download controls directly into YouTube watch and shorts pages.
 */

const DAEMON_URL = "http://127.0.0.1:8765";

console.log("%c[YT Global DL] Extension script initialized.", "color: #a78bfa; font-size: 14px; font-weight: bold;");

function isWatchPage() {
  return window.location.pathname === "/watch" || window.location.pathname.startsWith("/shorts");
}

function initButtonInjection() {
  if (!isWatchPage()) {
    return;
  }

  // Also try injecting player control button
  initPlayerButtonInjection();

  const existing = document.getElementById("yt-gdl-btn-container");
  if (existing && document.body.contains(existing)) {
    return;
  }

  const actions =
    document.querySelector("#actions.ytd-watch-metadata") ||
    document.querySelector("#actions") ||
    document.querySelector("#actions-inner");

  const topRow =
    document.querySelector("#top-row.ytd-watch-metadata") ||
    document.querySelector("#top-row");

  const owner =
    document.querySelector("#owner.ytd-watch-metadata") ||
    document.querySelector("#owner");

  if (!actions && !topRow && !owner) {
    return;
  }

  const container = document.createElement("div");
  container.id = "yt-gdl-btn-container";
  container.className = "yt-gdl-btn-container";

  container.innerHTML = `
    <button class="yt-gdl-main-btn" id="yt-gdl-trigger" title="Download this video or audio">
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

  // Guaranteed placement: Insert right BEFORE #actions (in the big open gap)
  if (actions && actions.parentElement) {
    actions.parentElement.insertBefore(container, actions);
    console.log("[YT Global DL] Success: Download button injected before #actions!");
  } else if (topRow) {
    topRow.appendChild(container);
    console.log("[YT Global DL] Success: Injected inside #top-row!");
  } else if (owner && owner.parentElement) {
    owner.parentElement.insertBefore(container, owner.nextSibling);
    console.log("[YT Global DL] Success: Injected after #owner!");
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

function initPlayerButtonInjection() {
  const rightControls = document.querySelector(".ytp-right-controls");
  if (!rightControls || document.getElementById("yt-gdl-player-btn")) {
    return;
  }

  const playerBtn = document.createElement("button");
  playerBtn.id = "yt-gdl-player-btn";
  playerBtn.className = "ytp-button yt-gdl-player-btn";
  playerBtn.title = "Download Video/Audio (YT Global DL)";
  playerBtn.innerHTML = `
    <svg viewBox="0 0 24 24" style="width: 22px; height: 22px; fill: white; vertical-align: middle; margin-top: 8px;">
      <path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z"/>
    </svg>
  `;

  playerBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const trigger = document.getElementById("yt-gdl-trigger");
    if (trigger) {
      trigger.click();
      trigger.scrollIntoView({ behavior: "smooth", block: "center" });
    } else {
      triggerDownload(window.location.href, "audio", "audio_high");
    }
  });

  rightControls.prepend(playerBtn);
  console.log("[YT Global DL] Success: Player controls button injected.");
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
  }, 400);
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
const observer = new MutationObserver(() => {
  if (isWatchPage()) {
    initButtonInjection();
  }
});
observer.observe(document.body, { childList: true, subtree: true });

window.addEventListener("yt-navigate-finish", initButtonInjection);
window.addEventListener("yt-page-data-updated", initButtonInjection);
window.addEventListener("spfdone", initButtonInjection);

// Regular periodic heartbeat to re-check injection
setInterval(() => {
  if (isWatchPage()) {
    initButtonInjection();
  }
}, 800);

initButtonInjection();
