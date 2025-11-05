
        // TODO: Replace with your Firebase config from Firebase Console
        const FIREBASE_ENABLED = false;
        
        const firebaseConfig = {
            apiKey: "AIzaSyDummy_Replace_With_Your_Config",
            authDomain: "your-project.firebaseapp.com",
            projectId: "your-project-id"
        };
        
        // Initialize Firebase only if enabled
        if (FIREBASE_ENABLED) {
            firebase.initializeApp(firebaseConfig);
        }
    


        const form = document.getElementById('createUserForm');
        const submitBtn = document.getElementById('submitBtn');
        const loading = document.getElementById('loading');
        const message = document.getElementById('message');
        const userIdInput = document.getElementById('user_id');
        const nameInput = document.getElementById('name');
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirm_password');

        function showMessage(text, type) {
            message.textContent = text;
            message.className = 'message ' + type;
            message.style.display = 'block';
        }

        function hideMessage() {
            message.style.display = 'none';
        }

        function setLoading(isLoading) {
            submitBtn.disabled = isLoading;
            loading.style.display = isLoading ? 'block' : 'none';
            submitBtn.textContent = isLoading ? 'Creating Account...' : 'Create Account with Firebase';
            [userIdInput, nameInput, emailInput, passwordInput, confirmPasswordInput].forEach(i => i.disabled = isLoading);
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const userData = {
                user_id: userIdInput.value.trim(),
                name: nameInput.value.trim(),
                email: emailInput.value.trim(),
                password: passwordInput.value,
                confirm_password: confirmPasswordInput.value
            };

            // Validation
            if (!userData.user_id || !userData.name || !userData.email || !userData.password) {
                showMessage('❌ Please fill all required fields', 'error');
                return;
            }

            if (userData.password !== userData.confirm_password) {
                showMessage('❌ Passwords do not match', 'error');
                return;
            }

            if (userData.password.length < 6) {
                showMessage('❌ Password must be at least 6 characters', 'error');
                return;
            }

            hideMessage();
            setLoading(true);

            try {
                // Register with Firebase
                const result = await registerWithFirebase(userData);

                showMessage(`🎉 Welcome, ${userData.name}! Your account has been created successfully with Firebase Auth.`, 'success');

                setTimeout(() => {
                    window.location.href = 'dashboard.html';
                }, 1500);

            } catch (err) {
                console.error('Registration error:', err);
                showMessage('❌ ' + err.message, 'error');
            } finally {
                setLoading(false);
            }
        });
    