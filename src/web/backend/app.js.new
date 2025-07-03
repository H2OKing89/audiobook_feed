const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const dotenv = require('dotenv');

// Load environment variables from .env file
dotenv.config();

// Create Express app
const app = express();
const port = process.env.PORT || 5005;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static Vue files (only in production mode when dist exists)
const distPath = path.join(__dirname, '../frontend/dist');
if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
}

// Import API routes
const v1Routes = require('./routes/v1');

// Register API routes with versioning
app.use('/api/v1', v1Routes);

// Legacy API support - redirect old routes to versioned ones
app.use('/api/audiostacker', (req, res, next) => {
  console.log('Legacy route detected: /api/audiostacker, redirecting to /api/v1/audiostacker');
  req.url = req.url;
  app.handle(Object.assign({}, req, { url: `/api/v1/audiostacker${req.url}` }), res, next);
});

app.use('/api/database', (req, res, next) => {
  console.log('Legacy route detected: /api/database, redirecting to /api/v1/database');
  req.url = req.url;
  app.handle(Object.assign({}, req, { url: `/api/v1/database${req.url}` }), res, next);
});

// API version information
app.get('/api', (req, res) => {
  res.json({
    name: 'AudioStacker API',
    versions: ['v1'],
    current: 'v1',
    endpoints: ['/api/v1/audiostacker', '/api/v1/database'],
    legacy_support: true
  });
});

// Catch 404s and forward to error handler
app.use((req, res, next) => {
  res.status(404).json({
    error: 'Not Found',
    message: `The requested endpoint ${req.originalUrl} does not exist`,
    available_endpoints: ['/api', '/api/v1']
  });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('API Error:', err);
  res.status(err.status || 500).json({
    error: err.message || 'Internal Server Error',
    status: err.status || 500
  });
});

// Start the server
app.listen(port, () => {
  console.log(`AudioStacker backend listening on port ${port}`);
  console.log(`API available at http://localhost:${port}/api`);
});

module.exports = app;
