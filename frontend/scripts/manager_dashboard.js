
        // Global variables
        let dashboardData = null;
        let allStaff = [];
        let allManagers = [];
        let currentUser = null; // Will be set after auth check
        
        // ==================== INITIALIZE EVENT LISTENERS ====================
        
        function initializeManagerEventListeners() {
            document.getElementById('assignStaffBtn').addEventListener('click', openAssignStaffModal);
            document.getElementById('closeAssignModal').addEventListener('click', closeAssignStaffModal);
            document.getElementById('selectAllStaff').addEventListener('click', () => {
                document.querySelectorAll('#staffCheckboxList input[type="checkbox"]').forEach(cb => cb.checked = true);
            });
            document.getElementById('deselectAllStaff').addEventListener('click', () => {
                document.querySelectorAll('#staffCheckboxList input[type="checkbox"]').forEach(cb => cb.checked = false);
            });
            document.getElementById('confirmAssignBtn').addEventListener('click', assignStaffToManager);
            document.getElementById('assignToOtherBtn').addEventListener('click', openSingleAssignModal);
            document.getElementById('closeSingleModal').addEventListener('click', closeSingleAssignModal);
            document.getElementById('singleAssignForm').addEventListener('submit', handleSingleAssign);
            document.getElementById('refreshTeamBtn').addEventListener('click', () => {
                loadMyTeam();
                loadManageTeamTab();
            });
        }
        
        // ==================== TAB SWITCHING ====================
        
        document.addEventListener('DOMContentLoaded', function() {
            // ✅ Require manager role or above - do this AFTER DOM is ready
            try {
                currentUser = requireManager();
                console.log('Manager authenticated:', currentUser);
            } catch (error) {
                console.error('Manager auth failed:', error);
                return; // Stop execution if not manager
            }
            // Tab switching
            document.getElementById('tab-overview').addEventListener('click', function() {
                switchTab('overview', this);
            });
            
            document.getElementById('tab-team').addEventListener('click', function() {
                switchTab('team', this);
                loadMyTeam();
            });
            
            document.getElementById('tab-tasks').addEventListener('click', function() {
                switchTab('tasks', this);
            });
            
            document.getElementById('tab-manage').addEventListener('click', function() {
                switchTab('manage', this);
                loadManageTeamTab();
            });
            
            // Initialize all event listeners
            initializeManagerEventListeners();
            
            // Load initial dashboard data
            loadManagerDashboard();
        });
        
        function switchTab(tabName, tabElement) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            document.getElementById(`${tabName}-tab`).classList.add('active');
            tabElement.classList.add('active');
        }
        
        // ==================== LOAD DASHBOARD ====================
        
        async function loadManagerDashboard() {
            try {
                const response = await fetch(`${API_BASE}/api/manager/dashboard`, {
                    headers: {
                        'X-User-Id': currentUser.user_id
                    }
                });
                
                if (!response.ok) {
                    throw new Error('Failed to load dashboard');
                }
                
                dashboardData = await response.json();
                
                // Display statistics
                displayStatistics(dashboardData);
                
                // Display overview
                displayOverview(dashboardData);
                
                // Display team members
                displayTeamMembers(dashboardData.team_members || []);
                
                // Display team tasks
                displayTeamTasks(dashboardData.team_tasks || []);
                
            } catch (error) {
                console.error('Error loading manager dashboard:', error);
                document.getElementById('statsGrid').innerHTML = '<p style="color: red;">Failed to load dashboard</p>';
            }
        }
        
        function displayStatistics(data) {
            const statsHtml = `
                <div class="stat-card">
                    <h3>Team Members</h3>
                    <div class="number">${data.team_size || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>Active Tasks</h3>
                    <div class="number">${data.active_tasks || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>Completed Tasks</h3>
                    <div class="number">${data.completed_tasks || 0}</div>
                </div>
                <div class="stat-card">
                    <h3>Total Tasks</h3>
                    <div class="number">${data.total_tasks || 0}</div>
                </div>
            `;
            document.getElementById('statsGrid').innerHTML = statsHtml;
        }
        
        function displayOverview(data) {
            const overviewHtml = `
                <p><strong>Manager:</strong> ${data.manager?.name || 'N/A'} (${data.manager?.email || 'N/A'})</p>
                <p><strong>Role:</strong> ${data.manager?.role || 'manager'}</p>
                <hr>
                <h3>Quick Stats</h3>
                <ul>
                    <li>Team Size: ${data.team_size || 0}</li>
                    <li>Active Tasks: ${data.active_tasks || 0}</li>
                    <li>Completed Tasks: ${data.completed_tasks || 0}</li>
                    ${data.overdue_tasks ? `<li style="color: red;">Overdue Tasks: ${data.overdue_tasks}</li>` : ''}
                </ul>
            `;
            document.getElementById('overviewContent').innerHTML = overviewHtml;
        }
        
        function displayTeamMembers(members) {
            if (!members || members.length === 0) {
                document.getElementById('teamMembers').innerHTML = '<p>No team members assigned yet.</p>';
                return;
            }
            
            const membersHtml = members.map(member => `
                <div class="member-card">
                    <h3>${member.name || 'N/A'}</h3>
                    <p><strong>Email:</strong> ${member.email || 'N/A'}</p>
                    <p><strong>Role:</strong> ${member.role || 'staff'}</p>
                    <p><strong>Status:</strong> ${member.is_active ? '✅ Active' : '❌ Inactive'}</p>
                    <button class="btn btn-danger btn-sm" onclick="removeStaffMember('${member.user_id}')">
                        Remove from Team
                    </button>
                </div>
            `).join('');
            
            document.getElementById('teamMembers').innerHTML = membersHtml;
        }
        
        function displayTeamTasks(tasks) {
            if (!tasks || tasks.length === 0) {
                document.getElementById('teamTasks').innerHTML = '<p>No tasks found.</p>';
                return;
            }
            
            const tasksHtml = tasks.map(task => {
                const statusClass = task.status?.toLowerCase().replace(' ', '') || 'todo';
                const priorityBadge = task.priority ? `<span class="badge badge-${task.priority < 3 ? 'high' : task.priority < 7 ? 'medium' : 'low'}">P${task.priority}</span>` : '';
                
                return `
                    <div class="task-card">
                        <h3>${task.title || 'Untitled Task'} <span class="badge badge-${statusClass}">${task.status || 'To Do'}</span> ${priorityBadge}</h3>
                        <p>${task.description || 'No description'}</p>
                        <p><strong>Assigned to:</strong> ${task.assigned_to?.name || task.assignee_name || 'Unassigned'}</p>
                        <p><strong>Due:</strong> ${task.due_date ? new Date(task.due_date).toLocaleDateString() : 'No due date'}</p>
                        ${task.is_overdue ? '<p style="color: red;"><strong>⚠️ OVERDUE</strong></p>' : ''}
                    </div>
                `;
            }).join('');
            
            document.getElementById('teamTasks').innerHTML = tasksHtml;
        }
        
        // ==================== MY TEAM TAB ====================
        
        async function loadMyTeam() {
            try {
                const response = await fetch(`${API_BASE}/api/manager/my-team`, {
                    headers: {
                        'X-User-Id': currentUser.user_id
                    }
                });
                
                const data = await response.json();
                displayTeamMembers(data.team_staff || []);
                
            } catch (error) {
                console.error('Error loading team:', error);
                document.getElementById('teamMembers').innerHTML = '<p style="color: red;">Failed to load team members</p>';
            }
        }
        
        // ==================== MANAGE TEAM TAB ====================
        
        async function loadManageTeamTab() {
            await loadAvailableUsers();
            await loadCurrentTeam();
        }
        
        async function loadAvailableUsers() {
            try {
                // Load all users to get staff and managers
                const response = await fetch(`${API_BASE}/api/manager/all-users`, {
                    headers: {
                        'X-User-Id': currentUser.user_id
                    }
                });
                
                // ✅ Add error checking
                if (!response.ok) {
                    throw new Error(`Failed to load users: ${response.status}`);
                }
                
                const data = await response.json();
                
                // ✅ CHANGED: Direct assignment from response structure
                allStaff = data.staff || [];
                allManagers = data.managers || [];
                
                console.log('Loaded users:', { 
                    staff: allStaff.length, 
                    managers: allManagers.length 
                });
                
            } catch (error) {
                console.error('Error loading users:', error);
                allStaff = [];
                allManagers = [];
            }
        }
        
        async function loadCurrentTeam() {
            try {
                const response = await fetch(`${API_BASE}/api/manager/my-team`, {
                    headers: {
                        'X-User-Id': currentUser.user_id
                    }
                });
                
                const data = await response.json();
                displayCurrentTeam(data.team_staff || []);
                
            } catch (error) {
                console.error('Error loading current team:', error);
            }
        }
        
        function displayCurrentTeam(team) {
            if (!team || team.length === 0) {
                document.getElementById('currentTeamList').innerHTML = '<p>No staff members assigned to you yet.</p>';
                return;
            }
            
            const teamHtml = team.map(member => `
                <div class="member-card">
                    <h4>${member.name}</h4>
                    <p>Email: ${member.email}</p>
                    <p>Assigned: ${member.assigned_at ? new Date(member.assigned_at).toLocaleDateString() : 'N/A'}</p>
                    <button class="btn btn-danger btn-sm" onclick="removeStaffMember('${member.user_id}')">Remove</button>
                </div>
            `).join('');
            
            document.getElementById('currentTeamList').innerHTML = teamHtml;
        }
        
        // ==================== ASSIGN STAFF MODAL ====================
        
        function openAssignStaffModal() {
            document.getElementById('assignStaffModal').style.display = 'block';
            populateStaffCheckboxes();
            populateManagerDropdown('targetManagerSelect', true);
        }
        
        function closeAssignStaffModal() {
            document.getElementById('assignStaffModal').style.display = 'none';
        }
        
        function populateStaffCheckboxes() {
            const container = document.getElementById('staffCheckboxList');
            
            if (!allStaff || allStaff.length === 0) {
                container.innerHTML = '<p>No available staff members found.</p>';
                return;
            }
            
            const checkboxesHtml = allStaff.map(staff => `
                <div class="checkbox-item">
                    <label>
                        <input type="checkbox" value="${staff.user_id}" class="staff-checkbox">
                        <strong>${staff.name}</strong> (${staff.email})
                        ${staff.manager_id ? ' - <em>Already assigned</em>' : ''}
                    </label>
                </div>
            `).join('');
            
            container.innerHTML = checkboxesHtml;
        }
        
        function populateManagerDropdown(selectId, includeBlank = false) {
            const select = document.getElementById(selectId);
            
            let options = includeBlank ? '<option value="">Myself</option>' : '<option value="">Select Manager...</option>';
            
            allManagers.forEach(manager => {
                options += `<option value="${manager.user_id}">${manager.name} (${manager.email})</option>`;
            });
            
            select.innerHTML = options;
        }
        
        async function assignStaffToManager() {
            const selectedStaffIds = Array.from(document.querySelectorAll('.staff-checkbox:checked'))
                .map(cb => cb.value);
            
            if (selectedStaffIds.length === 0) {
                alert('Please select at least one staff member');
                return;
            }
            
            const targetManagerId = document.getElementById('targetManagerSelect').value || currentUser.user_id;
            
            const messageDiv = document.getElementById('assignMessage');
            messageDiv.innerHTML = '<p>Assigning staff members...</p>';
            
            try {
                const response = await fetch(`${API_BASE}/api/manager/assign-staff`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-User-Id': currentUser.user_id
                    },
                    body: JSON.stringify({
                        staff_ids: selectedStaffIds,
                        manager_id: targetManagerId
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    messageDiv.innerHTML = `
                        <div class="message success">
                            <p><strong>✅ Success!</strong></p>
                            <p>${result.message}</p>
                            <p>Total team size: ${result.total_team_size}</p>
                            ${result.failed.length > 0 ? `<p style="color: red;">Failed: ${result.failed.length}</p>` : ''}
                        </div>
                    `;
                    
                    // Refresh team list
                    setTimeout(() => {
                        loadCurrentTeam();
                        loadManagerDashboard();
                        closeAssignStaffModal();
                    }, 2000);
                } else {
                    messageDiv.innerHTML = `<div class="message error">❌ ${result.error}</div>`;
                }
                
            } catch (error) {
                messageDiv.innerHTML = `<div class="message error">❌ Error: ${error.message}</div>`;
            }
        }
        
        // ==================== ASSIGN SINGLE STAFF MODAL ====================
        
        function openSingleAssignModal() {
            document.getElementById('assignSingleModal').style.display = 'block';
            populateStaffDropdown();
            populateManagerDropdown('singleManagerSelect', false);
        }
        
        function closeSingleAssignModal() {
            document.getElementById('assignSingleModal').style.display = 'none';
        }
        
        function populateStaffDropdown() {
            const select = document.getElementById('singleStaffSelect');
            
            let options = '<option value="">Select Staff...</option>';
            allStaff.forEach(staff => {
                options += `<option value="${staff.user_id}">${staff.name} (${staff.email})</option>`;
            });
            
            select.innerHTML = options;
        }
        
        async function handleSingleAssign(e) {
            e.preventDefault();
            
            const staffId = document.getElementById('singleStaffSelect').value;
            const managerId = document.getElementById('singleManagerSelect').value;
            
            if (!staffId || !managerId) {
                alert('Please select both staff and manager');
                return;
            }
            
            const messageDiv = document.getElementById('singleAssignMessage');
            messageDiv.innerHTML = '<p>Assigning manager...</p>';
            
            try {
                const response = await fetch(`${API_BASE}/api/manager/staff/${staffId}/assign-manager`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-User-Id': currentUser.user_id
                    },
                    body: JSON.stringify({
                        manager_id: managerId
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    messageDiv.innerHTML = `
                        <div class="message success">
                            <p><strong>✅ Success!</strong></p>
                            <p>${result.message}</p>
                            <p>Staff: ${result.staff_name}</p>
                            <p>Manager: ${result.manager_name}</p>
                        </div>
                    `;
                    
                    setTimeout(() => {
                        closeSingleAssignModal();
                        loadCurrentTeam();
                    }, 2000);
                } else {
                    messageDiv.innerHTML = `<div class="message error">❌ ${result.error}</div>`;
                }
                
            } catch (error) {
                messageDiv.innerHTML = `<div class="message error">❌ Error: ${error.message}</div>`;
            }
        }
        
        // ==================== REMOVE STAFF ====================
        
        async function removeStaffMember(staffId) {
            if (!confirm('Remove this staff member from your team?')) {
                return;
            }
            
            try {
                const response = await fetch(`${API_BASE}/api/manager/staff/${staffId}/remove-manager`, {
                    method: 'DELETE',
                    headers: {
                        'X-User-Id': currentUser.user_id
                    }
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert('✅ Staff member removed from team');
                    loadCurrentTeam();
                    loadManagerDashboard();
                } else {
                    alert('❌ ' + result.error);
                }
                
            } catch (error) {
                alert('❌ Error removing staff member');
            }
        }
        
        // ==================== MODAL CLOSE ON OUTSIDE CLICK ====================
        
        window.onclick = function(event) {
            const assignModal = document.getElementById('assignStaffModal');
            const singleModal = document.getElementById('assignSingleModal');
            
            if (event.target === assignModal) {
                closeAssignStaffModal();
            }
            if (event.target === singleModal) {
                closeSingleAssignModal();
            }
        }
    