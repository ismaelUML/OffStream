const API_BASE = "http://127.0.0.1:8765";

const statusPill = document.getElementById("status-pill");
const statusText = document.getElementById("status-text");
const urlInput = document.getElementById("url-input");
const btnPaste = document.getElementById("btn-paste");
const btnDownloadVideo = document.getElementById("btn-download-video");
const btnDownloadAudio = document.getElementById("btn-download-audio");
const qualitySelect = document.getElementById("quality-select");
const btnClear = document.getElementById("btn-clear");
const btnRefresh = document.getElementById("btn-refresh");
const jobsList = document.getElementById("jobs-list");

let eventSource = null;
let currentJobs = [];

// Autodetectar URL si el usuario ya está viendo un video en la pestaña activa
if (typeof chrome !== "undefined" && chrome.tabs && chrome.tabs.query) {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs[0] && tabs[0].url) {
      const tabUrl = tabs[0].url;
      if (tabUrl.includes("youtube.com") || tabUrl.includes("youtu.be")) {
        urlInput.value = tabUrl;
      }
    }
  });
}

btnPaste.addEventListener("click", async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text) urlInput.value = text.trim();
  } catch {
    urlInput.focus();
  }
});

btnDownloadVideo.addEventListener("click", () => {
  const quality = qualitySelect ? qualitySelect.value : "best";
  triggerDownload("video", quality);
});

btnDownloadAudio.addEventListener("click", () => triggerDownload("audio", "audio_high"));
btnRefresh.addEventListener("click", refreshJobs);

if (btnClear) {
  btnClear.addEventListener("click", async () => {
    try {
      await fetch(`${API_BASE}/api/jobs/clear`, { method: "POST" });
      currentJobs = currentJobs.filter((j) => !["completed", "failed", "cancelled"].includes(j.status));
      renderJobs();
    } catch {
      // Ignorar si offline
    }
  });
}

window.cancelJob = async function (jobId) {
  try {
    await fetch(`${API_BASE}/api/jobs/${jobId}`, { method: "DELETE" });
  } catch {
    // Ignorar si offline
  }
};

async function triggerDownload(kind, quality) {
  const url = urlInput.value.trim();
  if (!url) {
    alert("Please enter a YouTube URL or Video ID");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, kind, quality }),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Error: ${err.detail || "Failed to start download"}`);
      return;
    }

    urlInput.value = "";
    refreshJobs();
  } catch {
    alert("Could not connect to local daemon.\nRun 'python -m adapters.in_bound.server'");
  }
}

function updateJobInList(job) {
  const existingIdx = currentJobs.findIndex((j) => j.job_id === job.job_id);
  if (existingIdx >= 0) {
    currentJobs[existingIdx] = { ...currentJobs[existingIdx], ...job };
  } else {
    currentJobs.unshift(job);
  }
  renderJobs();
}

function renderJobs() {
  if (!currentJobs || currentJobs.length === 0) {
    jobsList.innerHTML = `<div class="empty-state">No active downloads</div>`;
    return;
  }

  jobsList.innerHTML = currentJobs
    .slice(0, 5)
    .map((job) => {
      const isCancellable = ["pending", "resolving", "downloading", "muxing"].includes(job.status);
      const cancelBtnHtml = isCancellable
        ? `<button class="btn-cancel-job" onclick="cancelJob('${job.job_id}')" title="Cancel Job">✕</button>`
        : "";
      const pct = Math.round(job.progress_percentage || 0);

      return `
        <div class="job-card" id="card-${job.job_id}">
          <div class="job-card-top">
            <span class="job-id">Job #${job.job_id} (${(job.target_kind || "video").toUpperCase()})</span>
            <div style="display: flex; align-items: center; gap: 6px;">
              <span class="job-status ${job.status}">${job.status} ${pct > 0 && pct < 100 ? pct + "%" : ""}</span>
              ${cancelBtnHtml}
            </div>
          </div>
          <div class="job-progress-bar">
            <div class="job-progress-fill" style="width: ${job.progress_percentage || 0}%"></div>
          </div>
        </div>
      `;
    })
    .join("");
}

async function refreshJobs() {
  try {
    const res = await fetch(`${API_BASE}/api/jobs`);
    if (!res.ok) return;
    currentJobs = await res.json();
    renderJobs();
  } catch {
    // Offline
  }
}

// Server-Sent Events (SSE): Actualizaciones en tiempo real sin saturar la red local con requests repetitivos
function connectSSE() {
  if (eventSource) {
    eventSource.close();
  }

  try {
    eventSource = new EventSource(`${API_BASE}/api/events`);

    eventSource.onopen = () => {
      statusPill.className = "status-pill online";
      statusText.textContent = "Online";
    };

    eventSource.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload.type === "connected") {
          statusPill.className = "status-pill online";
          statusText.textContent = "Online";
          refreshJobs();
        } else if (payload.type === "job_update") {
          updateJobInList(payload);
        }
      } catch {
        // Heartbeats o comentarios
      }
    };

    eventSource.onerror = () => {
      statusPill.className = "status-pill offline";
      statusText.textContent = "Offline";
    };
  } catch {
    // Fallback silencioso
  }
}

// Inicializamos SSE y sincronizamos estado
connectSSE();
refreshJobs();
