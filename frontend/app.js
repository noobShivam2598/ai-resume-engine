const uploadForm = document.getElementById("uploadForm");
const uploadMessage = document.getElementById("uploadMessage");
const urlForm = document.getElementById("urlForm");
const urlMessage = document.getElementById("urlMessage");
const listMessage = document.getElementById("listMessage");
const tableBody = document.getElementById("resumeTableBody");
const resumeDetail = document.getElementById("resumeDetail");
const refreshBtn = document.getElementById("refreshBtn");
const totalResumes = document.getElementById("totalResumes");
const analyzedResumes = document.getElementById("analyzedResumes");
const pendingResumes = document.getElementById("pendingResumes");
const dashboard = document.getElementById("dashboard");
const sidebarToggle = document.getElementById("sidebarToggle");
let currentUrlAnalysis = null;

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data?.detail || `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return data;
}

function formatDate(dateString) {
  if (!dateString) return "-";
  const date = new Date(dateString);
  return Number.isNaN(date.getTime()) ? dateString : date.toLocaleString();
}

function statusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value === "analyzed" || value === "parsed") return "status-analyzed";
  if (value === "failed") return "status-failed";
  return "status-parsing";
}

function updateStats(resumes) {
  const total = resumes.length;
  const analyzed = resumes.filter((r) => String(r.status).toLowerCase() === "analyzed").length;
  const pending = total - analyzed;
  totalResumes.textContent = String(total);
  analyzedResumes.textContent = String(analyzed);
  pendingResumes.textContent = String(pending);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderResumeDetail(detail) {
  const skills = Array.isArray(detail?.parsed_data?.skills) ? detail.parsed_data.skills : [];
  const jobSkills = Array.isArray(currentUrlAnalysis?.skills) ? currentUrlAnalysis.skills : [];
  const profileSkillSet = new Set(skills.map(normalizeSkill).filter(Boolean));
  const hasJobSkills = jobSkills.length > 0;
  const skillMarkup = hasJobSkills
    ? jobSkills
        .map((skill) => {
          const matched = profileSkillSet.has(normalizeSkill(skill));
          const chipClass = matched ? "skill-chip-match" : "skill-chip-miss";
          return `<span class="skill-chip ${chipClass}">${escapeHtml(skill)}</span>`;
        })
        .join("")
    : skills.length > 0
      ? skills.map((skill) => `<span class="skill-chip">${escapeHtml(skill)}</span>`).join("")
      : '<p class="empty-text">No skills detected.</p>';
  const exp = detail?.parsed_data?.experience_years;
  const expText = Number.isInteger(exp) ? `${exp} year(s)` : "Not available";
  const match = computeMatchPercentage(skills, currentUrlAnalysis?.skills || []);
  const matchText = Number.isInteger(match) ? `${match}%` : "Analyze Job URL to see match";

  resumeDetail.className = "";
  resumeDetail.innerHTML = `
    <div class="detail-grid">
      <article class="detail-item">
        <p class="detail-label">Resume ID</p>
        <p class="detail-value">${escapeHtml(detail.id)}</p>
      </article>
      <article class="detail-item">
        <p class="detail-label">Status</p>
        <p class="detail-value">
          <span class="status-chip ${statusClass(detail.status)}">${escapeHtml(detail.status)}</span>
        </p>
      </article>
      <article class="detail-item full">
        <p class="detail-label">File Name</p>
        <p class="detail-value">${escapeHtml(detail.file_name || "-")}</p>
      </article>
      <article class="detail-item">
        <p class="detail-label">Experience</p>
        <p class="detail-value">${escapeHtml(expText)}</p>
      </article>
      <article class="detail-item">
        <p class="detail-label">Match</p>
        <p class="detail-value">${escapeHtml(matchText)}</p>
      </article>
      <article class="detail-item full">
        <p class="detail-label">Skills ${hasJobSkills ? '(Green = matched, Red = missing in profile)' : ""}</p>
        <div class="skills-wrap">${skillMarkup}</div>
      </article>
    </div>
  `;
}

function renderUrlDetail(detail) {
  const skills = Array.isArray(detail?.skills) ? detail.skills : [];
  const skillMarkup =
    skills.length > 0
      ? skills.map((skill) => `<span class="skill-chip">${escapeHtml(skill)}</span>`).join("")
      : '<p class="empty-text">No skills detected.</p>';
  const roleText = detail?.role ? String(detail.role) : "Not available";
  const expText = Number.isInteger(detail?.experience_years) ? `${detail.experience_years} year(s)` : "Not available";

  resumeDetail.className = "";
  resumeDetail.innerHTML = `
    <div class="detail-grid">
      <article class="detail-item full">
        <p class="detail-label">Source URL</p>
        <p class="detail-value">${escapeHtml(detail?.url || "-")}</p>
      </article>
      <article class="detail-item">
        <p class="detail-label">Role</p>
        <p class="detail-value">${escapeHtml(roleText)}</p>
      </article>
      <article class="detail-item">
        <p class="detail-label">Experience</p>
        <p class="detail-value">${escapeHtml(expText)}</p>
      </article>
      <article class="detail-item full">
        <p class="detail-label">Skills</p>
        <div class="skills-wrap">${skillMarkup}</div>
      </article>
    </div>
  `;
}

function normalizeSkill(skill) {
  return String(skill || "").trim().toLowerCase();
}

function computeMatchPercentage(resumeSkills, jobSkills) {
  const jobSet = new Set((Array.isArray(jobSkills) ? jobSkills : []).map(normalizeSkill).filter(Boolean));
  if (jobSet.size === 0) return null;
  const resumeSet = new Set((Array.isArray(resumeSkills) ? resumeSkills : []).map(normalizeSkill).filter(Boolean));
  let overlap = 0;
  for (const s of jobSet) {
    if (resumeSet.has(s)) overlap += 1;
  }
  return Math.round((overlap / jobSet.size) * 100);
}

async function updateMatchPercentages(resumes) {
  if (!currentUrlAnalysis?.skills?.length) return;
  const rowsById = new Map();
  for (const row of tableBody.querySelectorAll("tr[data-resume-id]")) {
    rowsById.set(Number(row.dataset.resumeId), row);
  }

  for (const resume of resumes) {
    const row = rowsById.get(Number(resume.id));
    if (!row) continue;
    const target = row.querySelector(".match-cell");
    if (!target) continue;
    target.textContent = "Calculating...";
    try {
      const detail = await fetchJson(`/api/resumes/${resume.id}`);
      const resumeSkills = detail?.parsed_data?.skills || [];
      const match = computeMatchPercentage(resumeSkills, currentUrlAnalysis.skills);
      target.innerHTML = Number.isInteger(match) ? `<span class="match-chip">${match}%</span>` : "-";
    } catch (_) {
      target.textContent = "-";
    }
  }
}

async function loadResumes() {
  listMessage.textContent = "Loading resumes...";
  tableBody.innerHTML = "";

  try {
    const resumes = await fetchJson("/api/resumes");
    updateStats(Array.isArray(resumes) ? resumes : []);
    if (!Array.isArray(resumes) || resumes.length === 0) {
      listMessage.textContent = "No resumes found.";
      return [];
    }

    listMessage.textContent = `Loaded ${resumes.length} resume(s).`;
    for (const resume of resumes) {
      const tr = document.createElement("tr");
      tr.dataset.resumeId = String(resume.id);
      tr.innerHTML = `
        <td>${resume.id}</td>
        <td>${resume.file_name}</td>
        <td><span class="status-chip ${statusClass(resume.status)}">${resume.status}</span></td>
        <td class="match-cell">-</td>
        <td>${formatDate(resume.created_at)}</td>
        <td>
          <button class="action-btn btn btn-primary" data-action="view" data-id="${resume.id}">View</button>
          <button class="action-btn btn danger" data-action="delete" data-id="${resume.id}">Delete</button>
        </td>
      `;
      tableBody.appendChild(tr);
    }
    await updateMatchPercentages(resumes);
    return resumes;
  } catch (error) {
    updateStats([]);
    listMessage.textContent = `Failed to load resumes: ${error.message}`;
    return [];
  }
}

async function viewResume(id) {
  resumeDetail.className = "resume-detail-empty";
  resumeDetail.textContent = "Loading detail...";
  try {
    const detail = await fetchJson(`/api/resumes/${id}`);
    renderResumeDetail(detail);
  } catch (error) {
    resumeDetail.className = "resume-detail-empty";
    resumeDetail.textContent = `Failed to load detail: ${error.message}`;
  }
}

async function deleteResume(id) {
  const ok = window.confirm(`Delete resume ${id}?`);
  if (!ok) return;

  try {
    await fetchJson(`/api/resumes/${id}`, { method: "DELETE" });
    listMessage.textContent = `Deleted resume ${id}.`;
    if (resumeDetail.textContent.includes(String(id))) {
      resumeDetail.className = "resume-detail-empty";
      resumeDetail.textContent = 'Select "View" from the list above.';
    }
    await loadResumes();
  } catch (error) {
    listMessage.textContent = `Delete failed: ${error.message}`;
  }
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  uploadMessage.textContent = "Uploading...";

  const formData = new FormData(uploadForm);
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    uploadMessage.textContent = "Please choose a file.";
    return;
  }

  try {
    const result = await fetchJson("/api/upload", {
      method: "POST",
      body: formData,
    });
    uploadMessage.textContent = `Uploaded resume ${result.id} (${result.status}).`;
    uploadForm.reset();
    document.getElementById("userId").value = "1";
    await loadResumes();
    await viewResume(result.id);
  } catch (error) {
    uploadMessage.textContent = `Upload failed: ${error.message}`;
  }
});

if (urlForm) {
  urlForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    urlMessage.textContent = "Analyzing URL...";
    const formData = new FormData(urlForm);
    const url = String(formData.get("url") || "").trim();
    if (!url) {
      urlMessage.textContent = "Please enter a valid URL.";
      return;
    }
    try {
      const result = await fetchJson("/api/analyze-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      currentUrlAnalysis = result;
      urlMessage.textContent = "URL analyzed successfully.";
      const resumes = await loadResumes();
      if (Array.isArray(resumes) && resumes.length > 0) {
        await viewResume(resumes[0].id);
      } else {
        renderUrlDetail(result);
      }
    } catch (error) {
      urlMessage.textContent = `URL analysis failed: ${error.message}`;
    }
  });
}

refreshBtn.addEventListener("click", () => {
  loadResumes();
});

if (sidebarToggle && dashboard) {
  sidebarToggle.addEventListener("click", () => {
    dashboard.classList.toggle("sidebar-collapsed");
  });
}

tableBody.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) return;
  const id = Number(target.dataset.id);
  const action = target.dataset.action;
  if (!id || !action) return;

  if (action === "view") {
    viewResume(id);
  } else if (action === "delete") {
    deleteResume(id);
  }
});

loadResumes();
