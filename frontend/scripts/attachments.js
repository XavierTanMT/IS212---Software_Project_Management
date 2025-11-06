try{requireAuth();}catch(e){}


    const API_BASE = "http://localhost:5000";
    // Using shared getCurrentUser from common.js catch (e) { return null; } }
    // Using shared setCurrentUser from common.js
    function q(s) { return document.querySelector(s); }
    function ce(t) { return document.createElement(t); }
    function fmtDate(d) { try { return new Date(d).toLocaleString(); } catch (e) { return d; } }
  


    var params = new URLSearchParams(location.search);
    var task_id = params.get("task_id");
    if (!task_id) { document.body.innerHTML = "<p>Missing ?task_id</p>"; throw new Error("no task_id"); }
    q("#task").innerText = "Task ID: " + task_id;

    async function addAttachment(e) {
      e.preventDefault();
      var payload = {
        task_id: task_id,
        file_name: q("#file_name").value.trim(),
        file_path: q("#file_path").value.trim(),
        uploaded_by: q("#uploaded_by").value.trim() || (getCurrentUser() ? getCurrentUser().user_id : "")
      };
      var res = await fetch(API_BASE + "/api/attachments", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
      });
      var data = await res.json();
      if (!res.ok) { alert((data && data.error) || "Add failed"); return; }
      q("#addForm").reset();
      load();
    }

    async function load() {
      var res = await fetch(API_BASE + "/api/attachments/by-task/" + encodeURIComponent(task_id));
      var list = await res.json();
      var host = q("#list"); host.innerHTML = "";
      if (!Array.isArray(list) || !list.length) { host.innerHTML = "<p>No attachments</p>"; return; }
      list.forEach(function (a) {
        var row = ce("div");
        row.innerHTML = "<strong>" + (a.file_name || "") + "</strong> — " + (a.file_path || "") + "<br/><small>by " + (a.uploaded_by || "") + " • " + fmtDate(a.upload_date) + "</small>";
        host.appendChild(row);
      });
    }

    q("#addForm").addEventListener("submit", addAttachment);
    q("#refresh").addEventListener("click", load);
    load();
  


// --- PATCH: generic empty-state guard --- //
(function(){
  if (window.__genericEmptyPatchApplied) return; window.__genericEmptyPatchApplied = true;
  function afterLoad(){
    document.querySelectorAll('.loading,.spinner').forEach(el=>el.remove());
    const empties = [
      ['#labelsList,.labels-list', 'No labels yet.'],
      ['#attachmentsList,.attachments-list', 'No attachments yet.'],
      ['#commentsList,.comments-list', 'No comments yet.'],
      ['#membersList,.members-list', 'No members yet.'],
    ];
    for (const [sel, text] of empties){
      const host = document.querySelector(sel);
      if (host && (host.children.length === 0 || host.innerHTML.trim() === '')){
        host.innerHTML = `<div style="padding:12px;color:#666">${text}</div>`;
      }
    }
  }
  window.addEventListener('load', ()=> setTimeout(afterLoad, 200));
})();
