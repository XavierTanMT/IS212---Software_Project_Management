/**
 * Error Handling Service
 * Centralized error handling for frontend
 */
class ErrorHandler {
    constructor() {
        this.errorLog = [];
        this.maxLogSize = 100;
    }
    
    /**
     * Handle API errors
     */
    static handleApiError(error, context = '') {
        console.error(`API Error${context ? ` in ${context}` : ''}:`, error);
        
        let userMessage = 'An unexpected error occurred';
        let errorCode = 'UNKNOWN_ERROR';
        
        if (error.response) {
            // Server responded with error status
            const status = error.response.status;
            const data = error.response.data || {};
            
            switch (status) {
                case 400:
                    userMessage = data.message || 'Invalid request';
                    errorCode = 'VALIDATION_ERROR';
                    break;
                case 401:
                    userMessage = 'Please log in again';
                    errorCode = 'AUTHENTICATION_ERROR';
                    // Redirect to login
                    setTimeout(() => {
                        window.location.href = 'login.html';
                    }, 2000);
                    break;
                case 403:
                    userMessage = 'You do not have permission to perform this action';
                    errorCode = 'AUTHORIZATION_ERROR';
                    break;
                case 404:
                    userMessage = 'The requested resource was not found';
                    errorCode = 'NOT_FOUND';
                    break;
                case 500:
                    userMessage = 'Server error. Please try again later';
                    errorCode = 'SERVER_ERROR';
                    break;
                default:
                    userMessage = data.message || `Error ${status}`;
                    errorCode = `HTTP_${status}`;
            }
        } else if (error.request) {
            // Network error
            userMessage = 'Network error. Please check your connection';
            errorCode = 'NETWORK_ERROR';
        } else {
            // Other error
            userMessage = error.message || 'An unexpected error occurred';
            errorCode = 'CLIENT_ERROR';
        }
        
        return {
            userMessage,
            errorCode,
            originalError: error
        };
    }
    
    /**
     * Handle Firebase Auth errors
     */
    static handleFirebaseError(error) {
        console.error('Firebase Error:', error);
        
        let userMessage = 'Authentication failed';
        
        if (error.code) {
            switch (error.code) {
                case 'auth/user-not-found':
                    userMessage = 'No account found with this email address';
                    break;
                case 'auth/wrong-password':
                    userMessage = 'Incorrect password. Please try again';
                    break;
                case 'auth/invalid-email':
                    userMessage = 'Please enter a valid email address';
                    break;
                case 'auth/user-disabled':
                    userMessage = 'This account has been disabled';
                    break;
                case 'auth/too-many-requests':
                    userMessage = 'Too many failed attempts. Please try again later';
                    break;
                case 'auth/email-already-in-use':
                    userMessage = 'This email is already registered';
                    break;
                case 'auth/weak-password':
                    userMessage = 'Password is too weak. Please choose a stronger password';
                    break;
                case 'auth/network-request-failed':
                    userMessage = 'Network error. Please check your connection';
                    break;
                default:
                    userMessage = error.message || 'Authentication failed';
            }
        }
        
        return {
            userMessage,
            errorCode: error.code || 'FIREBASE_ERROR',
            originalError: error
        };
    }
    
    /**
     * Handle validation errors
     */
    static handleValidationError(errors) {
        console.error('Validation Error:', errors);
        
        let userMessage = 'Please check your input';
        
        if (Array.isArray(errors)) {
            userMessage = errors.join('; ');
        } else if (typeof errors === 'string') {
            userMessage = errors;
        } else if (errors && errors.errors) {
            userMessage = errors.errors.join('; ');
        }
        
        return {
            userMessage,
            errorCode: 'VALIDATION_ERROR',
            originalError: errors
        };
    }
    
    /**
     * Show error message to user
     */
    static showError(message, containerId = 'message') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error('Error container not found:', containerId);
            return;
        }
        
        // Clear existing messages
        container.innerHTML = '';
        container.className = 'message error';
        container.textContent = message;
        container.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            container.style.display = 'none';
        }, 5000);
    }
    
    /**
     * Show success message to user
     */
    static showSuccess(message, containerId = 'message') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error('Success container not found:', containerId);
            return;
        }
        
        // Clear existing messages
        container.innerHTML = '';
        container.className = 'message success';
        container.textContent = message;
        container.style.display = 'block';
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            container.style.display = 'none';
        }, 3000);
    }
    
    /**
     * Hide messages
     */
    static hideMessage(containerId = 'message') {
        const container = document.getElementById(containerId);
        if (container) {
            container.style.display = 'none';
        }
    }
    
    /**
     * Log error for debugging
     */
    logError(error, context = '') {
        const errorEntry = {
            timestamp: new Date().toISOString(),
            context,
            error: error.message || error,
            stack: error.stack,
            userAgent: navigator.userAgent,
            url: window.location.href
        };
        
        this.errorLog.push(errorEntry);
        
        // Keep only recent errors
        if (this.errorLog.length > this.maxLogSize) {
            this.errorLog.shift();
        }
        
        console.error('Logged error:', errorEntry);
    }
    
    /**
     * Get error log for debugging
     */
    getErrorLog() {
        return this.errorLog;
    }
    
    /**
     * Clear error log
     */
    clearErrorLog() {
        this.errorLog = [];
    }
}

// Create global error handler instance
window.ErrorHandler = ErrorHandler;

// Global error handler for unhandled errors
window.addEventListener('error', (event) => {
    console.error('Unhandled error:', event.error);
    ErrorHandler.logError(event.error, 'Global Error Handler');
});

// Global error handler for unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    ErrorHandler.logError(event.reason, 'Unhandled Promise Rejection');
});
