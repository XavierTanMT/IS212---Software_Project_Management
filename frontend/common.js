// common.js — shared helpers + global sticky navbar + auth-aware fetch
const API_BASE = "http://localhost:5000";

// Firebase Auth - Use sessionStorage for better security
function getCurrentUser(){ try { return JSON.parse(sessionStorage.getItem("currentUser") || "null"); } catch(e){ return null; } }
function setCurrentUser(u){ sessionStorage.setItem("currentUser", JSON.stringify(u)); }
function clearCurrentUser(){ 
  sessionStorage.removeItem("currentUser"); 
  sessionStorage.removeItem("firebaseToken");
}

function getFirebaseToken(){ return sessionStorage.getItem("firebaseToken"); }
function setFirebaseToken(token){ sessionStorage.setItem("firebaseToken", token); }

function getCurrentProject(){ try { return JSON.parse(sessionStorage.getItem("currentProject") || "null"); } catch(e){ return null; } }
function setCurrentProject(p){ sessionStorage.setItem("currentProject", JSON.stringify(p)); }
function clearCurrentProject(){ sessionStorage.removeItem("currentProject"); }

function requireAuth(){
  const u = getCurrentUser();
  if(!u){ window.location.href = "login.html"; throw new Error("not authed"); }
  return u;
}
function signOut(){ clearCurrentUser(); window.location.href = "login.html"; }
function el(id){ return document.getElementById(id); }

// Patch fetch to add Authorization and viewer header
;(function(){
  const _fetch = window.fetch;
  window.fetch = function(resource, init){
    init = init || {};
    init.headers = init.headers || {};
    const u = getCurrentUser();
    if (u && u.idToken){
      if (init.headers instanceof Headers){
        init.headers.set("Authorization", "Bearer " + u.idToken);
      } else if (typeof init.headers === "object"){
        init.headers["Authorization"] = "Bearer " + u.idToken;
      }
    }
    // Always provide viewer id for backend convenience
    const viewerId = u && (u.user_id || u.uid);
    if (viewerId){
      if (init.headers instanceof Headers){
        if (!init.headers.has("X-User-Id")) init.headers.set("X-User-Id", viewerId);
      } else if (typeof init.headers === "object"){
        if (!init.headers["X-User-Id"]) init.headers["X-User-Id"] = viewerId;
      }
    }
    return _fetch(resource, init);
  }
})();

// Sticky navbar at top of every page
function injectNavbar(){
  if (!document.getElementById("app-navbar-style")){
    const style = document.createElement("style");
    style.id = "app-navbar-style";
    style.textContent = `
      :root { --nav-bg:#fff; --nav-border:#eaeaea; --nav-link:#333; --nav-accent:#667eea; }
      body { margin:0; }
      #app-navbar { position: sticky; top:0; z-index:9999; background:var(--nav-bg); border-bottom:1px solid var(--nav-border); }
      #app-navbar .row { max-width:1100px; margin:0 auto; padding:10px 14px; display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;}
      #app-navbar .links a { color:var(--nav-link); text-decoration:none; font-weight:600; margin-right:12px; }
      #app-navbar .links a.active { color:var(--nav-accent); }
      #app-navbar .right { display:flex; align-items:center; gap:10px; font-size:13px; color:#444; }
      #app-navbar button { padding:6px 10px; border-radius:8px; border:1px solid var(--nav-border); background:#f7f7fb; cursor:pointer; }
      #app-navbar button:hover { background:#eef0ff; border-color:#d7dbff; }
      .with-navbar { padding-top: 4px; }
    `;
    document.head.appendChild(style);
  }
  if (!document.getElementById("app-navbar")){
    const wrap = document.createElement("header");
    wrap.id = "app-navbar";
    wrap.innerHTML = `
      <div class="row">
        <div class="links">
          <a href="index.html"><strong>TaskMgr</strong></a>
          <a href="dashboard.html" data-route="dashboard.html">Dashboard</a>
          <a href="projects.html" data-route="projects.html">Projects</a>
          <a href="tasks_list.html" data-route="tasks_list.html">Tasks</a>
          <a href="create_task.html" data-route="create_task.html">Create Task</a>
        </div>
        <div class="right">
          <span id="navProject"></span>
          <span id="navUser"></span>
          <button id="logoutBtn" style="display:none">Sign out</button>
          <a id="loginLink" href="login.html" style="display:none">Login</a>
        </div>
      </div>
    `;
    document.body.insertAdjacentElement("afterbegin", wrap);
    document.body.classList.add("with-navbar");
  }

  const current = (location.pathname.split("/").pop() || "").toLowerCase();
  document.querySelectorAll('#app-navbar .links a[data-route]').forEach(a => {
    a.classList.toggle('active', a.getAttribute('data-route').toLowerCase() === current);
  });

  const u = getCurrentUser();
  const p = getCurrentProject();
  const navUser = document.getElementById("navUser");
  const navProj = document.getElementById("navProject");
  const logoutBtn = document.getElementById("logoutBtn");
  const loginLink = document.getElementById("loginLink");

 
  navProj.textContent = "";
  if (p) {
    navProj.innerHTML = `<span style="font-size:12px;color:#666">Project selected</span> <button id="clearProjectBtn" style="margin-left:6px;padding:4px 6px;border-radius:6px;border:1px solid #eaeaea;background:#fff;font-size:11px;cursor:pointer">Clear</button>`;
    const btn = document.getElementById('clearProjectBtn');
    if (btn) btn.onclick = function(){ clearCurrentProject(); navProj.textContent = ''; window.location.reload(); };
  }

  // Prefer email if present, then name, never show raw uid unless nothing else exists
  let who = "guest";
  if (u){
    who = u.email ? u.email : (u.name ? u.name : "signed-in");
  }
  navUser.textContent = "User: " + who;

  if (u){
    logoutBtn.style.display = "inline-block";
    loginLink.style.display = "none";
    logoutBtn.onclick = signOut;
  } else {
    logoutBtn.style.display = "none";
    loginLink.style.display = "inline-block";
  }
}
document.addEventListener("DOMContentLoaded", injectNavbar);

// UI helpers
function showEmptyState(hostSelector, text){
  try{
    const host = document.querySelector(hostSelector);
    if (!host) return;
    host.innerHTML = `<div style="padding:16px;color:#666">${text}</div>`;
  }catch(e){}
}
function stopLoading(selector){
  try{
    const el = document.querySelector(selector);
    if (el){ el.remove(); }
  }catch(e){}
}
