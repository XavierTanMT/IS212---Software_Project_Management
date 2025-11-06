requireAuth();


  // Cache project id -> name
  const projectMap = Object.create(null);

  const ARCHIVE_PREF_KEY = "tasks_include_archived";
  function paramsFromUI(){
    const p = new URLSearchParams();
    const project_id = document.getElementById("project_id").value.trim();
    const assigned_to_id = document.getElementById("assigned_to_id").value.trim();
    const tag_filter = document.getElementById("tag_filter").value.trim();
    const limit = document.getElementById("limit").value.trim();
    const includeArchived = (localStorage.getItem(ARCHIVE_PREF_KEY) === 'true');
    if(project_id) p.set("project_id", project_id);
    if(assigned_to_id) p.set("assigned_to_id", assigned_to_id);
    if(tag_filter) p.set("label_id", tag_filter);
    if(limit) p.set("limit", limit);
    if(includeArchived) p.set("include_archived", "true");
    // Include viewer id as a fallback for servers that accept ?viewer_id
    try{
      const cu = (getCurrentUser && getCurrentUser()) || {};
      const vid = cu.user_id || cu.uid || cu.id || '';
      if (vid) p.set('viewer_id', vid);
    }catch(e){}
    return p.toString();
  }

  function nameForProject(id){
    if(!id) return "";
    return projectMap[id] || id; // fallback to id until map loaded
  }

  // Helper function to format assignees (handles single or multiple)
  function formatAssignees(assigned_to) {
    if (!assigned_to) return "Unassigned";
    
    // Handle array of assignees
    if (Array.isArray(assigned_to)) {
        if (assigned_to.length === 0) return "Unassigned";
        if (assigned_to.length === 1) return assigned_to[0].name || "Unassigned";
        return assigned_to.map(a => a.name).join(", "); // "John, Jane, Bob"
    }
    
    // Handle single assignee object
    return assigned_to.name || "Unassigned";
  }

  async function load(){
    const qs = paramsFromUI();
    // Ensure server sees the viewer id via header as well as querystring
    const current = (getCurrentUser && getCurrentUser()) || {};
    const viewerId = current.user_id || current.uid || current.id || '';
    const url = API_BASE + "/api/tasks" + (qs ? "?" + qs : "");
    console.debug('[tasks] fetching', { url, viewerId, qs });
    const res = await fetch(url, { headers: viewerId ? { 'X-User-Id': viewerId } : {} });
    const list = await res.json();
    const tbody = document.getElementById("rows"); tbody.innerHTML = "";
    if(!res.ok){ tbody.innerHTML = "<tr><td colspan='7'>"+ (list.error || "Failed to load") +"</td></tr>"; return; }
    console.debug('[tasks] fetched', Array.isArray(list) ? list.length : 'non-array', (Array.isArray(list) ? list.slice(0,5) : list));
    if(!Array.isArray(list) || !list.length){
      tbody.innerHTML = "<tr><td colspan='7'>No tasks</td></tr>";
      return;
    }

    // Role-aware filtering: staff -> see tasks assigned to them OR created by them
    // manager/director/hr -> see tasks belonging to their team (assigned to or created by team members) or tasks assigned to the manager
    // admin -> see everything
    const user = getCurrentUser() || {};
    const userId = user.user_id || user.uid || user.id || '';
    const role = (user.role || '').toLowerCase();
    const isManager = ['manager','director','hr','admin'].includes(role);

    // helper checks
    function taskHasAssignee(task, id){
      if(!task || !id) return false;
      const a = task.assigned_to;
      if(!a) return false;
      if(Array.isArray(a)) return a.some(x => (x && x.user_id && x.user_id === id) || x === id || (typeof x === 'string' && x === id));
      if(typeof a === 'object') return a.user_id === id || a === id;
      return a === id;
    }
    function createdByIs(task, id){
      if(!task || !id) return false;
      if(task.created_by){
        if(typeof task.created_by === 'object') return task.created_by.user_id === id || task.created_by.user_id === id;
        if(typeof task.created_by === 'string') return task.created_by === id;
      }
      if(task.created_by_id) return task.created_by_id === id;
      if(task.creator_id) return task.creator_id === id;
      return false;
    }

    async function getManagerTeamIds(){
      try{
        const resp = await fetch(`${API_BASE}/api/manager/my-team`, { headers: { 'X-User-Id': userId } });
        if(!resp.ok) return [];
        const data = await resp.json();
        return (Array.isArray(data.team_staff)?data.team_staff:[]).map(s=>s.user_id).filter(Boolean);
      }catch(e){
        return [];
      }
    }

    // The server enforces visibility rules (members, owners, managers, admins).
    // Show whatever the server returned rather than applying another client-side filter.
    const selectedProjectId = (document.getElementById('project_id') && document.getElementById('project_id').value || '').trim();
    let filtered = list; // server-returned tasks are authoritative

    filtered.forEach(t=>{
      const tr = document.createElement("tr");
      const showCompleteBtn = t.status !== 'Completed';

      // Determine if task is archived. Support both a boolean flag and a status string.
      const isArchived = Boolean(t.archived) || (t.status === 'Archived');

      // Create assign button for managers only (but not for archived tasks)
      const assignBtn = (!isArchived && isManager)
          ? `<button onclick='openAssignModal("${t.task_id}")' style='background:#007bff;color:white;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;margin-right:8px' title='Assign to team members'>👥 Assign</button>`
          : '';

      // Build actions column. If archived, show a simple label instead of action buttons/links.
      const actionsHtml = isArchived
          ? "<span class='pill'>Archived</span>"
          : (
              assignBtn
              + (showCompleteBtn ? "<button onclick='markAsDone(\"" + t.task_id + "\")' style='background:#28a745;color:white;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;margin-right:8px'>✓ Done</button>" : "")
              + "<a href='edit_task.html?task_id=" + encodeURIComponent(t.task_id) + "'>Edit</a> · "
              + "<a href='task_notes.html?task_id=" + encodeURIComponent(t.task_id) + "'>Notes</a> · "
              + "<a href='attachments.html?task_id=" + encodeURIComponent(t.task_id) + "'>Files</a>"
            );

      // compute progress percentage from subtask counts (no decimals)
      const total = Number(t.subtask_count || 0);
      const done = Number(t.subtask_completed_count || 0);
      const pct = total > 0 ? Math.round((done / total) * 100) : 0;
      tr.innerHTML = ""
        + "<td><a href='task_detail.html?task_id=" + encodeURIComponent(t.task_id) + "'>" + (t.title || "") + "</a></td>"
        + "<td>" + (total > 0 ? (pct + '%') : '0%') + "</td>"
        + "<td><span class='pill'>" + (t.status || "") + "</span></td>"
        + "<td>" + (t.priority || "") + "</td>"
        + "<td>" + (t.due_date || "") + "</td>"
        + "<td>" + nameForProject(t.project_id) + "</td>"
        + "<td>" + formatAssignees(t.assigned_to) + "</td>"
        + "<td>" + actionsHtml + "</td>";

      tbody.appendChild(tr);
    });
    console.debug('[tasks] rendered', { total: list.length, filtered: filtered.length });
  }

  document.getElementById("refresh").addEventListener("click", load);

  // --- archived toggle init ---
  const hideR = document.getElementById("hideArchived");
  const showR = document.getElementById("showArchived");
  const saved = localStorage.getItem(ARCHIVE_PREF_KEY);
  if (saved === 'true'){ showR.checked = true; } else { hideR.checked = true; }
  function onToggle(){
    const on = showR.checked;
    localStorage.setItem(ARCHIVE_PREF_KEY, on ? 'true' : 'false');
    load();
  }
  hideR.addEventListener("change", onToggle);
  showR.addEventListener("change", onToggle);

  async function fillProjects(){
    const res = await fetch(API_BASE + "/api/projects");
    const list = await res.json();
    const sel = document.getElementById("project_select");
    sel.innerHTML = '<option value="">(all my tasks)</option>';
    (Array.isArray(list)?list:[]).forEach(p=>{
      const opt = document.createElement('option');
      opt.value = p.project_id; opt.textContent = p.name || p.project_id;
      sel.appendChild(opt);
      projectMap[p.project_id] = p.name || p.project_id; // populate map
    });
    const cp = getCurrentProject();
    if(cp && cp.project_id){ sel.value = cp.project_id; document.getElementById("project_id").value = cp.project_id; }
    sel.addEventListener("change", ()=>{
      document.getElementById("project_id").value = sel.value;
      load();
    });
  }

  document.addEventListener("DOMContentLoaded", async function(){
    await fillProjects();
    await load();
  });

  // Mark task as done
  async function markAsDone(taskId) {
    if (!confirm('Mark this task as completed?')) return;
    
    try {
      const user = getCurrentUser() || {};
      const uid = user.user_id || user.uid || user.id || '';
      const response = await fetch(API_BASE + "/api/tasks/" + taskId, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': uid
        },
        body: JSON.stringify({ status: 'Completed' })
      });

      const result = await response.json();

      if (response.ok) {
        alert('Task marked as completed!');
        
        // If this was a recurring task, show info about next occurrence
        if (result.next_recurring_task_id) {
          alert('Task completed! Next occurrence has been created.');
        }
        
        // Refresh the task list
        await load();
      } else {
        alert('Failed to complete task: ' + (result.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error marking task as done:', error);
      alert('Network error. Please check your connection and try again.');
    }
  }
  


  // Assignment Modal Functions
  let currentAssignTaskId = null;
  let teamMembers = [];

  async function openAssignModal(taskId) {
      currentAssignTaskId = taskId;
      document.getElementById('assignModal').style.display = 'block';
      await loadTeamMembers();
  }

  function closeAssignModal() {
      document.getElementById('assignModal').style.display = 'none';
      currentAssignTaskId = null;
  }

  async function loadTeamMembers() {
    const user = getCurrentUser() || {};
      const listDiv = document.getElementById('teamMembersList');
      
      listDiv.innerHTML = '<p style="padding:20px;text-align:center;color:#666">Loading team members...</p>';
      
      try {
          // ✅ Step 1: Get team members
      const uid = user.user_id || user.uid || user.id || '';
      const response = await fetch(`${API_BASE}/api/manager/my-team`, {
        headers: { 'X-User-Id': uid }
      });
          
          if (!response.ok) {
              throw new Error('Failed to load team members');
          }
          
          const data = await response.json();
          teamMembers = data.team_staff || [];
          
          if (teamMembers.length === 0) {
              listDiv.innerHTML = '<p style="padding:20px;color:#666;text-align:center">No team members found.<br>Add staff to your team from the <a href="manager_dashboard.html">Manager Dashboard</a>.</p>';
              return;
          }
          
          // ✅ Step 2: Get current task to find existing assignees
          const taskResponse = await fetch(`${API_BASE}/api/tasks/${currentAssignTaskId}`);
          const taskData = await taskResponse.json();
          
          // ✅ Step 3: Extract current assignee IDs
          let currentAssigneeIds = [];
          if (taskData && taskData.assigned_to) {
              if (Array.isArray(taskData.assigned_to)) {
                  // Multiple assignees
                  currentAssigneeIds = taskData.assigned_to.map(a => a.user_id);
              } else {
                  // Single assignee
                  currentAssigneeIds = [taskData.assigned_to.user_id];
              }
          }
          
          // ✅ Step 4: Render checkboxes with current assignees pre-checked and highlighted
          listDiv.innerHTML = teamMembers.map(member => {
              const isCurrentlyAssigned = currentAssigneeIds.includes(member.user_id);
              return `
                  <div style="padding:12px; border-bottom:1px solid #eee; background:${isCurrentlyAssigned ? '#e8f5e9' : 'white'}">
                      <label style="display:flex; align-items:center; cursor:pointer">
                          <input type="checkbox" 
                                 value="${member.user_id}" 
                                 class="team-member-checkbox" 
                                 ${isCurrentlyAssigned ? 'checked' : ''}
                                 style="margin-right:10px; width:18px; height:18px; cursor:pointer">
                          <div style="flex:1">
                              <strong style="font-size:14px">${member.name}</strong>
                              ${isCurrentlyAssigned ? '<span style="color:#4caf50;font-size:12px;margin-left:8px;font-weight:bold">✓ Currently Assigned</span>' : ''}
                              <br>
                              <small style="color:#666">${member.email}</small>
                          </div>
                      </label>
                  </div>
              `;
          }).join('');
          
      } catch (error) {
          console.error('Error loading team members:', error);
          listDiv.innerHTML = '<p style="padding:20px;color:red;text-align:center">Error loading team members.<br>Please try again.</p>';
      }
  }

  async function assignSelectedMembers() {
    const user = getCurrentUser() || {};
      const selectedIds = Array.from(document.querySelectorAll('.team-member-checkbox:checked'))
          .map(cb => cb.value);
      
      if (selectedIds.length === 0) {
          alert('Please select at least one team member');
          return;
      }
      
      try {
      const uid = user.user_id || user.uid || user.id || '';
      const response = await fetch(`${API_BASE}/api/manager/tasks/${currentAssignTaskId}/assign`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': uid
        },
        body: JSON.stringify({ assignee_ids: selectedIds })
      });
          
          const result = await response.json();
          
          if (response.ok) {
              alert(`✅ Task assigned to ${selectedIds.length} team member(s)`);
              closeAssignModal();
              await load(); // Refresh task list
          } else {
              alert(`❌ Error: ${result.error || 'Failed to assign task'}`);
          }
      } catch (error) {
          console.error('Error assigning task:', error);
          alert('❌ Network error. Please try again.');
      }
  }

  // Close modal when clicking outside
  document.getElementById('assignModal')?.addEventListener('click', function(e) {
      if (e.target === this) {
          closeAssignModal();
      }
  });
  


  // --- PATCH: tasks empty state --- //
  (function(){
    if (window.__tasksPatchApplied) return; window.__tasksPatchApplied = true;
    function afterLoad(){
      const listHost = document.querySelector('#tasksList, .tasks-list, #taskList');
      if (!listHost) return;
      if (listHost.children.length === 0 || listHost.innerHTML.trim() === ''){
        listHost.innerHTML = '<div style="padding:12px;color:#666">No tasks yet. Create your first task.</div>';
      }
      document.querySelectorAll('.loading, .spinner').forEach(el=>el.remove());
    }
    window.addEventListener('load', ()=> setTimeout(afterLoad, 200));
  })();
  