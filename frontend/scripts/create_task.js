
requireAuth();

// Subtasks state & helpers
const subtasks = [];

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function renderSubtasks() {
  const host = document.getElementById('subtasksList');
  host.innerHTML = '';
  subtasks.forEach((s, idx) => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;align-items:flex-start;margin-bottom:8px;padding:8px;background:#f9f9f9;border-radius:4px';
    const descHtml = s.description ? `<div style="color:#666;font-size:0.9em;margin-top:2px">${escapeHtml(s.description)}</div>` : '';
    row.innerHTML = `
        <div style="flex:1">
          <div style="font-weight:500">${escapeHtml(s.title)}</div>
          ${descHtml}
          ${s.due_date ? '<small style="color:#999">Due: ' + escapeHtml(s.due_date) + '</small>' : ''}
        </div>
        <button type="button" data-idx="${idx}" class="removeSub" style="padding:4px 8px;cursor:pointer;align-self:flex-start">Remove</button>
      `;
    host.appendChild(row);
  });
  // attach listeners
  host.querySelectorAll('.removeSub').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const i = Number(e.currentTarget.dataset.idx);
      subtasks.splice(i, 1);
      renderSubtasks();
    });
  });
}

document.getElementById('addSubtaskBtn').addEventListener('click', () => {
  const title = document.getElementById('newSubtaskTitle').value.trim();
  const description = document.getElementById('newSubtaskDesc').value.trim();
  const due = document.getElementById('newSubtaskDue').value || null;
  if (!title) {
    alert('Subtask title required');
    return;
  }
  subtasks.push({ title, description: description || null, due_date: due, status: 'To Do' });
  document.getElementById('newSubtaskTitle').value = '';
  document.getElementById('newSubtaskDesc').value = '';
  document.getElementById('newSubtaskDue').value = '';
  renderSubtasks();
});

// Toggle recurring options visibility
document.getElementById("is_recurring").addEventListener("change", (e) => {
  const options = document.getElementById("recurring_options");
  options.style.display = e.target.checked ? "block" : "none";
  if (!e.target.checked) {
    document.getElementById("recurrence_interval_days").value = "";
  }
});

async function loadProjects() {
  const sel = document.getElementById("project_id");
  const res = await fetch(API_BASE + "/api/projects");
  const list = await res.json();
  if (Array.isArray(list)) {
    list.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.project_id;
      opt.textContent = p.name + " (" + p.project_id + ")";
      sel.appendChild(opt);
    });
  }
  const cp = getCurrentProject();
  if (cp && cp.project_id) { sel.value = cp.project_id; }
}


document.getElementById("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const current = requireAuth();
  const btn = e.submitter || document.querySelector('#form button[type="submit"]');
  const msg = document.getElementById("formMsg");

  const isRecurring = document.getElementById("is_recurring").checked;
  const recurrenceInterval = document.getElementById("recurrence_interval_days").value;
  const dueDate = document.getElementById("due_date").value;

  // Validation for recurring tasks
  if (isRecurring) {
    if (!dueDate) {
      alert("Recurring tasks must have a due date");
      return;
    }
    if (!recurrenceInterval || parseInt(recurrenceInterval) <= 0) {
      alert("Please specify a positive number of days for recurrence interval");
      return;
    }
  }

  const payload = {
    title: document.getElementById("title").value.trim(),
    description: document.getElementById("description").value.trim(),
    priority: document.getElementById("priority").value,
    status: document.getElementById("status").value,
    due_date: dueDate || null,
    created_by_id: current.user_id,
    project_id: document.getElementById("project_id").value || null,
    is_recurring: isRecurring,
    recurrence_interval_days: isRecurring ? parseInt(recurrenceInterval) : null,
    tags: [
      document.getElementById("tag1").value.trim(),
      document.getElementById("tag2").value.trim(),
      document.getElementById("tag3").value.trim()
    ].filter(t => t.length > 0),
    subtasks: subtasks  // Include subtasks array
  };
  if (!payload.title || payload.title.length < 3) {
    alert("Title must be at least 3 characters"); return;
  }
  if (!payload.description || payload.description.length < 10) {
    alert("Description must be at least 10 characters"); return;
  }
  btn.disabled = true; const old = btn.textContent; btn.textContent = "Creating..."; msg.textContent = "Creating task...";
  try {
    const res = await fetch(API_BASE + "/api/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    let data = null; let text = "";
    try { data = await res.json(); } catch (_) { try { text = await res.text(); } catch (e) { } }
    if (!res.ok) {
      const err = (data && (data.error || JSON.stringify(data))) || text || ("HTTP " + res.status);
      alert("Create task failed: " + err);
      msg.textContent = "❌ " + err;
      return;
    }
    msg.textContent = "✅ Task created";
    alert("Task created");
    window.location.href = "tasks_list.html";
  } catch (err) {
    console.error(err);
    alert("Create task failed: " + (err.message || err));
    msg.textContent = "❌ " + (err.message || err);
  } finally {
    btn.disabled = false; btn.textContent = old;
  }
});

loadProjects();



// --- PATCH: generic empty-state guard --- //
(function () {
  if (window.__genericEmptyPatchApplied) return; window.__genericEmptyPatchApplied = true;
  function afterLoad() {
    document.querySelectorAll('.loading,.spinner').forEach(el => el.remove());
    const empties = [
      ['#labelsList,.labels-list', 'No labels yet.'],
      ['#attachmentsList,.attachments-list', 'No attachments yet.'],
      ['#commentsList,.comments-list', 'No comments yet.'],
      ['#membersList,.members-list', 'No members yet.'],
    ];
    for (const [sel, text] of empties) {
      const host = document.querySelector(sel);
      if (host && (host.children.length === 0 || host.innerHTML.trim() === '')) {
        host.innerHTML = `<div style="padding:12px;color:#666">${text}</div>`;
      }
    }
  }
  window.addEventListener('load', () => setTimeout(afterLoad, 200));
})();
