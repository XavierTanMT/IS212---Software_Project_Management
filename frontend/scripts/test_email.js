
        let currentUser = null;

        // Initialize page
        document.addEventListener('DOMContentLoaded', async () => {
            try {
                currentUser = requireAuth();
                document.getElementById('userIdDisplay').textContent = currentUser.user_id || 'N/A';
                document.getElementById('userEmailDisplay').textContent = currentUser.email || 'N/A';
                document.getElementById('userNameDisplay').textContent = currentUser.name || 'N/A';
                
                // Load projects for dropdown
                await loadProjects();
                await loadRecentNotifications();
            } catch (e) {
                console.error('Init error:', e);
            }
        });

        async function loadProjects() {
            try {
                const res = await fetch(`${API_BASE}/api/projects`);
                if (res.ok) {
                    const data = await res.json();
                    const select = document.getElementById('taskProject');
                    data.projects.forEach(proj => {
                        const opt = document.createElement('option');
                        opt.value = proj.project_id;
                        opt.textContent = proj.name;
                        select.appendChild(opt);
                    });
                }
            } catch (e) {
                console.error('Error loading projects:', e);
            }
        }

        async function sendDirectNotification() {
            const title = document.getElementById('directTitle').value;
            const body = document.getElementById('directBody').value;
            const resultDiv = document.getElementById('directResult');

            if (!title || !body) {
                showResult(resultDiv, 'error', 'Please fill in both title and body');
                return;
            }

            try {
                resultDiv.className = 'result info';
                resultDiv.innerHTML = 'Sending email... <span class="loading"></span>';
                resultDiv.style.display = 'block';

                const payload = {
                    user_id: currentUser.user_id,
                    title: title,
                    body: body
                };

                console.log('Sending test email:', payload);

                // Use the test-email endpoint to send directly
                const res = await fetch(`${API_BASE}/api/notifications/test-email`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                console.log('Response status:', res.status);

                if (res.ok) {
                    const data = await res.json();
                    console.log('Response data:', data);
                    showResult(resultDiv, 'success', 
                        `✓ Email sent successfully!<br>
                        Recipient: ${data.recipient}<br>
                        <small>${data.message}</small>`);
                } else {
                    const errText = await res.text();
                    console.error('Error response:', errText);
                    let errMsg = errText;
                    try {
                        const errJson = JSON.parse(errText);
                        errMsg = errJson.error || errJson.message || errText;
                    } catch (e) {}
                    showResult(resultDiv, 'error', `Failed: ${errMsg}`);
                }
            } catch (e) {
                console.error('Exception:', e);
                showResult(resultDiv, 'error', `Error: ${e.message}`);
            }
        }

        async function checkDeadlines() {
            const hours = document.getElementById('deadlineHours').value;
            const resendExisting = document.getElementById('resendExisting').checked;
            const resultDiv = document.getElementById('deadlineResult');

            try {
                resultDiv.className = 'result info';
                resultDiv.innerHTML = 'Checking deadlines... <span class="loading"></span>';
                resultDiv.style.display = 'block';

                // Calculate start and end times
                const now = new Date();
                const end = new Date(now.getTime() + (hours * 60 * 60 * 1000));
                
                // Use very wide range - go back 7 days to catch past due tasks too
                const start = new Date(now.getTime() - (7 * 24 * 60 * 60 * 1000));
                
                const startIso = start.toISOString();
                const endIso = end.toISOString();

                console.log('Checking deadlines:', { startIso, endIso, hours });

                const url = `${API_BASE}/api/notifications/check-deadlines?start_iso=${encodeURIComponent(startIso)}&end_iso=${encodeURIComponent(endIso)}&resend_existing=${resendExisting}`;
                const res = await fetch(url, { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (res.ok) {
                    const data = await res.json();
                    showResult(resultDiv, 'success', 
                        `✓ Checked ${data.checked} tasks. Created ${data.notifications_created} notifications.<br>
                        <small>Time range: ${start.toLocaleString()} to ${end.toLocaleString()}</small>`);
                    setTimeout(() => loadRecentNotifications(), 1000);
                } else {
                    const errText = await res.text();
                    let errMsg = errText;
                    try {
                        const errJson = JSON.parse(errText);
                        errMsg = errJson.message || errJson.error || errText;
                    } catch (e) {}
                    showResult(resultDiv, 'error', `Failed: ${errMsg}`);
                }
            } catch (e) {
                showResult(resultDiv, 'error', `Error: ${e.message}`);
            }
        }

        async function getDueToday() {
            const resultDiv = document.getElementById('dueTodayResult');

            try {
                resultDiv.className = 'result info';
                resultDiv.innerHTML = 'Fetching tasks... <span class="loading"></span>';
                resultDiv.style.display = 'block';

                const res = await fetch(`${API_BASE}/api/notifications/due-today`, {
                    method: 'GET'
                });

                if (res.ok) {
                    const data = await res.json();
                    if (data.count === 0) {
                        showResult(resultDiv, 'info', 'No tasks due today.');
                    } else {
                        let html = `<strong>${data.count} task(s) due today:</strong><br><br>`;
                        data.tasks.forEach(task => {
                            html += `• ${task.title} (Due: ${task.due_date})<br>`;
                        });
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = html;
                    }
                } else {
                    const errText = await res.text();
                    let errMsg = errText;
                    try {
                        const errJson = JSON.parse(errText);
                        errMsg = errJson.message || errJson.error || errText;
                    } catch (e) {}
                    showResult(resultDiv, 'error', `Failed: ${errMsg}`);
                }
            } catch (e) {
                showResult(resultDiv, 'error', `Error: ${e.message}`);
            }
        }

        async function createTestTask() {
            const title = document.getElementById('taskTitle').value;
            const hoursFromNow = parseInt(document.getElementById('taskHours').value);
            const projectId = document.getElementById('taskProject').value;
            const resultDiv = document.getElementById('taskResult');

            if (!title) {
                showResult(resultDiv, 'error', 'Please enter a task title');
                return;
            }

            try {
                resultDiv.className = 'result info';
                resultDiv.innerHTML = 'Creating task... <span class="loading"></span>';
                resultDiv.style.display = 'block';

                const dueDate = new Date();
                dueDate.setHours(dueDate.getHours() + hoursFromNow);

                // Follow your backend conventions exactly
                const taskData = {
                    title: title,
                    description: `Test task created at ${new Date().toLocaleString()} for email notification testing. This task will trigger deadline notifications when checked.`,
                    status: 'To Do',  // Your backend expects 'To Do', not 'pending'
                    priority: 'High',  // Your backend expects 'High', not 'high'
                    due_date: dueDate.toISOString().slice(0, 16), // Format: YYYY-MM-DDTHH:mm
                    created_by_id: currentUser.user_id,
                    assigned_to_id: currentUser.user_id,
                    project_id: projectId || undefined,
                    labels: []
                };

                const res = await fetch(`${API_BASE}/api/tasks`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(taskData)
                });

                if (res.ok) {
                    const data = await res.json();
                    showResult(resultDiv, 'success', 
                        `✓ Task created successfully!<br>
                        Task ID: ${data.task_id}<br>
                        Status: ${data.status}<br>
                        Priority: ${data.priority}<br>
                        Due: ${dueDate.toLocaleString()}<br>
                        <small>Run "Check Deadlines" to trigger notification emails.</small>`);
                } else {
                    const errText = await res.text();
                    let errMsg = errText;
                    try {
                        const errJson = JSON.parse(errText);
                        errMsg = errJson.error || errJson.message || errText;
                    } catch (e) {}
                    showResult(resultDiv, 'error', `Failed: ${errMsg}`);
                }
            } catch (e) {
                showResult(resultDiv, 'error', `Error: ${e.message}`);
            }
        }

        async function loadRecentNotifications() {
            const container = document.getElementById('notificationsList');
            
            try {
                container.innerHTML = '<p style="color: #888;">Loading notifications...</p>';
                
                // Fetch tasks to get task IDs, then check for notifications
                // For now, we'll just show a message since there's no direct "get my notifications" endpoint
                container.innerHTML = `
                    <div style="padding: 1rem; background: #f8f9fa; border-radius: 8px; color: #666;">
                        <p><strong>Note:</strong> To view notifications, you can:</p>
                        <ul style="margin-left: 1.5rem; margin-top: 0.5rem; line-height: 1.8;">
                            <li>Check your email inbox for notification emails</li>
                            <li>Create a test task and run "Check Deadlines"</li>
                            <li>Use the "Tasks Due Today" feature</li>
                        </ul>
                        <p style="margin-top: 1rem; font-size: 0.9rem;">
                            💡 Tip: Create a task due in 2 hours, then run "Check Deadlines" with a 24-hour window.
                        </p>
                    </div>
                `;
            } catch (e) {
                container.innerHTML = `<p style="color: #d32f2f;">Error loading notifications: ${e.message}</p>`;
            }
        }

        function showResult(div, type, message) {
            div.className = `result ${type}`;
            div.innerHTML = message;
            div.style.display = 'block';
        }
    