requireAuth();


  const API = API_BASE;
  function q(name){
    return new URLSearchParams(location.search).get(name);
  }
  const taskId = q('task_id');
  if(!taskId){ document.body.innerHTML = '<div style="padding:20px">Missing task_id</div>'; }

  async function load(){
    const viewer = (getCurrentUser && getCurrentUser()) || {};
    const vid = viewer.user_id || viewer.uid || viewer.id || '';

    // Fetch task
    const res = await fetch(API + '/api/tasks/' + encodeURIComponent(taskId), { headers: vid?{ 'X-User-Id': vid } : {} });
    if(!res.ok){ const e = await res.json().catch(()=>({})); document.getElementById('title').textContent = 'Task not found'; return; }
    const task = await res.json();
    document.getElementById('title').textContent = task.title || 'Task';
    const meta = document.getElementById('taskMeta');
    meta.innerHTML = '';
    meta.innerHTML += '<div><strong>Status:</strong> <span class="pill">'+(task.status||'')+'</span></div>';
    meta.innerHTML += '<div><strong>Priority:</strong> '+(task.priority||'')+'</div>';
    // Show project name instead of id when possible
    if (task.project_id) {
      try {
        const pRes = await fetch(API + '/api/projects');
        if (pRes.ok) {
          const projects = await pRes.json();
          const proj = (Array.isArray(projects)?projects:[]).find(p=>p.project_id===task.project_id) || {};
          meta.innerHTML += '<div><strong>Project:</strong> '+(proj.name || task.project_id)+'</div>';
        } else {
          meta.innerHTML += '<div><strong>Project:</strong> '+(task.project_id||'')+'</div>';
        }
      } catch(e) {
        meta.innerHTML += '<div><strong>Project:</strong> '+(task.project_id||'')+'</div>';
      }
    } else {
      meta.innerHTML += '<div><strong>Project:</strong> '+(task.project_id||'')+'</div>';
    }
    meta.innerHTML += '<div style="margin-top:8px"><strong>Description</strong><div>'+(task.description||'')+'</div></div>';

  // show counts and percentage (no decimals)
  const total = Number(task.subtask_count || 0);
  const completed = Number(task.subtask_completed_count || 0);
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  document.getElementById('subcounts').textContent = `(${completed}/${total} — ${percent}%)`;

    // show create form only if viewer is creator
    const isCreator = vid && task.created_by && task.created_by.user_id === vid;
    document.getElementById('creatorActions').style.display = isCreator ? 'block' : 'none';

    await loadSubtasks();
  }

  async function loadSubtasks(){
    const viewer = (getCurrentUser && getCurrentUser()) || {};
    const vid = viewer.user_id || viewer.uid || viewer.id || '';
    const res = await fetch(API + '/api/tasks/' + encodeURIComponent(taskId) + '/subtasks', { headers: vid?{ 'X-User-Id': vid } : {} });
    const list = await res.json();
    const host = document.getElementById('subtasks'); host.innerHTML = '';
    if(!res.ok){ host.innerHTML = '<div style="padding:10px;color:red">Failed to load subtasks</div>'; return; }
    if(!Array.isArray(list) || !list.length){ host.innerHTML = '<div style="padding:8px;color:#666">No subtasks</div>'; return; }

    const viewerId = vid;
    const taskCreatorId = (getCurrentUser && getCurrentUser()).user_id; // may be used later

    list.forEach(s=>{
      const div = document.createElement('div'); 
      div.className = 'subtask';
      div.style.cssText = 'display:flex;align-items:flex-start;gap:12px;padding:12px;margin:8px 0;background:#f9f9f9;border-radius:6px;border-left:3px solid #3498db';
      
      const cb = document.createElement('input'); 
      cb.type='checkbox'; 
      cb.checked = !!s.completed;
      cb.style.cssText = 'margin-top:4px;cursor:pointer;width:18px;height:18px;flex-shrink:0';
      cb.addEventListener('change', async ()=>{
        try{
          const r = await fetch(API + '/api/tasks/' + encodeURIComponent(taskId) + '/subtasks/' + encodeURIComponent(s.subtask_id) + '/complete', {
            method: 'PATCH',
            headers: { 'Content-Type':'application/json', ...(viewerId?{'X-User-Id': viewerId}: {}) },
            body: JSON.stringify({ completed: cb.checked })
          });
          if(!r.ok){ alert('Failed to update'); cb.checked = !cb.checked; return; }
          await load();
        }catch(e){ console.error(e); cb.checked = !cb.checked; alert('Network error'); }
      });

      const meta = document.createElement('div'); 
      meta.className='meta';
      meta.style.cssText = 'flex:1;min-width:0';
      meta.innerHTML = '<div style="font-weight:600;margin-bottom:4px;color:#333">'+(s.title||'')+'</div>' + (s.description?('<div style="color:#666;font-size:0.9em;line-height:1.4">'+s.description+'</div>'):'');

      div.appendChild(cb); div.appendChild(meta);

      // If viewer is task creator, show edit/delete
      (async function(){
    const tRes = await fetch(API + '/api/tasks/' + encodeURIComponent(taskId), { headers: vidNow?{ 'X-User-Id': vidNow } : {} });
    const t = await tRes.json().catch(()=>({}));
        const viewerNow = (getCurrentUser && getCurrentUser()) || {};
        const vidNow = viewerNow.user_id || viewerNow.uid || viewerNow.id || '';
        const isCreator = vidNow && t.created_by && t.created_by.user_id === vidNow;
        if(isCreator){
          const btnContainer = document.createElement('div');
          btnContainer.style.cssText = 'display:flex;gap:6px;margin-left:auto;flex-shrink:0';
          
          const edit = document.createElement('button'); 
          edit.textContent = 'Edit'; 
          edit.style.cssText = 'padding:4px 12px;font-size:0.85em;background:#3498db;color:white;border:none;border-radius:4px;cursor:pointer';
          edit.addEventListener('click', ()=>{
            const newTitle = prompt('Title', s.title||''); if(newTitle===null) return;
            const newDesc = prompt('Description', s.description||'');
            fetch(API + '/api/tasks/' + encodeURIComponent(taskId) + '/subtasks/' + encodeURIComponent(s.subtask_id), {
              method: 'PUT', headers: { 'Content-Type':'application/json', ...(vidNow?{'X-User-Id': vidNow}: {}) },
              body: JSON.stringify({ title: newTitle, description: newDesc })
            }).then(r=>{ if(!r.ok) return r.json().then(js=>alert(js.error||'Failed')); else loadSubtasks(); });
          });
          const del = document.createElement('button'); 
          del.textContent = 'Delete'; 
          del.style.cssText = 'padding:4px 12px;font-size:0.85em;background:#e74c3c;color:white;border:none;border-radius:4px;cursor:pointer';
          del.addEventListener('click', ()=>{
            if(!confirm('Delete this subtask?')) return;
            fetch(API + '/api/tasks/' + encodeURIComponent(taskId) + '/subtasks/' + encodeURIComponent(s.subtask_id), {
              method: 'DELETE', headers: {...(vidNow?{'X-User-Id': vidNow}: {}) }
            }).then(async r=>{ if(!r.ok){ const j = await r.json().catch(()=>({})); alert(j.error||'Failed'); } else { await load(); } });
          });
          btnContainer.appendChild(edit); 
          btnContainer.appendChild(del);
          div.appendChild(btnContainer);
        }
      })();

      host.appendChild(div);
    });
  }

  document.getElementById('addSub')?.addEventListener('click', async function(){
    const viewer = (getCurrentUser && getCurrentUser()) || {};
    const vid = viewer.user_id || viewer.uid || viewer.id || '';
    const title = document.getElementById('sub_title').value.trim();
    const description = document.getElementById('sub_description').value.trim();
    if(!title){ alert('Enter title'); return; }
    try{
      const r = await fetch(API + '/api/tasks/' + encodeURIComponent(taskId) + '/subtasks', {
        method: 'POST', headers: { 'Content-Type':'application/json', ...(vid?{'X-User-Id': vid}: {}) },
        body: JSON.stringify({ title, description })
      });
      if(!r.ok){ const j = await r.json().catch(()=>({})); alert(j.error || 'Failed'); return; }
      document.getElementById('sub_title').value = '';
      document.getElementById('sub_description').value = '';
      await load();
    }catch(e){ console.error(e); alert('Network error'); }
  });

  load();
  