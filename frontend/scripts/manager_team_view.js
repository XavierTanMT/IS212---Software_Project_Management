
        let currentUser = null;
        let teamData = null;
        let currentTab = 'by-member';

        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {
            currentUser = requireAuth();
            if (!currentUser) {
                window.location.href = 'login.html';
                return;
            }

            // Check if user is manager
            checkManagerRole();

            // Show role chip and toggle manager-only UI decorations
            showRoleIndicators(currentUser).catch(()=>{});

            // Setup tab switching
            setupTabButtons();

            // Setup sort controls
            setupSortControls();

            // Load initial data
            loadTeamTasks();
        });

        function checkManagerRole() {
            fetch(`${API_BASE}/api/users/${currentUser.user_id}/role`, {
                headers: { 'X-User-Id': currentUser.user_id }
            })
            .then(res => res.json())
            .then(data => {
                if (data.role && !['manager', 'director', 'hr'].includes(data.role)) {
                    alert('Access denied. Only managers and above can view this page.');
                    window.location.href = 'dashboard.html';
                }
            })
            .catch(err => {
                console.error('Error checking role:', err);
                alert('Error checking permissions');
            });
        }

        function setupTabButtons() {
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    currentTab = this.dataset.tab;
                    renderTasks();
                });
            });
        }

        function setupSortControls() {
            document.getElementById('sortBy').addEventListener('change', loadTeamTasks);
            document.getElementById('sortOrder').addEventListener('change', loadTeamTasks);
        }

        function loadTeamTasks() {
            const sortBy = document.getElementById('sortBy').value;
            const sortOrder = document.getElementById('sortOrder').value;
            const viewMode = currentTab === 'timeline' ? 'timeline' : 'grid';
            
            fetch(`${API_BASE}/api/manager/team-tasks?sort_by=${sortBy}&sort_order=${sortOrder}&view_mode=${viewMode}`, {
                headers: { 'X-User-Id': currentUser.user_id }
            })
            .then(res => res.json())
            .then(data => {
                teamData = data;
                updateStatistics();
                populateFilterOptions();
                renderTasks();
            })
            .catch(err => {
                console.error('Error loading team tasks:', err);
                document.getElementById('taskGrid').innerHTML = '<div class="loading">Error loading team tasks</div>';
            });
        }

        function updateStatistics() {
            if (!teamData) return;

            document.getElementById('totalTasks').textContent = teamData.statistics.total_tasks;
            document.getElementById('overdueTasks').textContent = teamData.statistics.overdue_count;
            document.getElementById('upcomingTasks').textContent = teamData.statistics.upcoming_count;
            document.getElementById('totalProjects').textContent = teamData.projects.length;
        }

        function renderTasks() {
            if (!teamData) return;

            const taskGrid = document.getElementById('taskGrid');
            const tasks = teamData.team_tasks;

            if (tasks.length === 0) {
                taskGrid.innerHTML = '<div class="loading">No team tasks found</div>';
                return;
            }

            if (currentTab === 'timeline') {
                renderTimelineView();
            } else {
                renderGridView();
            }
        }

        function renderTimelineView() {
            const taskGrid = document.getElementById('taskGrid');
            const timeline = teamData.timeline || {};
            const conflicts = teamData.conflicts || [];
            
            let html = '';
            
            // Render conflicts if any
            if (conflicts.length > 0) {
                html += '<div class="conflicts-section">';
                html += '<div class="conflicts-title">⚠️ Schedule Conflicts</div>';
                conflicts.forEach(conflict => {
                    html += `<div class="conflict-item">`;
                    html += `<strong>${conflict.date}</strong>: ${conflict.count} tasks scheduled`;
                    html += '<ul>';
                    conflict.tasks.forEach(task => {
                        html += `<li>${escapeHtml(task.title)} - ${task.assigned_to ? escapeHtml(task.assigned_to.name) : 'Unassigned'}</li>`;
                    });
                    html += '</ul></div>';
                });
                html += '</div>';
            }
            
            // Render timeline sections
            const sections = [
                { key: 'overdue', title: '🚨 Overdue Tasks', icon: '🚨' },
                { key: 'today', title: '📅 Today', icon: '📅' },
                { key: 'this_week', title: '📆 This Week', icon: '📆' },
                { key: 'future', title: '🔮 Future', icon: '🔮' },
                { key: 'no_due_date', title: '📝 No Due Date', icon: '📝' }
            ];
            
            sections.forEach(section => {
                const tasks = timeline[section.key] || [];
                const count = tasks.length;
                
                html += `<div class="timeline-section" data-period="${section.key}">`;
                html += `<div class="timeline-header ${section.key}">`;
                html += `<span>${section.icon}</span>`;
                html += `<span>${section.title}</span>`;
                html += `<span>(${count})</span>`;
                html += '</div>';
                
                if (tasks.length === 0) {
                    html += '<div style="padding: 1rem; color: #666; text-align: center;">No tasks</div>';
                } else {
                    html += '<div class="timeline-tasks">';
                    tasks.forEach(task => {
                        html += renderTimelineTaskCard(task);
                    });
                    html += '</div>';
                }
                
                html += '</div>';
            });
            
            taskGrid.innerHTML = html;
        }

        function renderGridView() {
            const taskGrid = document.getElementById('taskGrid');
            const tasks = teamData.team_tasks;

            let groupedTasks = {};
            
            if (currentTab === 'by-member') {
                // Group by team member
                tasks.forEach(task => {
                    const memberId = task.member_id;
                    if (!groupedTasks[memberId]) {
                        groupedTasks[memberId] = [];
                    }
                    groupedTasks[memberId].push(task);
                });
            } else if (currentTab === 'by-project') {
                // Group by project
                tasks.forEach(task => {
                    const projectId = task.project_id || 'no-project';
                    if (!groupedTasks[projectId]) {
                        groupedTasks[projectId] = [];
                    }
                    groupedTasks[projectId].push(task);
                });
            } else if (currentTab === 'by-status') {
                // Group by status
                tasks.forEach(task => {
                    const status = task.status;
                    if (!groupedTasks[status]) {
                        groupedTasks[status] = [];
                    }
                    groupedTasks[status].push(task);
                });
            }

            let html = '';
            for (const [groupKey, groupTasks] of Object.entries(groupedTasks)) {
                html += `<div class="task-group">`;
                html += `<h3>${getGroupTitle(groupKey)}</h3>`;
                html += `<div class="task-grid">`;
                
                groupTasks.forEach(task => {
                    html += renderTaskCard(task);
                });
                
                html += `</div></div>`;
            }

            taskGrid.innerHTML = html;
        }

        function renderTimelineTaskCard(task) {
            const statusClass = getTaskStatusClass(task);
            const priorityClass = getPriorityClass(task.priority);
            const visualStatusClass = getVisualStatusClass(task);
            const dueDateText = formatDueDate(task.due_date, task.is_overdue, task.is_upcoming);
            
            return `
                <div class="timeline-task-card" onclick="showTaskDetails('${task.task_id}')">
                    <div class="task-title">
                        <span class="priority-indicator ${priorityClass}"></span>
                        ${escapeHtml(task.title)}
                        <span class="status-badge ${visualStatusClass}">${getVisualStatusText(task)}</span>
                    </div>
                    <div class="task-description">${escapeHtml(task.description.substring(0, 100))}${task.description.length > 100 ? '...' : ''}</div>
                    <div class="task-meta">
                        <div class="meta-item">
                            <span class="meta-label">Assigned to:</span>
                            <span class="meta-value">${task.assigned_to ? escapeHtml(task.assigned_to.name) : 'Unassigned'}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Project:</span>
                            <span class="meta-value">${task.project_id ? getProjectName(task.project_id) : 'No Project'}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Status:</span>
                            <span class="status-badge status-${task.status.toLowerCase().replace(' ', '-')}">${task.status}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Due:</span>
                            <span class="due-date ${task.is_overdue ? 'overdue' : task.is_upcoming ? 'upcoming' : 'on-track'}">${dueDateText}</span>
                        </div>
                        ${task.days_overdue > 0 ? `<div class="meta-item"><span class="meta-label">Days Overdue:</span><span class="meta-value">${task.days_overdue}</span></div>` : ''}
                    </div>
                </div>
            `;
        }

        function getGroupTitle(groupKey) {
            if (currentTab === 'by-member') {
                const member = teamData.team_members.find(m => m.user_id === groupKey);
                return member ? member.name : 'Unknown Member';
            } else if (currentTab === 'by-project') {
                if (groupKey === 'no-project') return 'No Project';
                const project = teamData.projects.find(p => p.project_id === groupKey);
                return project ? project.name : 'Unknown Project';
            } else if (currentTab === 'by-status') {
                return groupKey;
            } else if (currentTab === 'timeline') {
                return groupKey; // This shouldn't be called for timeline view
            }
            return groupKey;
        }

        function renderTaskCard(task) {
            const statusClass = getTaskStatusClass(task);
            const priorityClass = getPriorityClass(task.priority);
            const visualStatusClass = getVisualStatusClass(task);
            const dueDateText = formatDueDate(task.due_date, task.is_overdue, task.is_upcoming);
            
            return `
                <div class="task-card ${statusClass}" onclick="showTaskDetails('${task.task_id}')">
                    <div class="task-header">
                        <div class="task-title">
                            <span class="priority-indicator ${priorityClass}"></span>
                            ${escapeHtml(task.title)}
                            <span class="status-badge ${visualStatusClass}">${getVisualStatusText(task)}</span>
                        </div>
                    </div>
                    <div class="task-description">${escapeHtml(task.description.substring(0, 100))}${task.description.length > 100 ? '...' : ''}</div>
                    <div class="task-meta">
                        <div class="meta-item">
                            <span class="meta-label">Assigned to:</span>
                            <span class="meta-value member-name">${task.assigned_to ? escapeHtml(task.assigned_to.name) : 'Unassigned'}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Project:</span>
                            <span class="meta-value project-name">${task.project_id ? getProjectName(task.project_id) : 'No Project'}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Status:</span>
                            <span class="status-badge status-${task.status.toLowerCase().replace(' ', '-')}">${task.status}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">Due:</span>
                            <span class="due-date ${task.is_overdue ? 'overdue' : task.is_upcoming ? 'upcoming' : 'on-track'}">${dueDateText}</span>
                        </div>
                        ${task.days_overdue > 0 ? `<div class="meta-item"><span class="meta-label">Days Overdue:</span><span class="meta-value">${task.days_overdue}</span></div>` : ''}
                    </div>
                </div>
            `;
        }

        function getTaskStatusClass(task) {
            if (task.is_overdue) return 'overdue';
            if (task.is_upcoming) return 'upcoming';
            if (task.due_date) return 'on-track';
            return 'no-due-date';
        }

        function getPriorityClass(priority) {
            const p = parseInt(priority) || 5;
            if (p >= 8) return 'priority-high';
            if (p <= 3) return 'priority-low';
            return 'priority-medium';
        }

        function getVisualStatusClass(task) {
            const visualStatus = task.visual_status || 'no-due-date';
            return `status-${visualStatus.replace('_', '-')}`;
        }

        function getVisualStatusText(task) {
            const visualStatus = task.visual_status || 'no-due-date';
            switch (visualStatus) {
                case 'critical_overdue':
                    return `Critical (${task.days_overdue}d)`;
                case 'overdue':
                    return `Overdue (${task.days_overdue}d)`;
                case 'upcoming':
                    return `Due Soon (${task.days_until_due}d)`;
                case 'on_track':
                    return 'On Track';
                case 'no_due_date':
                    return 'No Due Date';
                default:
                    return visualStatus.replace('_', ' ');
            }
        }

        function getPriorityColor(priority) {
            const colors = [
                '#95a5a6', // 1 - Very Low
                '#95a5a6', // 2 - Low
                '#95a5a6', // 3 - Low
                '#f39c12', // 4 - Below Medium
                '#f39c12', // 5 - Medium
                '#f39c12', // 6 - Above Medium
                '#e74c3c', // 7 - High
                '#e74c3c', // 8 - High
                '#e74c3c', // 9 - Very High
                '#8e44ad'  // 10 - Critical
            ];
            return colors[Math.max(0, Math.min(9, priority - 1))];
        }

        function formatDueDate(dueDate, isOverdue, isUpcoming) {
            if (!dueDate) return 'No due date';
            
            const date = new Date(dueDate);
            const now = new Date();
            const diffTime = date - now;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            if (isOverdue) {
                return `${Math.abs(diffDays)} days overdue`;
            } else if (isUpcoming) {
                return `${diffDays} days remaining`;
            } else {
                return date.toLocaleDateString();
            }
        }

        function getProjectName(projectId) {
            const project = teamData.projects.find(p => p.project_id === projectId);
            return project ? project.name : 'Unknown Project';
        }

        function showTaskDetails(taskId) {
            const task = teamData.team_tasks.find(t => t.task_id === taskId);
            if (!task) return;

            document.getElementById('modalTitle').textContent = task.title;
            
            const modalBody = document.getElementById('modalBody');
            modalBody.innerHTML = `
                <div class="modal-field">
                    <label>Description:</label>
                    <div class="value">${escapeHtml(task.description)}</div>
                </div>
                <div class="modal-field">
                    <label>Priority:</label>
                    <div class="value">
                        <span class="priority-indicator ${getPriorityClass(task.priority)}"></span>
                        ${task.priority}/10
                    </div>
                </div>
                <div class="modal-field">
                    <label>Status:</label>
                    <div class="value">
                        <span class="status-badge status-${task.status.toLowerCase().replace(' ', '-')}">${task.status}</span>
                        <span class="status-badge ${getVisualStatusClass(task)}">${getVisualStatusText(task)}</span>
                    </div>
                </div>
                <div class="modal-field">
                    <label>Assigned to:</label>
                    <div class="value member-name">${task.assigned_to ? escapeHtml(task.assigned_to.name) : 'Unassigned'}</div>
                </div>
                <div class="modal-field">
                    <label>Project:</label>
                    <div class="value project-name">${task.project_id ? getProjectName(task.project_id) : 'No Project'}</div>
                </div>
                <div class="modal-field">
                    <label>Due Date:</label>
                    <div class="value">${formatDueDate(task.due_date, task.is_overdue, task.is_upcoming)}</div>
                </div>
                ${task.days_overdue > 0 ? `
                <div class="modal-field">
                    <label>Days Overdue:</label>
                    <div class="value" style="color: #dc3545; font-weight: bold;">${task.days_overdue} days</div>
                </div>
                ` : ''}
                <div class="modal-field">
                    <label>Created:</label>
                    <div class="value">${new Date(task.created_at).toLocaleString()}</div>
                </div>
                ${task.labels && task.labels.length > 0 ? `
                <div class="modal-field">
                    <label>Labels:</label>
                    <div class="value">${task.labels.map(label => `<span class="label-badge">${escapeHtml(label)}</span>`).join(' ')}</div>
                </div>
                ` : ''}
            `;

            const modalActions = document.getElementById('modalActions');
            modalActions.innerHTML = `
                <button class="btn btn-secondary" onclick="closeModal()">Close</button>
                <button class="btn btn-primary" onclick="editTask('${task.task_id}')">Edit Task</button>
                <button class="btn btn-warning" onclick="reassignTask('${task.task_id}')">Reassign Task</button>
            `;

            document.getElementById('taskModal').style.display = 'block';
        }

        function editTask(taskId) {
            closeModal();
            window.location.href = `edit_task.html?id=${taskId}`;
        }

        function reassignTask(taskId) {
            const task = teamData.team_tasks.find(t => t.task_id === taskId);
            if (!task) return;

            const currentAssignee = task.assigned_to ? task.assigned_to.user_id : null;
            
            // Create reassignment modal
            const reassignModal = document.createElement('div');
            reassignModal.className = 'modal';
            reassignModal.style.display = 'block';
            reassignModal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2 class="modal-title">Reassign Task</h2>
                        <span class="close" onclick="this.parentElement.parentElement.remove()">&times;</span>
                    </div>
                    <div class="modal-body">
                        <div class="modal-field">
                            <label>Task:</label>
                            <div class="value">${escapeHtml(task.title)}</div>
                        </div>
                        <div class="modal-field">
                            <label>Current Assignee:</label>
                            <div class="value">${task.assigned_to ? escapeHtml(task.assigned_to.name) : 'Unassigned'}</div>
                        </div>
                        <div class="modal-field">
                            <label>Reassign to:</label>
                            <select id="newAssignee" style="width: 100%; padding: 0.5rem; border: 1px solid #ddd; border-radius: 5px;">
                                <option value="">Select team member...</option>
                                ${teamData.team_members.map(member => 
                                    `<option value="${member.user_id}" ${member.user_id === currentAssignee ? 'selected' : ''}>${escapeHtml(member.name)} (${member.role})</option>`
                                ).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="modal-actions">
                        <button class="btn btn-secondary" onclick="this.parentElement.parentElement.remove()">Cancel</button>
                        <button class="btn btn-primary" onclick="confirmReassignment('${taskId}')">Reassign</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(reassignModal);
        }

        function confirmReassignment(taskId) {
            const newAssigneeId = document.getElementById('newAssignee').value;
            if (!newAssigneeId) {
                alert('Please select a team member to reassign to');
                return;
            }

            fetch(`${API_BASE}/api/tasks/${taskId}/reassign`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-Id': currentUser.user_id
                },
                body: JSON.stringify({
                    new_assigned_to_id: newAssigneeId
                })
            })
            .then(res => res.json())
            .then(data => {
                if (res.ok) {
                    alert('Task reassigned successfully');
                    closeModal();
                    document.querySelector('.modal').remove();
                    loadTeamTasks(); // Refresh data
                } else {
                    alert('Error: ' + (data.error || 'Failed to reassign task'));
                }
            })
            .catch(err => {
                console.error('Error reassigning task:', err);
                alert('Error reassigning task');
            });
        }

        function closeModal() {
            document.getElementById('taskModal').style.display = 'none';
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function logout() {
            if (confirm('Are you sure you want to logout?')) {
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
        }

        // Role indicators
        async function showRoleIndicators(user){
            try{
                const res = await fetch(`${API_BASE}/api/users/${user.user_id}/role`, {
                    headers: { 'X-User-Id': user.user_id }
                });
                const data = await res.json();
                const role = (data && data.role) || 'staff';
                const isManager = ['manager','director','hr'].includes(role);

                // Add role chip near user name
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

        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('taskModal');
            if (event.target === modal) {
                closeModal();
            }
        }

        // Filtering functions
        function populateFilterOptions() {
            if (!teamData) return;
            
            // Populate member filter
            const memberSelect = document.getElementById('filterTeamMember');
            memberSelect.innerHTML = '<option value="">All Members</option>';
            teamData.team_members.forEach(member => {
                memberSelect.innerHTML += `<option value="${member.user_id}">${member.name}</option>`;
            });
            
            // Populate project filter
            const projectSelect = document.getElementById('filterProject');
            projectSelect.innerHTML = '<option value="">All Projects</option>';
            teamData.projects.forEach(project => {
                projectSelect.innerHTML += `<option value="${project.project_id}">${project.name}</option>`;
            });
            
            // Populate status filter
            const statusSelect = document.getElementById('filterStatus');
            statusSelect.innerHTML = '<option value="">All Statuses</option>';
            const statuses = [...new Set(teamData.team_tasks.map(task => task.status))];
            statuses.forEach(status => {
                statusSelect.innerHTML += `<option value="${status}">${status}</option>`;
            });
        }

        function applyFilters() {
            const memberFilter = document.getElementById('filterTeamMember').value;
            const projectFilter = document.getElementById('filterProject').value;
            const statusFilter = document.getElementById('filterStatus').value;
            
            let filteredTasks = teamData.team_tasks;
            
            if (memberFilter) {
                filteredTasks = filteredTasks.filter(task => 
                    task.assigned_to && task.assigned_to.user_id === memberFilter
                );
            }
            
            if (projectFilter) {
                filteredTasks = filteredTasks.filter(task => 
                    task.project_id === projectFilter
                );
            }
            
            if (statusFilter) {
                filteredTasks = filteredTasks.filter(task => 
                    task.status === statusFilter
                );
            }
            
            renderFilteredTasks(filteredTasks);
        }

        function renderFilteredTasks(tasks) {
            const taskGrid = document.getElementById('taskGrid');
            
            if (tasks.length === 0) {
                taskGrid.innerHTML = '<div class="no-tasks">No tasks match the current filters.</div>';
                return;
            }
            
            if (currentTab === 'timeline') {
                // For timeline view, create a temporary timeline data structure
                const tempTeamData = {
                    ...teamData,
                    team_tasks: tasks
                };
                
                // Group filtered tasks by timeline periods
                const timeline = groupTasksByTimeline(tasks);
                const conflicts = detectConflicts(tasks);
                
                tempTeamData.timeline = timeline;
                tempTeamData.conflicts = conflicts;
                
                // Temporarily replace teamData and render timeline
                const originalTeamData = teamData;
                teamData = tempTeamData;
                renderTimelineView();
                teamData = originalTeamData;
            } else {
                // Group tasks by current tab
                let groupedTasks = {};
                
                if (currentTab === 'by-member') {
                    tasks.forEach(task => {
                        const memberId = task.member_id;
                        if (!groupedTasks[memberId]) {
                            groupedTasks[memberId] = [];
                        }
                        groupedTasks[memberId].push(task);
                    });
                } else if (currentTab === 'by-project') {
                    tasks.forEach(task => {
                        const projectId = task.project_id || 'no-project';
                        if (!groupedTasks[projectId]) {
                            groupedTasks[projectId] = [];
                        }
                        groupedTasks[projectId].push(task);
                    });
                } else if (currentTab === 'by-status') {
                    tasks.forEach(task => {
                        const status = task.status;
                        if (!groupedTasks[status]) {
                            groupedTasks[status] = [];
                        }
                        groupedTasks[status].push(task);
                    });
                }
                
                let html = '';
                for (const [groupKey, groupTasks] of Object.entries(groupedTasks)) {
                    html += `<div class="task-group">
                        <h3 class="group-title">${getGroupTitle(groupKey)}</h3>
                        <div class="group-tasks">`;
                    
                    groupTasks.forEach(task => {
                        html += renderTaskCard(task);
                    });
                    
                    html += `</div></div>`;
                }
                
                taskGrid.innerHTML = html;
            }
        }

        function groupTasksByTimeline(tasks) {
            const timeline = {
                "overdue": [],
                "today": [],
                "this_week": [],
                "future": [],
                "no_due_date": []
            };
            
            tasks.forEach(task => {
                const due_date = task.due_date;
                if (!due_date) {
                    timeline["no_due_date"].push(task);
                    return;
                }
                
                const due_dt = new Date(due_date);
                const now = new Date();
                const days_until_due = Math.ceil((due_dt - now) / (1000 * 60 * 60 * 24));
                
                if (days_until_due < 0) {
                    timeline["overdue"].push(task);
                } else if (days_until_due === 0) {
                    timeline["today"].push(task);
                } else if (days_until_due <= 7) {
                    timeline["this_week"].push(task);
                } else {
                    timeline["future"].push(task);
                }
            });
            
            return timeline;
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

        function clearFilters() {
            document.getElementById('filterTeamMember').value = '';
            document.getElementById('filterProject').value = '';
            document.getElementById('filterStatus').value = '';
            renderTasks(); // Render all tasks
        }
    