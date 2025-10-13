/**
 * Configuration Service
 * Handles environment-specific configuration
 */
class ConfigService {
    constructor() {
        this.config = {
            // Detect environment
            isDevelopment: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1',
            isProduction: window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
        };
        
        this.loadConfig();
    }
    
    loadConfig() {
        // Set API base URL based on environment
        if (this.config.isDevelopment) {
            this.config.API_BASE_URL = 'http://localhost:5000';
        } else {
            // Production URL - should be set via environment variables
            this.config.API_BASE_URL = window.location.origin.replace('8002', '5000');
        }
        
        console.log(`Environment: ${this.config.isDevelopment ? 'Development' : 'Production'}`);
        console.log(`API Base URL: ${this.config.API_BASE_URL}`);
    }
    
    get(key) {
        return this.config[key];
    }
    
    getApiUrl(endpoint) {
        return `${this.config.API_BASE_URL}${endpoint}`;
    }
}

// Create global config instance
window.ConfigService = new ConfigService();

// Debug: Log that ConfigService is loaded
console.log('ConfigService loaded successfully');
console.log('ConfigService.getApiUrl method available:', typeof window.ConfigService.getApiUrl === 'function');

// Helper function to get API URL with fallback
window.getApiUrl = function(endpoint) {
    if (window.ConfigService && typeof window.ConfigService.getApiUrl === 'function') {
        return window.ConfigService.getApiUrl(endpoint);
    } else {
        // Fallback to hardcoded URL for development
        console.warn('ConfigService not available, using fallback URL');
        return `http://localhost:5000${endpoint}`;
    }
};
