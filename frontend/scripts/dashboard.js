try{requireAuth();}catch(e){}


    // Notifications: show tasks due today on login
    async function fetchDueTodayReminders() {
        try {
            // Compute local day's UTC range and send as query params so server can match user's "today"
            const now = new Date();
            const localYear = now.getFullYear();
            const localMonth = now.getMonth(); // 0-based
            const localDate = now.getDate();

            const localStart = new Date(localYear, localMonth, localDate, 0, 0, 0);
            const localEnd = new Date(localYear, localMonth, localDate, 23, 59, 59, 999);
            // Convert local start/end to UTC ISO strings
            const start_iso = localStart.toISOString();
            const end_iso = localEnd.toISOString();

            const url = `${API_BASE}/api/notifications/due-today?start_iso=${encodeURIComponent(start_iso)}&end_iso=${encodeURIComponent(end_iso)}`;
            console.debug('Reminder request url:', url, 'start_iso', start_iso, 'end_iso', end_iso);
            const res = await fetch(url);
            console.debug('Reminder response status:', res.status);
            if (!res.ok) {
                console.warn('Reminder fetch returned non-OK', res.status);
                return null;
            }
            const payload = await res.json();
            console.debug('Reminder payload:', payload);
            return payload;
        } catch (e) {
            console.warn('Failed to fetch due-today reminders', e);
            return null;
        }
    }

    function renderReminderBanner(data) {
        const container = document.getElementById('reminderBannerContainer');
        if (!container) return;

        const hideKey = 'hideReminderUntil';
        const hideUntil = sessionStorage.getItem(hideKey);
        const today = new Date().toISOString().slice(0,10);

        // If user hid reminders for today, show a floating toggle button so they can unhide
        if (hideUntil === today) {
            container.innerHTML = '';
            showFloatingReminderToggle();
            return;
        }

        if (!data || !data.count || data.count === 0) {
            // No reminders to show — ensure floating toggle is removed
            removeFloatingReminderToggle();
            container.innerHTML = '';
            return;
        }

        // We have reminders — ensure floating toggle is hidden
        removeFloatingReminderToggle();

        const tasks = data.tasks || [];
        const plural = tasks.length > 1 ? 's' : '';
        let itemsHtml = '';
        for (const t of tasks.slice(0,5)) {
            itemsHtml += `<div style="padding:6px 0;border-bottom:1px dashed rgba(0,0,0,0.06)">${escapeHtml(t.title || 'Untitled')} — due ${escapeHtml(t.due_date || '')}</div>`;
        }

        const more = tasks.length > 5 ? `<div style="padding:6px 0;color:#666">And ${tasks.length-5} more...</div>` : '';

        container.innerHTML = `
            <div style="background:#fff3cd;border:1px solid #ffeeba;padding:12px 16px;border-radius:6px;margin:12px 0;display:flex;align-items:flex-start;gap:12px">
                <div style="font-size:1.5rem">🔔</div>
                <div style="flex:1">
                    <div style="font-weight:600;margin-bottom:6px">You have ${tasks.length} reminder${plural} due today</div>
                    <div style="max-height:120px;overflow:auto">${itemsHtml}${more}</div>
                    <div style="margin-top:8px;display:flex;gap:8px;align-items:center">
                        <button id="dismissReminderBtn" style="background:#fff;border:1px solid #ddd;padding:6px 10px;border-radius:4px;cursor:pointer">Dismiss for today</button>
                        <button id="viewAllRemindersBtn" style="background:#667eea;color:#fff;border:none;padding:6px 10px;border-radius:4px;cursor:pointer">View reminders</button>
                    </div>
                </div>
            </div>
        `;

        const dismissBtn = document.getElementById('dismissReminderBtn');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', () => {
                sessionStorage.setItem(hideKey, today);
                container.innerHTML = '';
                showFloatingReminderToggle();
            });
        }

        const viewAllBtn = document.getElementById('viewAllRemindersBtn');
        if (viewAllBtn) {
            viewAllBtn.addEventListener('click', () => {
                // navigate to notifications or dashboard timeline if available
                try { window.toggleView && window.toggleView('timeline'); } catch(e) {}
            });
        }
    }

    function showFloatingReminderToggle() {
        const id = 'showReminderBtn';
        if (document.getElementById(id)) return; // already present
        const btn = document.createElement('button');
        btn.id = id;
        btn.title = "Show today's reminders";
        btn.innerHTML = '🔔';
        btn.addEventListener('click', async () => {
            // Unhide for today
            sessionStorage.removeItem('hideReminderUntil');
            // Remove floating toggle
            removeFloatingReminderToggle();
            // Re-fetch reminders and render banner
            try {
                const data = await fetchDueTodayReminders();
                renderReminderBanner(data);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            } catch (e) { console.warn('Failed to refetch reminders', e); }
        });
        const header = document.querySelector('.header');
        const userInfo = header ? header.querySelector('.user-info') : null;
        if (userInfo) {
            const avatar = userInfo.querySelector('.user-avatar');
            if (avatar && avatar.parentNode) {
                avatar.parentNode.insertBefore(btn, avatar);
            } else {
                userInfo.appendChild(btn);
            }
        } else if (header) {
            header.appendChild(btn);
        } else {
            document.body.appendChild(btn);
        }
    }

    function removeFloatingReminderToggle() {
        const el = document.getElementById('showReminderBtn');
        if (el) el.remove();
    }

    function escapeHtml(str){
        if(!str) return '';
        return String(str).replace(/[&<>"'`]/g, function(s){
            return ({'&':'&amp;','<':'&lt;','>':'&gt;', '"':'&quot;',"'":'&#39;', '`':'&#96;'})[s];
        });
    }

    // Initialize reminders when this fragment is ready. If the fragment is injected
    // after the page's DOMContentLoaded event, call init immediately instead of
    // waiting for the event that already fired.
    async function __initReminderBanner() {
        try {
            // Ensure user is authenticated (requireAuth is safe to call)
            try { requireAuth(); } catch(e){ return; }
            const data = await fetchDueTodayReminders();
            renderReminderBanner(data);
        } catch (e) {
            console.warn('Reminder init failed', e);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', __initReminderBanner);
    } else {
        // DOM already ready (fragment likely injected after load) — run init now
        __initReminderBanner();
    }
    


// API_BASE is already defined in firebase-auth.js
// Using shared getCurrentUser from common.js
// Using shared setCurrentUser from common.js

// Notifications (reminder banner + helpers) moved to frontend/notifications.html and are loaded dynamically

// -----------------------------------------------------------------------------

// Timeline View Functions - Defined early so onclick handlers can use them
// Make variables global so they're accessible across script blocks
window.currentView = 'grid';
window.timelineData = null;
window.refreshInterval = null;

window.toggleView = async function(viewType) {
    window.currentView = viewType;
    
    // Update toggle buttons
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    const targetBtn = document.querySelector(`[data-view="${viewType}"]`);
    if (targetBtn) targetBtn.classList.add('active');
    
    // Show/hide containers
    const gridView = document.getElementById('gridView');
    const timelineView = document.getElementById('timelineView');
    if (gridView) gridView.classList.toggle('hidden', viewType !== 'grid');
    if (timelineView) timelineView.classList.toggle('hidden', viewType !== 'timeline');
    
    if (viewType === 'timeline') {
        await window.loadTimelineView();
        window.setupAutoRefresh();
    } else {
        window.clearAutoRefresh();
    }
};

// First loadTimelineView function removed - using the full implementation below

// Helper function for showing empty states
function showEmptyState(selector, message) {
    const element = document.querySelector(selector);
    if (element) {
        element.innerHTML = `<div style="padding: 2rem; text-align: center; color: #666;">${message}</div>`;
    }
}

window.renderTimelineView = function(data) {
    // This function will be fully defined later in the file
    // For now, just a placeholder to prevent errors
    console.log('Rendering timeline view...', data);
};

window.setupAutoRefresh = function() {
    window.clearAutoRefresh();
    window.refreshInterval = setInterval(() => {
        if (window.currentView === 'timeline') {
            window.loadTimelineView();
        }
    }, 30000); // 30 seconds
};

window.clearAutoRefresh = function() {
    if (window.refreshInterval) {
        clearInterval(window.refreshInterval);
        window.refreshInterval = null;
    }
};

// Make functions accessible without window. prefix for onclick handlers
const toggleView = window.toggleView;
const loadTimelineView = window.loadTimelineView;
const setupAutoRefresh = window.setupAutoRefresh;
const clearAutoRefresh = window.clearAutoRefresh;



        const API_BASE_URL = 'http://localhost:5000';
        let currentUser = null;

        // Check authentication and load dashboard
        window.addEventListener('load', async () => {
            // Check if user is logged in
            const userData = sessionStorage.getItem('currentUser');
            if (!userData) {
                window.location.href = 'login.html';
                return;
            }

            currentUser = JSON.parse(userData);
            initializeDashboard();
            await loadDashboardData();
        });

        function initializeDashboard() {
            // Update header with user info (only if elements exist)
            const welcomeMsg = document.getElementById('welcomeMessage');
            const userName = document.getElementById('userName');
            const userEmail = document.getElementById('userEmail');
            const userAvatar = document.getElementById('userAvatar');
            
            if (welcomeMsg) welcomeMsg.textContent = `Welcome, ${currentUser.name}!`;
            if (userName) userName.textContent = currentUser.name;
            if (userEmail) userEmail.textContent = currentUser.email;
            if (userAvatar) userAvatar.textContent = currentUser.name.charAt(0).toUpperCase();
            document.title = `Dashboard - ${currentUser.name}`;

            // Fetch and show role chip, and toggle manager-only UI
            showRoleIndicators(currentUser).catch(()=>{});
        }

        
async function loadDashboardData() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/users/${currentUser.user_id}/dashboard`);
        let dashboardData = null;
        try { dashboardData = await response.json(); } catch(e){ dashboardData = null; }
        if (!response.ok || !dashboardData) {
            renderDashboard({
                statistics: { total_created: 0, total_assigned: 0, status_breakdown: {}, priority_breakdown: {}, overdue_count: 0 },
                recent_created_tasks: [], recent_assigned_tasks: []
            });
            return;
        }
        renderDashboard(dashboardData);
    } catch (error) {
        console.error('Dashboard load failed:', error);
        renderDashboard({
            statistics: { total_created: 0, total_assigned: 0, status_breakdown: {}, priority_breakdown: {}, overdue_count: 0 },
            recent_created_tasks: [], recent_assigned_tasks: []
        });
    }
}

    function renderDashboard(data) {
        data = data || {};
        const stats = data.statistics || { total_created: 0, total_assigned: 0, status_breakdown: {}, priority_breakdown: {}, overdue_count: 0 };

        // Update statistics cards
        const createdEl = document.getElementById('createdCount');
        const assignedEl = document.getElementById('assignedCount');
        const completedEl = document.getElementById('completedCount');
        const overdueEl = document.getElementById('overdueCount');
        if (createdEl) createdEl.textContent = stats.total_created || 0;
        if (assignedEl) assignedEl.textContent = stats.total_assigned || 0;
        if (completedEl) completedEl.textContent = (stats.status_breakdown && stats.status_breakdown['Completed']) || 0;
        if (overdueEl) overdueEl.textContent = stats.overdue_count || 0;

        // Render charts and lists
        try { renderStatusChart(stats.status_breakdown || {}); } catch(e) { console.warn('renderStatusChart failed', e); }
        try { renderPriorityChart(stats.priority_breakdown || {}); } catch(e) { console.warn('renderPriorityChart failed', e); }

        try { renderTaskList('createdTasksList', data.recent_created_tasks || [], 'created'); } catch(e) { console.warn('renderTaskList created failed', e); }
        try { renderTaskList('assignedTasksList', data.recent_assigned_tasks || [], 'assigned'); } catch(e) { console.warn('renderTaskList assigned failed', e); }
    }

        function renderStatusChart(statusData) {
            const chartContainer = document.getElementById('statusChart');

            if (!chartContainer) {
                console.warn('statusChart element not found');
                return;
            }

            if (!statusData || Object.keys(statusData).length === 0) {
                chartContainer.innerHTML = '<div class="empty-state">No status data available</div>';
                return;
            }

            const statusColors = {
                'To Do': '#3498db',
                'In Progress': '#f39c12',
                'Completed': '#27ae60',
                'Blocked': '#e74c3c',
                'Review': '#9b59b6'
            };

            const total = Object.values(statusData).reduce((sum, count) => sum + count, 0);

            let chartHTML = '';
            for (const [status, count] of Object.entries(statusData)) {
                if (count > 0) {
                    const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
                    chartHTML += `
                        <div class="chart-item">
                            <div class="chart-label">
                                <div class="chart-dot" style="background: ${statusColors[status] || '#666'}"></div>
                                <span>${status}</span>
                            </div>
                            <div class="chart-value">${count} (${percentage}%)</div>
                        </div>
                    `;
                }
            }

            chartContainer.innerHTML = chartHTML || '<div class="empty-state">No status data</div>';
        }

        function renderPriorityChart(priorityData) {
            const chartContainer = document.getElementById('priorityChart');

            if (Object.keys(priorityData).length === 0) {
                chartContainer.innerHTML = '<div class="empty-state">No priority data available</div>';
                return;
            }

            const priorityColors = {
                'High': '#e74c3c',
                'Medium': '#f39c12',
                'Low': '#27ae60'
            };

            const total = Object.values(priorityData).reduce((sum, count) => sum + count, 0);

            let chartHTML = '';
            for (const [priority, count] of Object.entries(priorityData)) {
                if (count > 0) {
                    const percentage = total > 0 ? Math.round((count / total) * 100) : 0;
                    chartHTML += `
                        <div class="chart-item">
                            <div class="chart-label">
                                <div class="chart-dot" style="background: ${priorityColors[priority] || '#666'}"></div>
                                <span>${priority}</span>
                            </div>
                            <div class="chart-value">${count} (${percentage}%)</div>
                        </div>
                    `;
                }
            }

            chartContainer.innerHTML = chartHTML || '<div class="empty-state">No priority data</div>';
        }

        // Replace the existing renderTaskList function with this updated version
        function renderTaskList(containerId, tasks, type) {
            const container = document.getElementById(containerId);

            if (!tasks || tasks.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📝</div>
                        <div>No ${type} tasks yet</div>
                    </div>
                `;
                return;
            }

            let tasksHTML = '';
            tasks.forEach(task => {
                const statusClass = `status-${task.status.toLowerCase().replace(' ', '-')}`;
                const priorityClass = `priority-${task.priority.toLowerCase()}`;

                // Only show delete button for tasks created by current user and for non-staff roles
                const role = (currentUser && (currentUser.role || '')).toLowerCase();
                const canDeleteRoles = ['manager','director','hr','admin'];
                const showDelete = task.created_by && task.created_by.user_id === currentUser.user_id && canDeleteRoles.includes(role);

                tasksHTML += `
                    <div class="task-item">
                        <div class="task-title">${task.title}</div>
                        <div class="task-meta">
                            <span class="task-status ${statusClass}">${task.status}</span>
                            <span class="priority ${priorityClass}">
                                <span class="priority-dot"></span>
                                ${task.priority}
                            </span>
                            ${task.due_date ? `<span>Due: ${formatDate(task.due_date)}</span>` : ''}
                        </div>
                        <div class="task-actions">
                            ${task.status !== 'Completed' ? `
                                <button class="task-btn btn-complete" onclick="markTaskAsDone('${task.task_id}')" title="Mark as Done">
                                    ✓ Done
                                </button>
                            ` : ''}
                            <button class="task-btn btn-edit" onclick="viewTask('${task.task_id}')" title="Edit Task">
                                ✏️ Edit
                            </button>
                            ${showDelete ? `
                                <button class="task-btn btn-delete" onclick="confirmDeleteTask('${task.task_id}', '${task.title.replace(/'/g, '\\\'')}')" title="Archive Task">
                                    🗑️ Archive
                                </button>
                            ` : ''}
                        </div>
                    </div>
                `;
            });

            container.innerHTML = tasksHTML;
        }

        function formatDate(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = date.getTime() - now.getTime();
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            if (diffDays < 0) {
                return `${Math.abs(diffDays)} days ago`;
            } else if (diffDays === 0) {
                return 'Today';
            } else if (diffDays === 1) {
                return 'Tomorrow';
            } else {
                return `${diffDays} days`;
            }
        }

        function showError(message) {
            const container = document.querySelector('.container');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = message;
            container.insertBefore(errorDiv, container.firstChild);
        }

        // Role indicators
        async function showRoleIndicators(user){
            try{
                const res = await fetch(`${API_BASE_URL}/api/users/${user.user_id}/role`, {
                    headers: { 'X-User-Id': user.user_id }
                });
                const data = await res.json();
                const role = (data && data.role) || 'staff';
                const isManager = ['manager','director','hr'].includes(role);

                // Add role chip
                const nameEl = document.getElementById('userName');
                if (nameEl && !document.getElementById('roleChip')){
                    const chip = document.createElement('span');
                    chip.id = 'roleChip';
                    chip.className = 'role-chip' + (isManager ? ' manager' : '');
                    chip.textContent = role.charAt(0).toUpperCase() + role.slice(1);
                    nameEl.after(chip);
                }

                // Toggle manager-only UI
                document.querySelectorAll('.manager-only').forEach(el => {
                    el.style.display = isManager ? '' : 'none';
                });
            }catch(e){ /* noop */ }
        }

        // Navigation functions
        function logout() {
            // Delegate to shared signOut() which clears session storage and redirects
            if (typeof signOut === 'function') {
                signOut();
            } else {
                // Fallback
                sessionStorage.removeItem('currentUser');
                sessionStorage.removeItem('firebaseToken');
                window.location.href = 'login.html';
            }
        }

        function createNewTask() {
            window.location.href = 'create_task.html';
        }

        function viewTask(taskId) {
            window.location.href = `edit_task.html?task_id=${taskId}`;
        }

        // Mark task as done
        async function markTaskAsDone(taskId) {
            try {
                const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-User-Id': currentUser.user_id
                    },
                    body: JSON.stringify({ status: 'Completed' })
                });

                const result = await response.json();

                if (response.ok) {
                    showSuccessMessage('Task marked as completed!');
                    
                    // If this was a recurring task, show info about next occurrence
                    if (result.next_recurring_task_id) {
                        showSuccessMessage(`Task completed! Next occurrence created.`);
                    }
                    
                    // Refresh dashboard to show updated task
                    await loadDashboardData();
                } else {
                    showErrorMessage(`Failed to complete task: ${result.error || 'Unknown error'}`);
                }
            } catch (error) {
                console.error('Error marking task as done:', error);
                showErrorMessage('Network error. Please check your connection and try again.');
            }
        }

        function viewAllCreated() {
            window.location.href = `tasks_list.html`;
        }

        function viewAllAssigned() {
            window.location.href = `tasks_list.html`;
        }

        // Add these functions to your existing JavaScript

        let taskToDelete = null; // Store task info for deletion

        // Show delete confirmation modal
        function confirmDeleteTask(taskId, taskTitle) {
            taskToDelete = { id: taskId, title: taskTitle };
            document.getElementById('deleteMessage').textContent =
                `Are you sure you want to Archive "${taskTitle}"? This action cannot be undone.`;
            document.getElementById('deleteModal').style.display = 'block';
        }

        // Close delete modal
        function closeDeleteModal() {
            document.getElementById('deleteModal').style.display = 'none';
            taskToDelete = null;
        }

        // Execute the deletion
        async function executeDelete() {
            if (!taskToDelete) return;

            const confirmBtn = document.getElementById('confirmDeleteBtn');
            const originalText = confirmBtn.textContent;

            try {
                // Show loading state
                confirmBtn.textContent = 'Archiving...';
                confirmBtn.disabled = true;

                // Call delete API
                const response = await fetch(`${API_BASE_URL}/api/tasks/${taskToDelete.id}`, {
                    method: 'DELETE'
                });

                const result = await response.json();

                if (response.ok) {
                    // Success - show message and refresh dashboard
                    showSuccessMessage(`Task "${taskToDelete.title}" archived successfully!`);
                    closeDeleteModal();

                    // Refresh dashboard data
                    await loadDashboardData();

                } else {
                    // Error from API
                    showErrorMessage(`Failed to archive task: ${result.error}`);
                }

            } catch (error) {
                console.error('Error archiving task:', error);
                showErrorMessage('Network error. Please check your connection and try again.');

            } finally {
                // Reset button state
                confirmBtn.textContent = originalText;
                confirmBtn.disabled = false;
            }
        }

        // Show success message
        function showSuccessMessage(message) {
            const successDiv = document.createElement('div');
            successDiv.className = 'success-message';
            successDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #d4edda;
                color: #155724;
                padding: 1rem 1.5rem;
                border: 1px solid #c3e6cb;
                border-radius: 5px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                z-index: 1001;
                animation: slideInRight 0.3s ease;
            `;
            successDiv.textContent = `✅ ${message}`;

            document.body.appendChild(successDiv);

            // Auto-remove after 3 seconds
            setTimeout(() => {
                successDiv.remove();
            }, 3000);
        }

        // Show error message
        function showErrorMessage(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #f8d7da;
                color: #721c24;
                padding: 1rem 1.5rem;
                border: 1px solid #f5c6cb;
                border-radius: 5px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                z-index: 1001;
                animation: slideInRight 0.3s ease;
            `;
            errorDiv.textContent = `❌ ${message}`;

            document.body.appendChild(errorDiv);

            // Auto-remove after 5 seconds
            setTimeout(() => {
                errorDiv.remove();
            }, 5000);
        }

        // Close modal when clicking outside
        window.addEventListener('click', (event) => {
            const modal = document.getElementById('deleteModal');
            if (event.target === modal) {
                closeDeleteModal();
            }
        });

        // Close modal with Escape key
        window.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                closeDeleteModal();
            }
        });

        // Auto-refresh dashboard every 5 minutes
        setInterval(loadDashboardData, 5 * 60 * 1000);
    


        // Using shared getCurrentUser from common.js catch (e) { return null; } }
        // Using shared setCurrentUser from common.js
    


        (function(){
            const current = getCurrentUser();
            if(!current){ window.location.href = "login.html"; return; }
            // Simplified: fetch dashboard data and render via the shared renderer.
            async function load(){
                try{
                    const res = await fetch(`${API_BASE}/api/users/${encodeURIComponent(current.user_id)}/dashboard`);
                    const data = await res.json();
                    if(!res.ok){ alert(data.error || "Failed to load dashboard"); return; }
                    // Use the shared renderDashboard function defined later in this file
                    if (typeof renderDashboard === 'function') {
                        renderDashboard(data);
                    } else {
                        console.warn('renderDashboard not available yet');
                    }
                }catch(e){
                    console.error('Failed to load dashboard:', e);
                }
            }
            load();
        })();
    


    // Timeline View Functions (variables and main functions defined earlier, full implementation here)
// Re-implement toggleView with full logic
window.toggleView = async function(viewType) {
    window.currentView = viewType;
    
    // Update toggle buttons
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-view="${viewType}"]`).classList.add('active');
    
    // Show/hide containers
    document.getElementById('gridView').classList.toggle('hidden', viewType !== 'grid');
    document.getElementById('timelineView').classList.toggle('hidden', viewType !== 'timeline');
    
    if (viewType === 'timeline') {
        await window.loadTimelineView();
        window.setupAutoRefresh();
    } else {
        window.clearAutoRefresh();
    }
};

// Full implementation of loadTimelineView
window.loadTimelineView = async function() {
    const u = getCurrentUser();
    const userId = u && (u.user_id || u.uid);
    const api = API_BASE || '';
    
    if (!userId) {
        showEmptyState('#timelineView', 'You are not signed in.');
        return;
    }
    
    try {
        const res = await fetch(`${api}/api/users/${userId}/dashboard?view_mode=timeline`);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        window.timelineData = data;
        window.renderTimelineView(data);
    } catch (e) {
        console.error('Timeline load failed:', e);
        showEmptyState('#timelineView', 'Failed to load timeline data.');
    }
};

window.renderTimelineView = function(data) {
    const timeline = data.timeline || {};
    const conflicts = data.conflicts || [];
    
    // Generate calendar for current month
    generateCalendar(window.currentYear || new Date().getFullYear(), window.currentMonth || new Date().getMonth());
    
    // Group all tasks by date
    const allTasks = [
        ...(timeline.overdue || []),
        ...(timeline.today || []),
        ...(timeline.this_week || []),
        ...(timeline.future || []),
        ...(timeline.no_due_date || [])
    ];
    
    // Populate calendar with tasks
    populateCalendarWithTasks(allTasks);
    
    // Render no due date tasks
    renderNoDueDateTasks(timeline.no_due_date || []);
    
    // Update counts
    document.getElementById('noDueDateCount').textContent = `(${timeline.no_due_date?.length || 0})`;
    
    // Render conflicts
    renderConflicts(conflicts);
    
    // Populate filter options
    populateTimelineFilterOptions();
};

// Re-implement setupAutoRefresh and clearAutoRefresh with full logic
window.setupAutoRefresh = function() {
    window.clearAutoRefresh();
    window.refreshInterval = setInterval(() => {
        if (window.currentView === 'timeline') {
            window.loadTimelineView();
        }
    }, 30000); // 30 seconds
};

window.clearAutoRefresh = function() {
    if (window.refreshInterval) {
        clearInterval(window.refreshInterval);
        window.refreshInterval = null;
    }
};

function renderConflicts(conflicts) {
    const conflictsSection = document.getElementById('conflictsSection');
    const conflictsList = document.getElementById('conflictsList');
    
    if (conflicts.length === 0) {
        conflictsSection.style.display = 'none';
        return;
    }
    
    conflictsSection.style.display = 'block';
    conflictsList.innerHTML = conflicts.map(conflict => `
        <div class="conflict-item">
            <strong>${conflict.date}</strong>: ${conflict.count} tasks scheduled
            <ul>
                ${conflict.tasks.map(task => `<li>${task.title}</li>`).join('')}
            </ul>
        </div>
    `).join('');
}

function renderTimelineSection(period, tasks) {
    // Convert snake_case to camelCase for element IDs
    // this_week -> thisWeek, no_due_date -> noDueDate
    const elementId = period.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
    const container = document.getElementById(`${elementId}Tasks`);
    console.log(`Rendering ${period}: elementId=${elementId}Tasks, container=`, container, 'tasks=', tasks);
    
    if (!container) {
        console.warn(`Container not found for period: ${period} (looking for ${elementId}Tasks)`);
        return;
    }
    
    if (tasks.length === 0) {
        container.innerHTML = '<div style="padding: 1rem; color: #666; text-align: center;">No tasks</div>';
        return;
    }
    
    const html = tasks.map(task => createTaskCard(task)).join('');
    console.log(`Generated HTML for ${period}:`, html);
    container.innerHTML = html;
}

function createTaskCard(task) {
    const u = getCurrentUser();
    const userId = u && (u.user_id || u.uid);
    const canEdit = userId === task.created_by?.user_id || userId === task.assigned_to?.user_id;
    const priorityClass = getPriorityClass(task.priority);
    
    return `
        <div class="timeline-task-card ${canEdit ? '' : 'locked'}" 
             data-task-id="${task.task_id}" 
             draggable="${canEdit ? 'true' : 'false'}"
             title="${canEdit ? 'Drag to reschedule' : 'Only creator or assignee can reschedule'}">
            <div class="task-title">${task.title}</div>
            <div class="task-meta">
                <div>Status: ${task.status}</div>
                <div>Priority: <span class="task-priority ${priorityClass}">${task.priority}</span></div>
                ${task.due_date ? `<div>Due: ${formatDate(task.due_date)}</div>` : ''}
                ${task.project_id ? `<div>Project: ${task.project_id}</div>` : ''}
            </div>
        </div>
    `;
}

function getPriorityClass(priority) {
    const p = priority?.toLowerCase() || 'medium';
    if (p.includes('high')) return 'priority-high';
    if (p.includes('low')) return 'priority-low';
    return 'priority-medium';
}

function formatDate(dateStr) {
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString();
    } catch {
        return dateStr;
    }
}

function initializeDragDrop() {
    // Make calendar date cells droppable
    const calendarCells = document.querySelectorAll('.calendar-date');
    console.log('Initializing drag and drop for', calendarCells.length, 'calendar cells');
    
    calendarCells.forEach(cell => {
        cell.addEventListener('dragover', handleDragOver);
        cell.addEventListener('dragleave', handleDragLeave);
        cell.addEventListener('drop', handleDrop);
    });
    
    // Make no due date section droppable
    const noDueDateSection = document.querySelector('.no-due-date-section');
    if (noDueDateSection) {
        noDueDateSection.addEventListener('dragover', handleDragOver);
        noDueDateSection.addEventListener('dragleave', handleDragLeave);
        noDueDateSection.addEventListener('drop', handleDrop);
    }
    
    // Make task cards draggable (both timeline and calendar mini tasks)
    const taskCards = document.querySelectorAll('.timeline-task-card, .calendar-task-mini');
    console.log('Initializing drag and drop for', taskCards.length, 'task cards');
    
    taskCards.forEach(card => {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
    });
}

function handleDragStart(e) {
    e.dataTransfer.setData('text/plain', e.target.dataset.taskId);
    e.target.classList.add('dragging');
    
    // Add visual feedback to all drop zones
    document.querySelectorAll('.calendar-date').forEach(cell => {
        cell.classList.add('drag-over');
    });
    
    const noDueDateSection = document.querySelector('.no-due-date-section');
    if (noDueDateSection) {
        noDueDateSection.classList.add('drag-over');
    }
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    
    // Remove visual feedback from all drop zones
    document.querySelectorAll('.calendar-date').forEach(cell => {
        cell.classList.remove('drag-over');
    });
    
    const noDueDateSection = document.querySelector('.no-due-date-section');
    if (noDueDateSection) {
        noDueDateSection.classList.remove('drag-over');
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    // Add visual feedback to current drop zone
    e.currentTarget.classList.add('drag-over');
    console.log('Drag over calendar cell:', e.currentTarget.dataset.date);
}

function handleDragLeave(e) {
    // Remove visual feedback when leaving drop zone
    e.currentTarget.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    const taskId = e.dataTransfer.getData('text/plain');
    const target = e.currentTarget;
    
    console.log('Drop event:', taskId, 'onto', target.classList.toString());
    
    // Show loading state on the dragged task
    const draggedTask = document.querySelector(`[data-task-id="${taskId}"]`);
    if (draggedTask) {
        draggedTask.classList.add('updating');
    }
    
    // Check if dropped on calendar date cell
    if (target.classList.contains('calendar-date')) {
        const dateStr = target.dataset.date;
        console.log('Dropped on calendar date:', dateStr);
        if (dateStr) {
            updateTaskDueDate(taskId, dateStr);
        }
    }
    // Check if dropped on no due date section
    else if (target.classList.contains('no-due-date-section')) {
        console.log('Dropped on no due date section');
        updateTaskDueDate(taskId, null);
    }
}

function calculateDateFromPeriod(period) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    switch (period) {
        case 'overdue':
            return new Date(today.getTime() - 24 * 60 * 60 * 1000).toISOString();
        case 'today':
            return today.toISOString();
        case 'this_week':
            return new Date(today.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString();
        case 'future':
            return new Date(today.getTime() + 14 * 24 * 60 * 60 * 1000).toISOString();
        default:
            return today.toISOString();
    }
}

// Calendar generation functions
function generateCalendar(year, month) {
    window.currentYear = year;
    window.currentMonth = month;
    
    const calendarGrid = document.getElementById('calendarGrid');
    const calendarTitle = document.getElementById('calendarTitle');
    
    // Update title
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
    calendarTitle.textContent = `${monthNames[month]} ${year}`;
    
    // Clear existing calendar
    calendarGrid.innerHTML = '';
    
    // Add day headers
    const dayHeaders = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    dayHeaders.forEach(day => {
        const header = document.createElement('div');
        header.className = 'calendar-day-header';
        header.textContent = day;
        calendarGrid.appendChild(header);
    });
    
    // Get first day of month and number of days
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startDayOfWeek = firstDay.getDay();
    
    // Add empty cells for days before the first day of the month
    for (let i = 0; i < startDayOfWeek; i++) {
        const prevMonth = new Date(year, month, 0);
        const dayNum = prevMonth.getDate() - startDayOfWeek + i + 1;
        const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
        
        const cell = createCalendarDateCell(dayNum, dateStr, true);
        calendarGrid.appendChild(cell);
    }
    
    // Add days of the current month
    const today = new Date();
    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const isToday = year === today.getFullYear() && month === today.getMonth() && day === today.getDate();
        
        const cell = createCalendarDateCell(day, dateStr, false, isToday);
        calendarGrid.appendChild(cell);
    }
    
    // Add empty cells for days after the last day of the month
    const remainingCells = 42 - (startDayOfWeek + daysInMonth); // 42 = 6 weeks * 7 days
    for (let day = 1; day <= remainingCells; day++) {
        const nextMonth = new Date(year, month + 1, day);
        const dateStr = `${nextMonth.getFullYear()}-${String(nextMonth.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        
        const cell = createCalendarDateCell(day, dateStr, true);
        calendarGrid.appendChild(cell);
    }
}

function createCalendarDateCell(dayNum, dateStr, isOtherMonth, isToday = false) {
    const cell = document.createElement('div');
    cell.className = 'calendar-date';
    cell.dataset.date = dateStr;
    
    if (isOtherMonth) {
        cell.classList.add('other-month');
    }
    if (isToday) {
        cell.classList.add('today');
    }
    
    const dayElement = document.createElement('div');
    dayElement.className = 'calendar-date-number';
    dayElement.textContent = dayNum;
    cell.appendChild(dayElement);
    
    return cell;
}

function populateCalendarWithTasks(allTasks) {
    // Group tasks by date
    const tasksByDate = {};
    
    allTasks.forEach(task => {
        const dueDate = task.due_date;
        if (dueDate) {
            // Extract date part from ISO string
            const dateStr = dueDate.split('T')[0];
            if (!tasksByDate[dateStr]) {
                tasksByDate[dateStr] = [];
            }
            tasksByDate[dateStr].push(task);
        }
    });
    
    // Populate calendar cells with tasks
    document.querySelectorAll('.calendar-date').forEach(cell => {
        const dateStr = cell.dataset.date;
        const tasks = tasksByDate[dateStr] || [];
        
        // Clear existing tasks
        const existingTasks = cell.querySelectorAll('.calendar-task-mini');
        existingTasks.forEach(task => task.remove());
        
        // Add task count badge
        const existingBadge = cell.querySelector('.calendar-task-count');
        if (existingBadge) {
            existingBadge.remove();
        }
        
        if (tasks.length > 0) {
            // Add count badge
            const badge = document.createElement('div');
            badge.className = 'calendar-task-count';
            badge.textContent = tasks.length;
            cell.appendChild(badge);
            
            // Add mini task cards (max 3 visible)
            const visibleTasks = tasks.slice(0, 3);
            visibleTasks.forEach(task => {
                const miniTask = document.createElement('div');
                miniTask.className = `calendar-task-mini priority-${task.priority.toLowerCase()}`;
                miniTask.textContent = task.title;
                miniTask.title = `${task.title} - ${task.priority} priority`;
                miniTask.dataset.taskId = task.task_id;
                miniTask.draggable = true;
                miniTask.onclick = () => showTaskDetails(task);
                cell.appendChild(miniTask);
            });
            
            // Show "+X more" if there are more tasks
            if (tasks.length > 3) {
                const moreTasks = document.createElement('div');
                moreTasks.className = 'calendar-task-mini';
                moreTasks.textContent = `+${tasks.length - 3} more`;
                moreTasks.style.background = '#999';
                cell.appendChild(moreTasks);
            }
        }
    });
    
    // Initialize drag and drop for calendar cells after populating
    initializeDragDrop();
}

function renderNoDueDateTasks(tasks) {
    const container = document.getElementById('noDueDateTasks');
    container.innerHTML = '';
    
    if (tasks.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #999; padding: 20px;">No tasks without due dates</div>';
        return;
    }
    
    tasks.forEach(task => {
        const taskCardHtml = createTaskCard(task);
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = taskCardHtml;
        const taskCard = tempDiv.firstElementChild;
        taskCard.draggable = true;
        container.appendChild(taskCard);
    });
}

function navigateMonth(direction) {
    const newDate = new Date(window.currentYear, window.currentMonth + direction, 1);
    generateCalendar(newDate.getFullYear(), newDate.getMonth());
    
    // Re-populate with tasks
    if (window.timelineData) {
        const allTasks = [
            ...(window.timelineData.timeline?.overdue || []),
            ...(window.timelineData.timeline?.today || []),
            ...(window.timelineData.timeline?.this_week || []),
            ...(window.timelineData.timeline?.future || []),
            ...(window.timelineData.timeline?.no_due_date || [])
        ];
        populateCalendarWithTasks(allTasks);
    }
}

async function updateTaskDueDate(taskId, newDate) {
    try {
        console.log('Updating task', taskId, 'to date', newDate);
        
        const u = getCurrentUser();
        const userId = u && (u.user_id || u.uid);
        if (!userId) {
            throw new Error('User not authenticated');
        }
        
        const payload = { due_date: newDate };
        console.log('Sending payload:', payload);
        
        const res = await fetch(`${API_BASE}/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'X-User-Id': userId
            },
            body: JSON.stringify(payload)
        });
        
        console.log('API response status:', res.status);
        
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            console.error('API error:', errorData);
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        
        console.log('Task updated successfully, reloading timeline...');
        
        // Reload timeline view
        await window.loadTimelineView();
    } catch (e) {
        console.error('Failed to update task:', e);
        alert(`Failed to reschedule task: ${e.message}`);
    } finally {
        // Remove loading state
        const draggedTask = document.querySelector(`[data-task-id="${taskId}"]`);
        if (draggedTask) {
            draggedTask.classList.remove('updating');
        }
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', window.clearAutoRefresh);

// Timeline Filtering Functions
let filteredTimelineData = null;

function toggleTimelineFilters() {
    const filtersPanel = document.getElementById('timelineFilters');
    const toggleBtn = document.querySelector('.toggle-filters-btn');
    
    if (filtersPanel.classList.contains('show')) {
        filtersPanel.classList.remove('show');
        toggleBtn.textContent = '🔍 Show Filters';
    } else {
        filtersPanel.classList.add('show');
        toggleBtn.textContent = '🔍 Hide Filters';
        populateTimelineFilterOptions();
    }
}

function populateTimelineFilterOptions() {
    if (!window.timelineData) return;
    
    // Populate project filter
    const projectSelect = document.getElementById('filterProject');
    projectSelect.innerHTML = '<option value="">All Projects</option>';
    const projects = [...new Set(window.timelineData.timeline?.overdue?.concat(
        window.timelineData.timeline?.today || [],
        window.timelineData.timeline?.this_week || [],
        window.timelineData.timeline?.future || [],
        window.timelineData.timeline?.no_due_date || []
    ).filter(task => task.project_id).map(task => task.project_id))];
    
    projects.forEach(projectId => {
        projectSelect.innerHTML += `<option value="${projectId}">${projectId}</option>`;
    });
    
    // Populate category filter (using labels as categories)
    const categorySelect = document.getElementById('filterCategory');
    categorySelect.innerHTML = '<option value="">All Categories</option>';
    const categories = [...new Set(window.timelineData.timeline?.overdue?.concat(
        window.timelineData.timeline?.today || [],
        window.timelineData.timeline?.this_week || [],
        window.timelineData.timeline?.future || [],
        window.timelineData.timeline?.no_due_date || []
    ).flatMap(task => task.labels || []))];
    
    categories.forEach(category => {
        categorySelect.innerHTML += `<option value="${category}">${category}</option>`;
    });
    
    // Populate status filter
    const statusSelect = document.getElementById('filterStatus');
    statusSelect.innerHTML = '<option value="">All Statuses</option>';
    const statuses = [...new Set(window.timelineData.timeline?.overdue?.concat(
        window.timelineData.timeline?.today || [],
        window.timelineData.timeline?.this_week || [],
        window.timelineData.timeline?.future || [],
        window.timelineData.timeline?.no_due_date || []
    ).map(task => task.status))];
    
    statuses.forEach(status => {
        statusSelect.innerHTML += `<option value="${status}">${status}</option>`;
    });
}

function applyTimelineFilters() {
    if (!window.timelineData) return;
    
    const projectFilter = document.getElementById('filterProject').value;
    const categoryFilter = document.getElementById('filterCategory').value;
    const statusFilter = document.getElementById('filterStatus').value;
    
    // Get all tasks from timeline
    const allTasks = [
        ...(window.timelineData.timeline?.overdue || []),
        ...(window.timelineData.timeline?.today || []),
        ...(window.timelineData.timeline?.this_week || []),
        ...(window.timelineData.timeline?.future || []),
        ...(window.timelineData.timeline?.no_due_date || [])
    ];
    
    // Apply filters
    let filteredTasks = allTasks;
    
    if (projectFilter) {
        filteredTasks = filteredTasks.filter(task => task.project_id === projectFilter);
    }
    
    if (categoryFilter) {
        filteredTasks = filteredTasks.filter(task => 
            task.labels && task.labels.includes(categoryFilter)
        );
    }
    
    if (statusFilter) {
        filteredTasks = filteredTasks.filter(task => task.status === statusFilter);
    }
    
    // Group filtered tasks by timeline periods
    const filteredTimeline = groupTasksByTimeline(filteredTasks);
    
    // Update conflict detection for filtered tasks
    const filteredConflicts = detectConflicts(filteredTasks);
    
    // Create filtered timeline data
    filteredTimelineData = {
        ...window.timelineData,
        timeline: filteredTimeline,
        conflicts: filteredConflicts,
        timeline_statistics: {
            total_tasks: filteredTasks.length,
            overdue_count: filteredTimeline.overdue?.length || 0,
            today_count: filteredTimeline.today?.length || 0,
            this_week_count: filteredTimeline.this_week?.length || 0,
            future_count: filteredTimeline.future?.length || 0,
            no_due_date_count: filteredTimeline.no_due_date?.length || 0,
            conflict_count: filteredConflicts.length
        }
    };
    
    // Render filtered calendar
    window.renderTimelineView(filteredTimelineData);
    
    // Save filter state
    sessionStorage.setItem('timelineFilters', JSON.stringify({
        project: projectFilter,
        category: categoryFilter,
        status: statusFilter
    }));
}

function clearTimelineFilters() {
    document.getElementById('filterProject').value = '';
    document.getElementById('filterCategory').value = '';
    document.getElementById('filterStatus').value = '';
    
    // Clear filtered data and render original timeline
    filteredTimelineData = null;
    window.renderTimelineView(window.timelineData);
    
    // Clear saved filter state
    sessionStorage.removeItem('timelineFilters');
}

function groupTasksByTimeline(tasks) {
    const timeline = {
        overdue: [],
        today: [],
        this_week: [],
        future: [],
        no_due_date: []
    };
    
    tasks.forEach(task => {
        const enrichedTask = enrichTaskWithTimelineStatus(task);
        const status = enrichedTask.timeline_status || "no_due_date";
        
        // Skip completed tasks - they shouldn't appear in timeline view
        if (status === "completed") {
            return;
        }
        
        if (status in timeline) {
            timeline[status].push(enrichedTask);
        }
    });
    
    return timeline;
}

function enrichTaskWithTimelineStatus(task) {
    const due_date = task.due_date;
    const status = task.status || "To Do";
    
    // Completed tasks should not appear in timeline categories
    if (status === "Completed") {
        task.timeline_status = "completed";
        task.is_overdue = false;
        task.is_upcoming = false;
        return task;
    }
    
    if (!due_date) {
        task.timeline_status = "no_due_date";
        task.is_overdue = false;
        task.is_upcoming = false;
        return task;
    }
    
    // Calculate days until due more accurately
    // Parse the due date and get just the date part (YYYY-MM-DD)
    let dueDateStr = due_date;
    if (due_date.includes('T')) {
        dueDateStr = due_date.split('T')[0];
    }
    
    // Get today's date as YYYY-MM-DD in LOCAL timezone
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const todayStr = `${year}-${month}-${day}`;
    
    // Parse both dates as local dates (not UTC to avoid timezone shifts)
    const dueParts = dueDateStr.split('-');
    const todayParts = todayStr.split('-');
    const due_dt = new Date(parseInt(dueParts[0]), parseInt(dueParts[1]) - 1, parseInt(dueParts[2]));
    const today_dt = new Date(parseInt(todayParts[0]), parseInt(todayParts[1]) - 1, parseInt(todayParts[2]));
    
    // Calculate difference in days
    const days_until_due = Math.round((due_dt - today_dt) / (1000 * 60 * 60 * 24));
    
    console.log(`Task: ${task.title}, Due: ${dueDateStr}, Today: ${todayStr}, Days: ${days_until_due}`);
    
    if (days_until_due < 0) {
        task.timeline_status = "overdue";
        task.is_overdue = true;
        task.is_upcoming = false;
    } else if (days_until_due === 0) {
        task.timeline_status = "today";
        task.is_overdue = false;
        task.is_upcoming = true;
    } else if (days_until_due >= 1 && days_until_due <= 7) {
        task.timeline_status = "this_week";
        task.is_overdue = false;
        task.is_upcoming = true;
    } else {
        task.timeline_status = "future";
        task.is_overdue = false;
        task.is_upcoming = false;
    }
    
    return task;
}

function detectConflicts(tasks) {
    const dateMap = {};
    const conflicts = [];
    
    tasks.forEach(task => {
        const due_date = task.due_date;
        if (due_date) {
            const date_str = due_date.split('T')[0];
            if (!(date_str in dateMap)) {
                dateMap[date_str] = [];
            }
            dateMap[date_str].push(task);
        }
    });
    
    // Find dates with multiple tasks
    for (const [date_str, tasks_on_date] of Object.entries(dateMap)) {
        if (tasks_on_date.length > 1) {
            conflicts.push({
                date: date_str,
                tasks: tasks_on_date,
                count: tasks_on_date.length
            });
        }
    }
    
    return conflicts;
}

// Load saved filter state on page load
function loadSavedTimelineFilters() {
    const savedFilters = sessionStorage.getItem('timelineFilters');
    if (savedFilters) {
        const filters = JSON.parse(savedFilters);
        document.getElementById('filterProject').value = filters.project || '';
        document.getElementById('filterCategory').value = filters.category || '';
        document.getElementById('filterStatus').value = filters.status || '';
        
        // Apply saved filters if timeline view is active
        if (window.currentView === 'timeline') {
            applyTimelineFilters();
        }
    }
}

