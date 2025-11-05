try{requireAuth();}catch(e){}


        const API_BASE_URL = 'http://localhost:5000';
        let currentUser = null;
        let currentTask = null;
        let taskId = null;
        
        // Get elements
        const form = document.getElementById('editTaskForm');
        const updateBtn = document.getElementById('updateBtn');
        const deleteBtn = document.getElementById('deleteBtn');
        const pageLoading = document.getElementById('pageLoading');
        const formLoading = document.getElementById('formLoading');
        const message = document.getElementById('message');
        const taskInfo = document.getElementById('taskInfo');
        
        // Check authentication and load task
        window.addEventListener('load', async () => {
            // Check if user is logged in
            const userData = sessionStorage.getItem('currentUser');
            if (!userData) {
                window.location.href = 'login.html';
                return;
            }
            
            currentUser = JSON.parse(userData);
            
            // Get task ID from URL parameter
            const urlParams = new URLSearchParams(window.location.search);
            taskId = urlParams.get('task_id');
            
            if (!taskId) {
                showMessage('❌ No task ID provided. Redirecting to dashboard...', 'error');
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 2000);
                return;
            }
            
            await loadTaskData();
        });
        
        async function loadTaskData() {
            try {
                pageLoading.style.display = 'block';
                
                const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`);
                
                if (!response.ok) {
                    if (response.status === 404) {
                        throw new Error('Task not found');
                    }
                    throw new Error('Failed to load task');
                }
                
                currentTask = await response.json();
                populateForm();
                
            } catch (error) {
                console.error('Error loading task:', error);
                showMessage(`❌ Error loading task: ${error.message}`, 'error');
                
                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 3000);
            } finally {
                pageLoading.style.display = 'none';
            }
        }
        
        function populateForm() {
            // Update page title
            document.title = `Edit: ${currentTask.title}`;
            
            // Show task info
            document.getElementById('taskId').textContent = currentTask.task_id;
            document.getElementById('createdDate').textContent = formatDate(currentTask.created_at);
            document.getElementById('createdBy').textContent = currentTask.created_by?.name || 'Unknown';
            taskInfo.style.display = 'block';
            
            // Populate form fields
            document.getElementById('title').value = currentTask.title || '';
            document.getElementById('description').value = currentTask.description || '';
            document.getElementById('priority').value = currentTask.priority || 'Medium';
            document.getElementById('status').value = currentTask.status || 'To Do';
            
            // Handle due date
            if (currentTask.due_date) {
                const dueDate = new Date(currentTask.due_date);
                dueDate.setMinutes(dueDate.getMinutes() - dueDate.getTimezoneOffset());
                document.getElementById('due_date').value = dueDate.toISOString().slice(0, 16);
            }
            
            // Set minimum due date to current date/time
            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            document.getElementById('due_date').min = now.toISOString().slice(0, 16);
            
            // Populate tags
            const tags = currentTask.tags || [];
            if (tags.length > 0) document.getElementById('tag1').value = tags[0] || '';
            if (tags.length > 1) document.getElementById('tag2').value = tags[1] || '';
            if (tags.length > 2) document.getElementById('tag3').value = tags[2] || '';
            
            // Populate recurring task fields
            const isRecurringCheckbox = document.getElementById('is_recurring');
            const recurringOptions = document.getElementById('recurring_options');
            const recurringInfo = document.getElementById('recurring_info');
            const recurringInfoText = document.getElementById('recurring_info_text');
            
            if (currentTask.is_recurring) {
                isRecurringCheckbox.checked = true;
                recurringOptions.style.display = 'block';
                document.getElementById('recurrence_interval_days').value = currentTask.recurrence_interval_days || '';
                
                // Show info about recurring task
                if (currentTask.parent_recurring_task_id) {
                    recurringInfo.style.display = 'block';
                    recurringInfoText.textContent = `This task was created from a recurring series (Parent: ${currentTask.parent_recurring_task_id})`;
                }
            }
            
            // Check if current user can edit/delete this task
            const canEdit = currentTask.created_by?.user_id === currentUser.user_id;
            if (!canEdit) {
                showMessage('⚠️ You can only edit tasks that you created.', 'error');
                updateBtn.disabled = true;
                deleteBtn.disabled = true;
                
                // Make form read-only
                const inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(input => input.disabled = true);
            }
            
            // Show the form
            form.style.display = 'block';
        }
        
        // Toggle recurring options visibility
        document.getElementById("is_recurring").addEventListener("change", (e) => {
            const options = document.getElementById("recurring_options");
            options.style.display = e.target.checked ? "block" : "none";
            if (!e.target.checked) {
                document.getElementById("recurrence_interval_days").value = "";
            }
        });
        
        // Handle form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const isRecurring = document.getElementById('is_recurring').checked;
            const recurrenceInterval = document.getElementById('recurrence_interval_days').value;
            const dueDate = formData.get('due_date');
            
            // Validation for recurring tasks
            if (isRecurring) {
                if (!dueDate) {
                    showMessage('❌ Recurring tasks must have a due date', 'error');
                    return;
                }
                if (!recurrenceInterval || parseInt(recurrenceInterval) <= 0) {
                    showMessage('❌ Please specify a positive number of days for recurrence interval', 'error');
                    return;
                }
            }
            
            const taskData = {
                title: formData.get('title').trim(),
                description: formData.get('description').trim(),
                priority: formData.get('priority'),
                status: formData.get('status'),
                due_date: dueDate || null,
                is_recurring: isRecurring,
                recurrence_interval_days: isRecurring ? parseInt(recurrenceInterval) : null,
                tags: [
                    document.getElementById("tag1").value.trim(),
                    document.getElementById("tag2").value.trim(),
                    document.getElementById("tag3").value.trim()
                ].filter(t => t.length > 0)
            };
            
            // Validation
            if (!taskData.title || taskData.title.length < 3) {
                showMessage('❌ Please enter a task title (at least 3 characters)', 'error');
                return;
            }
            
            if (!taskData.description || taskData.description.length < 10) {
                showMessage('❌ Please enter a detailed description (at least 10 characters)', 'error');
                return;
            }
            
            setLoading(true);
            hideMessage();
            
            try {
                console.log('Sending update request for task:', taskId);
                console.log('Task data:', taskData);
                console.log('Current user:', currentUser);
                
                const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-User-Id': currentUser.user_id
                    },
                    body: JSON.stringify(taskData)
                });
                
                console.log('Response status:', response.status);
                const result = await response.json();
                console.log('Response data:', result);
                
                if (response.ok) {
                    let message = `✅ Task "${taskData.title}" updated successfully!`;
                    
                    // Check if a new recurring task was created
                    if (result.next_recurring_task_id) {
                        message += ` 🔄 Next occurrence created (ID: ${result.next_recurring_task_id})`;
                    }
                    
                    showMessage(message, 'success');
                    
                    // Update current task data
                    currentTask = result;
                    
                    // Redirect to dashboard after 2 seconds
                    setTimeout(() => {
                        window.location.href = 'dashboard.html';
                    }, 2000);
                    
                } else {
                    console.error('Update failed:', result);
                    showMessage(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
                }
                
            } catch (error) {
                console.error('Error updating task:', error);
                showMessage('❌ Network error. Please check server connection.', 'error');
            } finally {
                setLoading(false);
            }
        });
        
        // Delete functionality
        function confirmDelete() {
            document.getElementById('deleteMessage').textContent = 
                `Are you sure you want to delete "${currentTask.title}"? This action cannot be undone.`;
            document.getElementById('deleteModal').style.display = 'block';
        }
        
        function closeDeleteModal() {
            document.getElementById('deleteModal').style.display = 'none';
        }
        
        async function executeDelete() {
            const confirmBtn = document.getElementById('confirmDeleteBtn');
            const originalText = confirmBtn.textContent;
            
            try {
                confirmBtn.textContent = 'Deleting...';
                confirmBtn.disabled = true;
                
                const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    showMessage(`✅ Task deleted successfully!`, 'success');
                    closeDeleteModal();
                    
                    setTimeout(() => {
                        window.location.href = 'dashboard.html';
                    }, 1500);
                    
                } else {
                    const result = await response.json();
                    showMessage(`❌ Error: ${result.error}`, 'error');
                }
                
            } catch (error) {
                console.error('Error deleting task:', error);
                showMessage('❌ Network error. Please try again.', 'error');
            } finally {
                confirmBtn.textContent = originalText;
                confirmBtn.disabled = false;
            }
        }
        
        // Helper functions
        function setLoading(isLoading) {
            updateBtn.disabled = isLoading;
            deleteBtn.disabled = isLoading;
            formLoading.style.display = isLoading ? 'block' : 'none';
            updateBtn.textContent = isLoading ? 'Updating...' : 'Update Task';
        }
        
        function showMessage(text, type) {
            message.textContent = text;
            message.className = `message ${type}`;
            message.style.display = 'block';
            
            if (type === 'error') {
                setTimeout(() => {
                    if (message.classList.contains('error')) {
                        hideMessage();
                    }
                }, 8000);
            }
        }
        
        function hideMessage() {
            message.style.display = 'none';
        }
        
        function formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleString();
        }
        
        function goToDashboard() {
            window.location.href = 'dashboard.html';
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
