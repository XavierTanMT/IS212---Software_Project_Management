/**
 * Firebase Authentication Configuration
 * This file handles Firebase initialization and authentication utilities
 */

// Firebase configuration - loaded from backend
let firebaseConfig = null;
let auth = null;

/**
 * Initialize Firebase with config from backend
 */
async function initializeFirebase() {
    try {
        // Check if ConfigService is available, with fallback
        let apiUrl;
        if (window.ConfigService && typeof window.ConfigService.getApiUrl === 'function') {
            apiUrl = window.ConfigService.getApiUrl('/api/config/firebase-config');
        } else {
            // Fallback to hardcoded URL for development
            console.warn('ConfigService not available, using fallback URL');
            apiUrl = 'http://localhost:5000/api/config/firebase-config';
        }
        
        console.log('Fetching Firebase config from:', apiUrl);
        
        const response = await fetch(apiUrl);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Failed to load Firebase config');
        }
        
        firebaseConfig = result.data;
        console.log('Firebase config loaded successfully');
        
        // Initialize Firebase
        firebase.initializeApp(firebaseConfig);
        auth = firebase.auth();
        
        // Make auth globally accessible
        window.auth = auth;
        
        return true;
    } catch (error) {
        console.error('Failed to initialize Firebase:', error);
        return false;
    }
}

// Auth utility functions
const AuthUtils = {
    /**
     * Initialize authentication system
     */
    init: async () => {
        return await initializeFirebase();
    },

    /**
     * Get current user
     */
    getCurrentUser: () => {
        return auth ? auth.currentUser : null;
    },

    /**
     * Check if user is authenticated
     */
    isAuthenticated: () => {
        return auth ? auth.currentUser !== null : false;
    },

    /**
     * Get authentication headers for API calls
     */
    getAuthHeaders: async () => {
        const idToken = localStorage.getItem('idToken');
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${idToken}`
        };
    },

    /**
     * Sign out user
     */
    signOut: async () => {
        try {
            console.log('Signing out from Firebase...');
            if (auth) {
                await auth.signOut();
            }
            console.log('Successfully signed out from Firebase');
            
            // Clear localStorage
            localStorage.removeItem('currentUser');
            localStorage.removeItem('idToken');
            
            return true;
        } catch (error) {
            console.error('Error signing out:', error);
            // Even if Firebase signout fails, clear local data
            localStorage.removeItem('currentUser');
            localStorage.removeItem('idToken');
            return false;
        }
    },

    /**
     * Create temporary user object from Firebase Auth data
     */
    createTempUser: (firebaseUser) => {
        return {
            uid: firebaseUser.uid,
            user_id: firebaseUser.uid,
            email: firebaseUser.email,
            name: firebaseUser.displayName || firebaseUser.email.split('@')[0],
            role: 'staff' // Default role
        };
    },

    /**
     * Handle authentication state changes
     */
    onAuthStateChanged: (callback) => {
        return auth ? auth.onAuthStateChanged(callback) : null;
    },

    /**
     * Sign in with email and password
     */
    signInWithEmailAndPassword: async (email, password) => {
        try {
            if (!auth) {
                throw new Error('Firebase auth not initialized');
            }
            
            const userCredential = await auth.signInWithEmailAndPassword(email, password);
            const idToken = await userCredential.user.getIdToken();
            
            // Store token
            localStorage.setItem('idToken', idToken);
            
            return { success: true, userCredential, idToken };
        } catch (error) {
            console.error('Sign in error:', error);
            return { success: false, error };
        }
    },

    /**
     * Create user with email and password
     */
    createUserWithEmailAndPassword: async (email, password) => {
        try {
            if (!auth) {
                throw new Error('Firebase auth not initialized');
            }
            
            const userCredential = await auth.createUserWithEmailAndPassword(email, password);
            const idToken = await userCredential.user.getIdToken();
            
            // Store token
            localStorage.setItem('idToken', idToken);
            
            return { success: true, userCredential, idToken };
        } catch (error) {
            console.error('Create user error:', error);
            return { success: false, error };
        }
    }
};

// Make AuthUtils globally accessible
window.AuthUtils = AuthUtils;

// Export for module systems (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AuthUtils, auth, firebaseConfig };
}
