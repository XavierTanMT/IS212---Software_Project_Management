
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



    // Immediately check authentication and redirect
    (function() {
      // Get current user from session
      const user = getCurrentUser();
      
      if (!user) {
        // Not logged in - redirect to login
        console.log('No user session found, redirecting to login');
        window.location.replace('login.html');
        return;
      }
      
      // User is logged in - redirect based on role
      console.log('User authenticated:', user.email, '| Role:', user.role);
      
      // Use the role-based redirect function from common.js
      if (typeof redirectToRoleDashboard === 'function') {
        redirectToRoleDashboard();
      } else {
        // Fallback if common.js doesn't have the function
        const role = user.role;
        
        if (role === 'admin' || role === 'hr') {
          window.location.replace('admin_dashboard.html');
        } else if (role === 'manager' || role === 'director') {
          window.location.replace('manager_dashboard.html');
        } else {
          // Default to staff dashboard
          window.location.replace('dashboard.html');
        }
      }
    })();
  