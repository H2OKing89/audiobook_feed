const express = require('express');
const router = express.Router();

// Import route modules
const audiostacker = require('./audiostacker');
const database = require('./database');

// Register routes
router.use('/audiostacker', audiostacker);
router.use('/database', database);

// Version info endpoint
router.get('/', (req, res) => {
  res.json({
    version: 'v1',
    status: 'active',
    endpoints: [
      '/audiostacker/status',
      '/audiostacker/watchlist',
      '/audiostacker/run',
      '/audiostacker/prune',
      '/database',
      '/database/:asin'
    ]
  });
});

module.exports = router;
