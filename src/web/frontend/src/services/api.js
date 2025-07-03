import axios from 'axios';

// Create base API configuration with environment variables or fallback defaults
const API_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:5005';
const API_VERSION = 'v1';
const API_TIMEOUT = 30000; // 30 seconds timeout

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: `${API_URL}/api/${API_VERSION}`,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

// Request interceptor for logging and headers
apiClient.interceptors.request.use(
  config => {
    // Log request details in development mode
    if (process.env.NODE_ENV === 'development') {
      console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  error => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for global error handling
apiClient.interceptors.response.use(
  response => {
    return response;
  },
  error => {
    // Handle specific error types
    if (error.code === 'ECONNABORTED') {
      console.error('API Request Timeout');
      // Could dispatch to a global error store here
    } else if (!error.response) {
      console.error('Network Error: No response from server');
      // Could dispatch to a global error store here
    } else {
      // Handle specific status codes
      switch (error.response.status) {
        case 400:
          console.error('Bad Request:', error.response.data);
          break;
        case 401:
          console.error('Unauthorized');
          // Could redirect to login page or refresh token
          break;
        case 403:
          console.error('Forbidden');
          break;
        case 404:
          console.error('Resource Not Found:', error.response.config.url);
          break;
        case 500:
          console.error('Server Error:', error.response.data);
          break;
        default:
          console.error(`Error ${error.response.status}:`, error.response.data);
      }
    }
    return Promise.reject(error);
  }
);

// Retry mechanism for failed requests
const withRetry = async (apiCall, retries = 2, delay = 1000) => {
  try {
    return await apiCall();
  } catch (error) {
    // Only retry on network errors or 5xx server errors
    if (
      retries > 0 && 
      (
        !error.response || 
        (error.response && error.response.status >= 500)
      )
    ) {
      console.log(`Retrying API call, ${retries} attempts left`);
      await new Promise(resolve => setTimeout(resolve, delay));
      return withRetry(apiCall, retries - 1, delay * 1.5);
    }
    throw error;
  }
};

// API Service object with methods for each endpoint
const apiService = {
  // Status endpoints
  getStatus() {
    return withRetry(() => apiClient.get('/audiostacker/status'));
  },
  
  // Watchlist endpoints
  getWatchlist() {
    return withRetry(() => apiClient.get('/audiostacker/watchlist'));
  },
  
  addToWatchlist(authorData) {
    return withRetry(() => apiClient.post('/audiostacker/watchlist', authorData));
  },
  
  updateWatchlist(authorData) {
    return withRetry(() => apiClient.put('/audiostacker/watchlist', authorData));
  },
  
  removeFromWatchlist(authorName) {
    return withRetry(() => apiClient.delete('/audiostacker/watchlist', { 
      params: { author: authorName } 
    }));
  },
  
  // Database endpoints
  getDatabaseBooks() {
    return withRetry(() => apiClient.get('/database'));
  },
  
  deleteBook(asin) {
    return withRetry(() => apiClient.delete(`/database/${asin}`));
  },
  
  // Run and maintenance endpoints
  runAudiostacker(dryRun = false) {
    return withRetry(() => apiClient.post('/audiostacker/run', { dryRun }));
  },
  
  pruneDatabase() {
    return withRetry(() => apiClient.post('/audiostacker/prune'));
  }
};

export default apiService;
