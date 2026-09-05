// API Configuration
// Automatically detects environment and uses appropriate base URL

// In production (Render static site), Vite replaces import.meta.env.PROD with true
// In development, it uses the Vite proxy at /api
export const API_BASE_URL = import.meta.env.PROD
  ? 'https://tata-ai-backend-og7t.onrender.com/api/v1'
  : '/api';