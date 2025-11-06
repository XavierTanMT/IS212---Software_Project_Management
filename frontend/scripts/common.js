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

// Sticky navbar at top of every page with role-based navigation
function injectNavbar(){
  // Skip navbar injection if page has skipNavbar flag
  if (window.skipNavbar) {
    return;
  }
  
  if (!document.getElementById("app-navbar-style")){
    const style = document.createElement("style");
    style.id = "app-navbar-style";
    style.textContent = `
      :root { --nav-bg:#fff; --nav-border:#eaeaea; --nav-link:#333; --nav-accent:#667eea; }
      body { margin:0; }
      #app-navbar { position: sticky; top:0; z-index:9999; background:var(--nav-bg); border-bottom:1px solid var(--nav-border); box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
      #app-navbar .row { max-width:100%; margin:0 auto; padding:12px 20px; display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;}
      #app-navbar .links { display:flex; align-items:center; gap:4px; flex-wrap:wrap; flex-shrink: 0; }
      #app-navbar .links a { color:var(--nav-link); text-decoration:none; font-weight:500; padding:8px 12px; border-radius:6px; transition: all 0.2s; font-size:14px; white-space:nowrap; }
      #app-navbar .links a:hover { background:#f5f6fa; color:var(--nav-accent); }
      #app-navbar .links a.active { color:var(--nav-accent); background:#f0f2ff; font-weight:600; }
      #app-navbar .links a.brand { font-weight:700; font-size:16px; color:var(--nav-accent); padding:8px 16px; }
      #app-navbar .links a.brand:hover { background:transparent; }
      #app-navbar .role-badge { padding:4px 8px; border-radius:12px; font-size:11px; font-weight:600; margin-left:4px; white-space:nowrap; }
      #app-navbar .role-admin { background:#dc3545; color:white; }
      #app-navbar .role-manager { background:#667eea; color:white; }
      #app-navbar .role-director { background:#764ba2; color:white; }
      #app-navbar .role-hr { background:#f093fb; color:white; }
      #app-navbar .role-staff { background:#a8edea; color:#333; }
      #app-navbar .right { display:flex; align-items:center; gap:12px; font-size:13px; color:#444; flex-wrap:wrap; }
      #app-navbar .user-info { display:flex; align-items:center; gap:8px; padding:6px 12px; background:#f8f9fa; border-radius:6px; white-space:nowrap; max-width:300px; overflow:hidden; text-overflow:ellipsis; }
      #app-navbar button { padding:8px 14px; border-radius:6px; border:1px solid var(--nav-border); background:#fff; cursor:pointer; font-weight:500; transition: all 0.2s; white-space:nowrap; }
      #app-navbar button:hover { background:#667eea; color:white; border-color:#667eea; }
      #app-navbar .project-info { display:flex; align-items:center; gap:6px; padding:6px 10px; background:#fff3cd; border-radius:6px; font-size:12px; white-space:nowrap; }
      #app-navbar .project-info button { padding:4px 8px; font-size:11px; margin:0; }
      .with-navbar { padding-top: 4px; }
      
      /* Responsive adjustments */
      @media (max-width: 768px) {
        #app-navbar .row { padding: 8px 12px; }
        #app-navbar .links a { padding: 6px 8px; font-size: 13px; }
        #app-navbar .links a.brand { font-size: 14px; padding: 6px 12px; }
        #app-navbar .user-info { max-width: 200px; font-size: 12px; }
      }
    `;
    document.head.appendChild(style);
  }
  
  if (!document.getElementById("app-navbar")){
    const wrap = document.createElement("header");
    wrap.id = "app-navbar";
    document.body.insertAdjacentElement("afterbegin", wrap);
    document.body.classList.add("with-navbar");
  }

  const u = getCurrentUser();
  const p = getCurrentProject();
  const userRole = (u?.role || 'staff').toLowerCase();
  
  // Build navigation links based on role
  // Logo always goes to dashboard
  let navLinks = '';
  
  if (u) {
    const dashboardUrl = getRoleDashboardUrl(userRole);
    navLinks += `<a href="${dashboardUrl}" class="brand">📋 TaskMgr</a>`;
    
    // Role-based dashboard links
    if (userRole === 'staff') {
      // Staff: Only Dashboard link
      navLinks += `<a href="dashboard.html" data-route="dashboard.html">Dashboard</a>`;
    } else if (['manager', 'director', 'hr'].includes(userRole)) {
      // Manager/Director/HR: Dashboard + Manager Dashboard
      navLinks += `<a href="dashboard.html" data-route="dashboard.html">Dashboard</a>`;
      navLinks += `<a href="manager_dashboard.html" data-route="manager_dashboard.html">Manager Dashboard</a>`;
    } else if (userRole === 'admin') {
      // Admin: Dashboard + Manager Dashboard + Admin Dashboard
      navLinks += `<a href="dashboard.html" data-route="dashboard.html">Dashboard</a>`;
      navLinks += `<a href="manager_dashboard.html" data-route="manager_dashboard.html">Manager Dashboard</a>`;
      navLinks += `<a href="admin_dashboard.html" data-route="admin_dashboard.html">Admin Dashboard</a>`;
    }
    
    // Common links for all authenticated users
    navLinks += `<a href="projects.html" data-route="projects.html">Projects</a>`;
    navLinks += `<a href="tasks_list.html" data-route="tasks_list.html">Tasks</a>`;
    navLinks += `<a href="create_task.html" data-route="create_task.html">Create Task</a>`;
  } else {
    // Not logged in - just show brand linking to index
    navLinks += `<a href="index.html" class="brand">📋 TaskMgr</a>`;
  }
  
  // Build user info section
  let userInfo = '';
  if (u) {
    const displayName = u.email || u.name || 'User';
    const roleClass = `role-${userRole}`;
    const roleName = userRole.charAt(0).toUpperCase() + userRole.slice(1);
    userInfo = `
      <div class="user-info">
        <span>${displayName}</span>
        <span class="role-badge ${roleClass}">${roleName}</span>
      </div>
    `;
  }
  
  // Build project info section
  let projectInfo = '';
  if (p) {
    projectInfo = `
      <div class="project-info">
        <span>📁 ${p.name || 'Project Selected'}</span>
        <button id="clearProjectBtn">Clear</button>
      </div>
    `;
  }
  
  // Build auth buttons
  let authButtons = '';
  if (u) {
    authButtons = `<button id="logoutBtn">Sign Out</button>`;
  } else {
    authButtons = `<a href="login.html" style="padding:8px 14px; border-radius:6px; background:#667eea; color:white; text-decoration:none; font-weight:500;">Login</a>`;
  }
  
  // Inject complete navbar
  document.getElementById("app-navbar").innerHTML = `
    <div class="row">
      <div class="links">${navLinks}</div>
      <div class="right">
        ${projectInfo}
        ${userInfo}
        ${authButtons}
      </div>
    </div>
  `;

  // Highlight active page
  const current = (location.pathname.split("/").pop() || "").toLowerCase();
  document.querySelectorAll('#app-navbar .links a[data-route]').forEach(a => {
    a.classList.toggle('active', a.getAttribute('data-route').toLowerCase() === current);
  });

  // Bind event handlers
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.onclick = signOut;
  }
  
  const clearProjectBtn = document.getElementById('clearProjectBtn');
  if (clearProjectBtn) {
    clearProjectBtn.onclick = function(){ 
      clearCurrentProject(); 
      window.location.reload(); 
    };
  }
}

// Helper function to get role-based dashboard URL
function getRoleDashboardUrl(role) {
  const dashboards = {
    'admin': 'admin_dashboard.html',
    'manager': 'manager_dashboard.html',
    'director': 'manager_dashboard.html',
    'hr': 'manager_dashboard.html',
    'staff': 'dashboard.html'
  };
  return dashboards[role] || 'dashboard.html';
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
