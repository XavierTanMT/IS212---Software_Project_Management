// common.js — shared helpers + navbar + auth-aware fetch
const API_BASE = "http://localhost:5000";

function getCurrentUser(){ try { return JSON.parse(localStorage.getItem("currentUser") || "null"); } catch(e){ return null; } }
function setCurrentUser(u){ localStorage.setItem("currentUser", JSON.stringify(u)); }
function clearCurrentUser(){ localStorage.removeItem("currentUser"); }

function getCurrentProject(){ try { return JSON.parse(localStorage.getItem("currentProject") || "null"); } catch(e){ return null; } }
function setCurrentProject(p){ localStorage.setItem("currentProject", JSON.stringify(p)); }

function requireAuth(){
  const u = getCurrentUser();
  if(!u){ window.location.href = "login.html"; throw new Error("not authed"); }
  return u;
}

function signOut(){ clearCurrentUser(); window.location.href = "login.html"; }
function el(id){ return document.getElementById(id); }

// Patch fetch to add X-User-Id
(function(){
  const _fetch = window.fetch;
  window.fetch = function(resource, init){
    init = init || {};
    init.headers = init.headers || {};
    const u = getCurrentUser();
    if(u && u.user_id){
      // Normalize headers object
      if (init.headers instanceof Headers){
        init.headers.set("X-User-Id", u.user_id);
      } else if (typeof init.headers === "object"){
        init.headers["X-User-Id"] = u.user_id;
      }
    }
    return _fetch(resource, init);
  }
})();

async function buildNavbar(){
  const host = document.getElementById("nav");
  if(!host) return;
  const u = getCurrentUser();
  const p = getCurrentProject();
  host.innerHTML = `
    <div style="display:flex;gap:12px;align-items:center;justify-content:space-between;padding:10px;border-bottom:1px solid #eee">
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <a href="index.html"><strong>TaskMgr</strong></a>
        <a href="dashboard.html">Dashboard</a>
        <a href="projects.html">Projects</a>
        <a href="tasks_list.html">Tasks</a>
        <a href="create_task.html">Create Task</a>
      </div>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12px;color:#333">
        <span>Project: <em>${p ? (p.name || p.project_id || "selected") : "none"}</em></span>
        <span>User: <em>${u ? (u.user_id || u.email || "signed-in") : "guest"}</em></span>
        ${u ? '<button id="logoutBtn">Sign out</button>' : '<a href="login.html">Login</a>'}
      </div>
    </div>
  `;
  const btn = document.getElementById("logoutBtn");
  if(btn) btn.addEventListener("click", signOut);
}
document.addEventListener("DOMContentLoaded", buildNavbar);