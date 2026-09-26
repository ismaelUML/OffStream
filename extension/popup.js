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

// Si el usuario ya está viendo un video en la pestaña activa, le ahorramos
// el embole de tener que copiar y pegar la URL a mano.
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs && tabs[0] && tabs[0].url) {
    const tabUrl = tabs[0].url;
    if (tabUrl.includes("youtube.com") || tabUrl.includes("youtu.be")) {
      urlInput.value = tabUrl;
    }
  }
});

async function checkHealth() {
  try {
    // Timeout corto de 1.2s: si el daemon local no responde al toque,
    // es porque está apagado; no dejemos la UI clavada esperando.
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(1200) });
    if (res.ok) {
      statusPill.className = "status-pill online";
      statusText.textContent = "Online";
      return true;
    }
  } catch {
    // Daemon apagado o muerto en segundo plano.
  }
  statusPill.className = "status-pill offline";
  statusText.textContent = "Offline";
  return false;
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
      refreshJobs();
    } catch {
      // Ignorar si offline
    }
  });
}

window.cancelJob = async function (jobId) {
  try {
    await fetch(`${API_BASE}/api/jobs/${jobId}`, { method: "DELETE" });
    refreshJobs();
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
  } catch (err) {
    alert(`Could not connect to local daemon.\nRun 'python -m adapters.in_bound.server'`);
  }
}

async function refreshJobs() {
  try {
    const res = await fetch(`${API_BASE}/api/jobs`);
    if (!res.ok) return;

    const jobs = await res.json();
    if (jobs.length === 0) {
      jobsList.innerHTML = `<div class="empty-state">No active downloads</div>`;
      return;
    }

    jobsList.innerHTML = jobs
      .slice(-4)
      .reverse()
      .map((job) => {
        const isCancellable = ["pending", "resolving", "downloading", "muxing"].includes(job.status);
        const cancelBtnHtml = isCancellable
          ? `<button class="btn-cancel-job" onclick="cancelJob('${job.job_id}')" title="Cancel Job">✕</button>`
          : "";

        return `
          <div class="job-card">
            <div class="job-card-top">
              <span class="job-id">Job #${job.job_id} (${job.target_kind.toUpperCase()})</span>
              <div style="display: flex; align-items: center; gap: 6px;">
                <span class="job-status ${job.status}">${job.status}</span>
                ${cancelBtnHtml}
              </div>
            </div>
            <div class="job-progress-bar">
              <div class="job-progress-fill" style="width: ${job.progress_percentage}%"></div>
            </div>
          </div>
        `;
      })
      .join("");
  } catch {
    // Offline
  }
}

// Polling cada 2 segundos. No es WebSockets ni magia reactiva, pero para
// ver la barrita de progreso de una descarga local alcanza y sobra sin comer CPU.
checkHealth().then(refreshJobs);
setInterval(() => {
  checkHealth();
  refreshJobs();
}, 2000);
