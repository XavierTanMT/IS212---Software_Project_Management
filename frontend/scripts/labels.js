try{requireAuth();}catch(e){}


    const API_BASE = "http://localhost:5000";
    // Using shared getCurrentUser from common.js catch (e) { return null; } }
    // Using shared setCurrentUser from common.js
    function q(s) { return document.querySelector(s); }
    function ce(t) { return document.createElement(t); }
    function fmtDate(d) { try { return new Date(d).toLocaleString(); } catch (e) { return d; } }
  


    async function createLabel(e) {
      e.preventDefault();
      var payload = { name: q("#name").value.trim(), color: q("#color").value.trim() };
      var res = await fetch(API_BASE + "/api/labels", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
      });
      var data = await res.json();
      if (!res.ok) { alert((data && data.error) || "Create failed"); return; }
      q("#createLabelForm").reset();
      load();
    }

    async function load() {
      var res = await fetch(API_BASE + "/api/labels");
      var list = await res.json();
      var host = q("#all"); host.innerHTML = "";
      if (!Array.isArray(list) || !list.length) { host.innerHTML = "<p>No labels</p>"; return; }
      list.forEach(function (l) {
        var chip = document.createElement("span");
        chip.className = "chip";
        chip.textContent = (l.name || "") + " (" + (l.label_id || "") + ")";
        if (l.color) { chip.style.background = l.color; }
        host.appendChild(chip);
      });
    }

    async function assign(kind) {
      var task_id = q("#task_id").value.trim();
      var label_id = q("#label_id").value.trim();
      if (!task_id || !label_id) { alert("Provide task_id and label_id"); return; }
      var url = kind === "assign" ? "/api/labels/assign" : "/api/labels/unassign";
      var res = await fetch(API_BASE + url, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: task_id, label_id: label_id })
      });
      var data = await res.json();
      if (!res.ok) { alert((data && data.error) || (kind + " failed")); return; }
      alert(kind + " ok");
    }

    q("#createLabelForm").addEventListener("submit", createLabel);
    q("#assign").addEventListener("click", function () { assign("assign"); });
    q("#unassign").addEventListener("click", function () { assign("unassign"); });
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
