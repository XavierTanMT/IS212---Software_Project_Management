
        // Global variables
        let allUsers = [];
        let currentUser = null; // Will be set after auth check
        
        // ==================== INITIALIZE EVENT LISTENERS ====================
        
        function initializeEventListeners() {
            document.getElementById('roleFilter').addEventListener('change', filterUsers);
            document.getElementById('statusFilter').addEventListener('change', filterUsers);
            document.getElementById('createUserBtn').addEventListener('click', openCreateUserModal);
            document.getElementById('closeModalBtn').addEventListener('click', closeCreateUserModal);
            document.getElementById('createUserForm').addEventListener('submit', handleCreateUser);
            document.getElementById('generateReportBtn').addEventListener('click', generateReport);
        }
        
        // ==================== TAB SWITCHING (Event Listeners) ====================
        
        // Wait for DOM to be ready before attaching event listeners
        document.addEventListener('DOMContentLoaded', function() {
            // ✅ Require admin role - do this AFTER DOM is ready
            try {
                currentUser = requireAdmin();
                console.log('Admin authenticated:', currentUser);
            } catch (error) {
                console.error('Admin auth failed:', error);
                return; // Stop execution if not admin
            }
            document.getElementById('tab-overview').addEventListener('click', function() {
                switchTab('overview', this);
            });
            
            document.getElementById('tab-users').addEventListener('click', function() {
                switchTab('users', this);
            });
            
            document.getElementById('tab-projects').addEventListener('click', function() {
                switchTab('projects', this);
            });
            
            document.getElementById('tab-reports').addEventListener('click', function() {
                switchTab('reports', this);
            });
            
            // Initialize all other event listeners
            initializeEventListeners();
            
            // Load initial data
            loadAdminDashboard();
        });
        
        function switchTab(tabName, tabElement) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(`${tabName}-tab`).classList.add('active');
            tabElement.classList.add('active');
            
            // Load data for tab
            if (tabName === 'users') {
                loadUsers();
            } else if (tabName === 'projects') {
                loadProjects();
            }
        }
        
        // ==================== DASHBOARD LOADING ====================
        
        async function loadAdminDashboard() {
            try {
                const response = await fetch(`${API_BASE}/api/admin/dashboard`);
                const data = await response.json();
                
                // Load statistics
                const statsHtml = `
                    <div class="stat-card">
                        <h3>Total Users</h3>
                        <div class="number">${data.statistics.total_users}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Active Users</h3>
                        <div class="number">${data.statistics.active_users}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Total Tasks</h3>
                        <div class="number">${data.statistics.total_tasks}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Total Projects</h3>
                        <div class="number">${data.statistics.total_projects}</div>
                    </div>
                `;
                document.getElementById('statsGrid').innerHTML = statsHtml;
                
                // Load system overview
                const overviewHtml = `
                    <p><strong>Users by Role:</strong></p>
                    <ul>
                        <li>Staff: ${data.statistics.users_by_role.staff || 0}</li>
                        <li>Managers: ${data.statistics.users_by_role.manager || 0}</li>
                        <li>Directors: ${data.statistics.users_by_role.director || 0}</li>
                        <li>HR: ${data.statistics.users_by_role.hr || 0}</li>
                        <li>Admins: ${data.statistics.users_by_role.admin || 0}</li>
                    </ul>
                    <p><strong>Recent Activity:</strong></p>
                    <p>Tasks created today: ${data.statistics.tasks_created_today || 0}</p>
                `;
                document.getElementById('systemOverview').innerHTML = overviewHtml;
                
                // Store users for filtering
                allUsers = data.recent_users || [];
                displayUsers(allUsers);
                
            } catch (error) {
                console.error('Error loading admin dashboard:', error);
                alert('Failed to load admin dashboard');
            }
        }
        
        async function loadUsers() {
            try {
                const response = await fetch(`${API_BASE}/api/admin/dashboard`);
                const data = await response.json();
                allUsers = data.recent_users || [];
                displayUsers(allUsers);
            } catch (error) {
                console.error('Error loading users:', error);
            }
        }
        
        function displayUsers(users) {
            const tbody = document.getElementById('usersTableBody');
            
            if (!users || users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8">No users found</td></tr>';
                return;
            }
            
            tbody.innerHTML = users.map(user => `
                <tr>
                    <td>${user.name || 'N/A'}</td>
                    <td>${user.email || 'N/A'}</td>
                    <td><code>${user.user_id || 'N/A'}</code></td>
                    <td>${user.department || 'N/A'}</td>
                    <td><span class="badge badge-${user.role || 'staff'}">${(user.role || 'staff').toUpperCase()}</span></td>
                    <td><span class="badge badge-${user.is_active !== false ? 'active' : 'inactive'}">${user.is_active !== false ? 'Active' : 'Inactive'}</span></td>
                    <td>${user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</td>
                    <td>
                        <button class="btn btn-primary" onclick="changeUserRole('${user.user_id}')">Change Role</button>
                        <button class="btn btn-primary" onclick="changeUserDepartment('${user.user_id}')">Set Dept</button>
                        ${user.is_active !== false ? 
                            `<button class="btn btn-danger" onclick="deactivateUser('${user.user_id}')">Deactivate</button>` :
                            `<button class="btn btn-success" onclick="activateUser('${user.user_id}')">Activate</button>`
                        }
                    </td>
                </tr>
            `).join('');
        }
        
        // ==================== USER FILTERING ====================
        
        function filterUsers() {
            const roleFilter = document.getElementById('roleFilter').value;
            const statusFilter = document.getElementById('statusFilter').value;
            
            let filtered = allUsers;
            
            if (roleFilter) {
                filtered = filtered.filter(u => u.role === roleFilter);
            }
            
            if (statusFilter === 'active') {
                filtered = filtered.filter(u => u.is_active !== false);
            } else if (statusFilter === 'inactive') {
                filtered = filtered.filter(u => u.is_active === false);
            }
            
            displayUsers(filtered);
        }
        
        // ==================== CREATE USER MODAL ====================
        
        function openCreateUserModal() {
            document.getElementById('createUserModal').style.display = 'block';
            document.getElementById('createUserForm').reset();
            document.getElementById('createUserMessage').innerHTML = '';
        }
        
        function closeCreateUserModal() {
            document.getElementById('createUserModal').style.display = 'none';
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('createUserModal');
            if (event.target == modal) {
                closeCreateUserModal();
            }
        }
        
        // ==================== CREATE USER HANDLER ====================
        
        async function handleCreateUser(e) {
            e.preventDefault();
            
            const messageDiv = document.getElementById('createUserMessage');
            messageDiv.innerHTML = '<p>Creating user...</p>';
            
            const userData = {
                user_id: document.getElementById('user_id').value.trim(),
                name: document.getElementById('name').value.trim(),
                email: document.getElementById('email').value.trim(),
                password: document.getElementById('password').value,
                role: document.getElementById('role').value,
                manager_type: document.getElementById('role').value,  // For backend compatibility
                department: document.getElementById('department').value || ''
            };
            
            try {
                // Determine endpoint based on role
                const endpoint = userData.role === 'staff' ? 'staff' : 'managers';
                
                const response = await fetch(`${API_BASE}/api/admin/${endpoint}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(userData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    messageDiv.innerHTML = `
                        <div class="message success">
                            <p><strong>✅ User Created Successfully!</strong></p>
                            <p>Send these credentials to the user:</p>
                            <p><strong>Email:</strong> ${result.user.email}</p>
                            <p><strong>Password:</strong> ${userData.password}</p>
                            <p><strong>Role:</strong> ${result.user.role}</p>
                            <p><strong>Department:</strong> ${result.user.department || userData.department || 'N/A'}</p>
                            <p><strong>Login URL:</strong> <a href="login.html" target="_blank">login.html</a></p>
                        </div>
                    `;
                    
                    // Reload users list
                    setTimeout(() => {
                        loadUsers();
                        closeCreateUserModal();
                    }, 3000);
                    
                } else {
                    messageDiv.innerHTML = `<div class="message error">❌ ${result.error}</div>`;
                }
                
            } catch (error) {
                messageDiv.innerHTML = `<div class="message error">❌ Error: ${error.message}</div>`;
            }
        }
        
        // ==================== USER MANAGEMENT ACTIONS ====================
        
        async function changeUserRole(userId) {
            const newRole = prompt('Enter new role (staff, manager, director, hr, admin):');
            if (!newRole) return;
            
            const validRoles = ['staff', 'manager', 'director', 'hr', 'admin'];
            if (!validRoles.includes(newRole)) {
                alert('Invalid role. Must be: staff, manager, director, hr, or admin');
                return;
            }
            
            try {
                const response = await fetch(`${API_BASE}/api/admin/users/${userId}/role`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ role: newRole })
                });
                
                if (response.ok) {
                    alert('Role updated successfully');
                    loadUsers();
                } else {
                    const error = await response.json();
                    alert('Failed: ' + error.error);
                }
            } catch (error) {
                alert('Error updating role');
            }
        }
        
        async function deactivateUser(userId) {
            if (!confirm('Deactivate this user? They will not be able to log in.')) return;
            
            try {
                const response = await fetch(`${API_BASE}/api/admin/users/${userId}/status`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_active: false })
                });
                
                if (response.ok) {
                    alert('User deactivated');
                    loadUsers();
                } else {
                    alert('Failed to deactivate user');
                }
            } catch (error) {
                alert('Error deactivating user');
            }
        }
        
        async function activateUser(userId) {
            try {
                const response = await fetch(`${API_BASE}/api/admin/users/${userId}/status`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_active: true })
                });
                
                if (response.ok) {
                    alert('User activated');
                    loadUsers();
                } else {
                    alert('Failed to activate user');
                }
            } catch (error) {
                alert('Error activating user');
            }
        }
        
        // ==================== PROJECTS ====================
        
        async function loadProjects() {
            try {
                const response = await fetch(`${API_BASE}/api/projects`);
                const projects = await response.json();
                
                const projectsHtml = projects.map(p => `
                    <div style="padding: 15px; border: 1px solid #eee; margin: 10px 0; border-radius: 4px; background: #f9f9f9;">
                        <h3>${p.name || p.project_id}</h3>
                        <p>${p.description || 'No description'}</p>
                        <p><strong>Project ID:</strong> <code>${p.project_id}</code></p>
                        <p><strong>Created:</strong> ${p.created_at ? new Date(p.created_at).toLocaleDateString() : 'N/A'}</p>
                    </div>
                `).join('');
                
                document.getElementById('projectsList').innerHTML = projectsHtml || 'No projects found';
            } catch (error) {
                console.error('Error loading projects:', error);
                document.getElementById('projectsList').innerHTML = 'Error loading projects';
            }
        }
        
        // ==================== REPORTS & EXPORT ====================
        
        async function generateReport() {
            const messageDiv = document.getElementById('reportMessage');
            messageDiv.innerHTML = '<div class="message info">⏳ Generating report...</div>';
            
            const reportType = document.getElementById('reportType').value;
            const format = document.getElementById('reportFormat').value;
            const userId = document.getElementById('filterUserId').value.trim();
            const projectId = document.getElementById('filterProjectId').value.trim();
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            
            // Build query parameters
            const params = new URLSearchParams({
                format: format,
                report_type: reportType
            });
            
            if (userId) params.append('user_id', userId);
            if (projectId) params.append('project_id', projectId);
            if (startDate) params.append('start_date', startDate + 'T00:00:00Z');
            if (endDate) params.append('end_date', endDate + 'T23:59:59Z');
            
            try {
                const response = await fetch(`${API_BASE}/api/reports/task-completion?${params.toString()}`, {
                    method: 'GET',
                    headers: {
                        'X-User-Id': currentUser.uid
                    }
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    messageDiv.innerHTML = `<div class="message error">❌ ${error.error || 'Failed to generate report'}</div>`;
                    return;
                }
                
                // Get filename from Content-Disposition header or create default
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = `task_report_${new Date().getTime()}.${format}`;
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
                    if (filenameMatch) filename = filenameMatch[1];
                }
                
                // Download the file
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                messageDiv.innerHTML = `<div class="message success">✅ Report downloaded successfully: ${filename}</div>`;
                
            } catch (error) {
                console.error('Error generating report:', error);
                messageDiv.innerHTML = `<div class="message error">❌ Error: ${error.message}</div>`;
            }
        }
        
        // Quick report functions
        function quickReport(type) {
            const messageDiv = document.getElementById('reportMessage');
            const today = new Date();
            let startDate = '';
            let endDate = '';
            
            // Calculate date ranges
            switch(type) {
                case 'this_week':
                    const monday = new Date(today);
                    monday.setDate(today.getDate() - today.getDay() + 1);
                    const sunday = new Date(monday);
                    sunday.setDate(monday.getDate() + 6);
                    startDate = monday.toISOString().split('T')[0];
                    endDate = sunday.toISOString().split('T')[0];
                    break;
                    
                case 'this_month':
                    startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
                    endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];
                    break;
                    
                case 'completed':
                    // Leave dates blank, will show all completed
                    break;
                    
                case 'overdue':
                    // Tasks due before today
                    endDate = new Date(today.setDate(today.getDate() - 1)).toISOString().split('T')[0];
                    break;
            }
            
            // Set form values
            document.getElementById('startDate').value = startDate;
            document.getElementById('endDate').value = endDate;
            document.getElementById('reportType').value = 'summary';
            document.getElementById('reportFormat').value = 'pdf';
            document.getElementById('filterUserId').value = '';
            document.getElementById('filterProjectId').value = '';
            
            // Show message
            messageDiv.innerHTML = `<div class="message info">📋 Quick report configured for: <strong>${type.replace('_', ' ')}</strong>. Click "Generate & Download Report" to export.</div>`;
        }

        // ==================== CHANGE DEPARTMENT ====================

        async function changeUserDepartment(userId) {
            // Allowed departments - must match backend
            const departments = [
                'Finance & Accounting',
                'Operations',
                'Customer Service (Support)',
                'Sales & Marketing',
                'Product Management',
                'Quality Assurance (QA)',
                'IT / Data / Infrastructure',
                'Legal & Compliance'
            ];

            // Show a prompt with options (admin must type exact value)
            const list = departments.map(d => `- ${d}`).join('\n');
            let newDept = prompt(`Enter new department for user ${userId}:\n(Enter empty to clear)\n\nAvailable departments:\n${list}`);
            if (newDept === null) return; // cancelled

            newDept = newDept.trim();

            if (newDept !== '' && !departments.includes(newDept)) {
                alert('Invalid department. Please enter one of the listed departments exactly.');
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/api/admin/users/${userId}/department`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'X-User-Id': currentUser.uid },
                    body: JSON.stringify({ department: newDept })
                });

                const result = await response.json();
                if (response.ok) {
                    alert('Department updated successfully');
                    loadUsers();
                } else {
                    alert('Failed to update department: ' + (result.error || JSON.stringify(result)));
                }
            } catch (err) {
                console.error('Error updating department:', err);
                alert('Error updating department');
            }
        }
    