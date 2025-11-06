requireAuth();


  const API = API_BASE;
  function q(name){
    return new URLSearchParams(location.search).get(name);
  }
  const taskId = q('task_id');
  if(!taskId){ document.body.innerHTML = '<div style="padding:20px">Missing task_id</div>'; }

  // File validation constants
  const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.xlsx', '.xls', '.csv', '.png', '.jpg', '.jpeg', '.txt', '.md', '.pptx', '.zip'];
  const BLOCKED_EXTENSIONS = ['.exe', '.bat', '.sh', '.js', '.cmd', '.com', '.app', '.vbs', '.ps1', '.jar', '.dmg', '.deb', '.rpm'];
  const MAX_FILE_SIZE = 700 * 1024; // 700 KB (Firestore document limit after Base64 encoding)

  const ALLOWED_MIME_TYPES = {
    'application/pdf': true,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': true,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': true,
    'application/vnd.ms-excel': true,
    'text/csv': true,
    'image/png': true,
    'image/jpeg': true,
    'text/plain': true,
    'text/markdown': true,
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': true,
    'application/zip': true,
    'application/x-zip-compressed': true
  };

  function validateFile(file) {
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return { valid: false, error: `File size exceeds 700 KB limit (${(file.size / 1024).toFixed(2)} KB). This limit exists because files are stored in Firestore.` };
    }

    // Check extension
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (BLOCKED_EXTENSIONS.includes(ext)) {
      return { valid: false, error: `File type not allowed: ${ext}` };
    }
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return { valid: false, error: `File type not supported: ${ext}` };
    }

    // Check MIME type
    if (!ALLOWED_MIME_TYPES[file.type]) {
      return { valid: false, error: `MIME type not allowed: ${file.type}` };
    }

    return { valid: true };
  }

  async function calculateFileHash(file) {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  async function uploadAttachment(file) {
    const viewer = getCurrentUser() || {};
    const userId = viewer.user_id || viewer.uid || viewer.id || '';
    
    if (!userId) {
      throw new Error('User not authenticated');
    }

    // Validate file
    const validation = validateFile(file);
    if (!validation.valid) {
      throw new Error(validation.error);
    }

    const progressDiv = document.getElementById('uploadProgress');
    progressDiv.style.display = 'block';
    progressDiv.innerHTML = 'Reading file...';

    // Calculate file hash
    const fileHash = await calculateFileHash(file);
    
    progressDiv.innerHTML = 'Converting file...';

    // Convert file to Base64 (FREE - no Firebase Storage needed!)
    const base64Data = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

    progressDiv.innerHTML = 'Uploading...';
    
    console.log('Uploading file as Base64 (size:', file.size, 'bytes)');
    
    // Save directly to backend (which stores in Firestore)
    const response = await fetch(API + '/api/attachments', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': userId
      },
      body: JSON.stringify({
        task_id: taskId,
        filename: file.name,
        mime_type: file.type,
        size_bytes: file.size,
        uploaded_by: userId,
        file_data: base64Data, // Store the actual file data
        file_hash: fileHash
      })
    });

    if (!response.ok) {
      const error = await response.json();
      progressDiv.style.display = 'none';
      throw new Error(error.error || 'Failed to save attachment');
    }

    progressDiv.innerHTML = '<span style="color:#27ae60">✓ Upload complete!</span>';
    setTimeout(() => { progressDiv.style.display = 'none'; }, 2000);
    
    return await response.json();
  }

  async function loadAttachments() {
    const viewer = getCurrentUser() || {};
    const userId = viewer.user_id || viewer.uid || viewer.id || '';
    
    const response = await fetch(API + '/api/attachments/by-task/' + encodeURIComponent(taskId), {
      headers: userId ? { 'X-User-Id': userId } : {}
    });

    const attachmentsList = document.getElementById('attachmentsList');
    
    if (!response.ok) {
      attachmentsList.innerHTML = '<div style="padding:10px;color:red">Failed to load attachments</div>';
      return;
    }

    const attachments = await response.json();
    
    if (!attachments || attachments.length === 0) {
      attachmentsList.innerHTML = '<div style="padding:10px;color:#666">No attachments yet</div>';
      return;
    }

    attachmentsList.innerHTML = '';
    
    for (const att of attachments) {
      const div = document.createElement('div');
      div.style.cssText = 'display:flex;align-items:center;gap:12px;padding:12px;margin:8px 0;background:#fff;border:1px solid #ddd;border-radius:6px';
      
      // File icon based on type
      const icon = getFileIcon(att.mime_type);
      const iconSpan = document.createElement('span');
      iconSpan.style.cssText = 'font-size:24px;flex-shrink:0';
      iconSpan.textContent = icon;
      
      // File info
      const info = document.createElement('div');
      info.style.cssText = 'flex:1;min-width:0';
      const fileName = document.createElement('div');
      fileName.style.cssText = 'font-weight:600;color:#333;word-break:break-word';
      fileName.textContent = att.filename || 'Unnamed';
      
      const meta = document.createElement('div');
      meta.style.cssText = 'font-size:0.85em;color:#666;margin-top:4px';
      const size = formatFileSize(att.size_bytes || 0);
      const date = att.uploaded_at ? new Date(att.uploaded_at).toLocaleString() : 'Unknown';
      meta.textContent = `${size} • ${date}`;
      
      info.appendChild(fileName);
      info.appendChild(meta);
      
      // Actions
      const actions = document.createElement('div');
      actions.style.cssText = 'display:flex;gap:8px;flex-shrink:0';
      
      // Download button
      const downloadBtn = document.createElement('button');
      downloadBtn.textContent = 'Download';
      downloadBtn.style.cssText = 'padding:6px 12px;background:#3498db;color:white;border:none;border-radius:4px;cursor:pointer;font-size:0.85em';
      downloadBtn.addEventListener('click', async () => {
        try {
          downloadBtn.disabled = true;
          downloadBtn.textContent = 'Loading...';
          
          console.log('Downloading attachment:', att.attachment_id);
          
          // File data is stored in the attachment document itself
          if (att.file_data) {
            // Create download link from Base64 data
            const a = document.createElement('a');
            a.href = att.file_data;
            a.download = att.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            downloadBtn.disabled = false;
            downloadBtn.textContent = 'Download';
          } else {
            throw new Error('File data not found. File may have been corrupted.');
          }
        } catch (error) {
          console.error('Download error:', error);
          downloadBtn.disabled = false;
          downloadBtn.textContent = 'Download';
          alert('Failed to download file: ' + error.message);
        }
      });
      
      // Delete button (only for uploader)
      if (userId && att.uploaded_by === userId) {
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.style.cssText = 'padding:6px 12px;background:#e74c3c;color:white;border:none;border-radius:4px;cursor:pointer;font-size:0.85em';
        deleteBtn.addEventListener('click', async () => {
          if (!confirm('Delete this attachment?')) return;
          
          try {
            const response = await fetch(API + '/api/attachments/' + att.attachment_id, {
              method: 'DELETE',
              headers: { 'X-User-Id': userId }
            });
            
            if (!response.ok) {
              const error = await response.json();
              throw new Error(error.error || 'Failed to delete attachment');
            }
            
            await loadAttachments();
          } catch (error) {
            alert('Failed to delete attachment: ' + error.message);
          }
        });
        actions.appendChild(deleteBtn);
      }
      
      actions.appendChild(downloadBtn);
      
      div.appendChild(iconSpan);
      div.appendChild(info);
      div.appendChild(actions);
      attachmentsList.appendChild(div);
    }
  }

  function getFileIcon(mimeType) {
    if (mimeType.startsWith('image/')) return '🖼️';
    if (mimeType === 'application/pdf') return '📄';
    if (mimeType.includes('word')) return '📝';
    if (mimeType.includes('sheet') || mimeType.includes('excel') || mimeType === 'text/csv') return '📊';
    if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return '📊';
    if (mimeType.includes('zip')) return '🗜️';
    if (mimeType === 'text/plain' || mimeType === 'text/markdown') return '📃';
    return '📎';
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

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

    // Load attachments
    await loadAttachments();

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

  // Upload attachment handler
  document.getElementById('uploadBtn')?.addEventListener('click', async function() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
      alert('Please select a file');
      return;
    }

    try {
      await uploadAttachment(file);
      fileInput.value = ''; // Clear input
      await loadAttachments(); // Reload attachments list
    } catch (error) {
      console.error('Upload error:', error);
      alert('Failed to upload file: ' + error.message);
    }
  });

  load();
  