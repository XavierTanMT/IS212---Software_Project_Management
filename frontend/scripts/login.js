
        // Backend-only mode - no client-side Firebase needed
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
    

window.skipNavbar = true;


        const form = document.getElementById('loginForm');
        const loginBtn = document.getElementById('loginBtn');
        const loading = document.getElementById('loading');
        const message = document.getElementById('message');
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');
        
        // Check if user is already logged in
        window.addEventListener('load', async () => {
            // Add a small delay to prevent rapid redirects
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const currentUser = getCurrentUser();
            const token = getFirebaseToken();
            
            if (currentUser && token) {
                try {
                    // Verify session is still valid (with throttling)
                    const isValid = await verifySession();
                    if (isValid) {
                        // User already logged in, redirect to role-appropriate dashboard
                        console.log('User already authenticated, redirecting to dashboard');
                        redirectToRoleDashboard();
                    } else {
                        // Session expired, clear it
                        console.log('Session expired, clearing user data');
                        clearCurrentUser();
                    }
                } catch (error) {
                    console.error('Error verifying session:', error);
                    clearCurrentUser();
                }
            }
        });
        
        // Handle login form
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = emailInput.value.trim();
            const password = passwordInput.value;
            
            if (!email || !password) {
                showMessage('Please enter both email and password', 'error');
                return;
            }
            
            setLoading(true);
            hideMessage();
            
            try {
                // Login with Firebase backend
                const result = await loginWithFirebase(email, password);
                
                showMessage(`✅ Welcome back, ${result.user.name}!`, 'success');
                
                // Redirect to role-appropriate dashboard
                setTimeout(() => {
                    redirectToRoleDashboard();
                }, 1000);
                
            } catch (error) {
                console.error('Login error:', error);
                showMessage(`❌ ${error.message}`, 'error');
            } finally {
                setLoading(false);
            }
        });
        
        // Helper functions
        function setLoading(isLoading) {
            loginBtn.disabled = isLoading;
            emailInput.disabled = isLoading;
            passwordInput.disabled = isLoading;
            loading.style.display = isLoading ? 'block' : 'none';
            loginBtn.textContent = isLoading ? 'Signing in...' : 'Sign In';
        }
        
        function showMessage(text, type) {
            message.textContent = text;
            message.className = `message ${type}`;
            message.style.display = 'block';
        }
        
        function hideMessage() {
            message.style.display = 'none';
        }
    