const express = require('express');
const app = express();

app.use(express.json());

app.get('/test', (req, res) => {
  res.json({ message: 'Test endpoint works' });
});

app.get('/api/status', (req, res) => {
  res.json({ status: 'ok', message: 'API is working' });
});

// Add our AudioStacker endpoints
app.get('/api/audiostacker/status', (req, res) => {
  res.json({ message: 'AudioStacker status endpoint works' });
});

app.get('/api/audiostacker/watchlist', (req, res) => {
  res.json({ message: 'AudioStacker watchlist endpoint works' });
});

app.post('/api/audiostacker/watchlist', (req, res) => {
  res.json({ message: 'AudioStacker add watchlist endpoint works' });
});

app.put('/api/audiostacker/watchlist/:id', (req, res) => {
  res.json({ message: 'AudioStacker update watchlist endpoint works', id: req.params.id });
});

app.delete('/api/audiostacker/watchlist/:id', (req, res) => {
  res.json({ message: 'AudioStacker delete watchlist endpoint works', id: req.params.id });
});

app.post('/api/audiostacker/run', (req, res) => {
  res.json({ message: 'AudioStacker run endpoint works' });
});

// Print all registered routes
console.log('Registered routes:');
app._router.stack.forEach((layer) => {
  if (layer.route) {
    const path = layer.route.path;
    const methods = Object.keys(layer.route.methods).map(m => m.toUpperCase()).join(',');
    console.log(`${methods} ${path}`);
  }
});

app.get('*', (req, res) => {
  res.status(404).json({ error: 'Endpoint not found', path: req.path });
});

const PORT = 5007; // Use a different port
app.listen(PORT, () => {
  console.log(`Test server running on port ${PORT}`);
});
