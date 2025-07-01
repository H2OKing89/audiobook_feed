const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Create Express app
const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Path to Python module
const PYTHON_PATH = path.resolve(__dirname, '../../audiostracker');

// Serve static Vue files (will be used in production)
app.use(express.static(path.join(__dirname, '../frontend/dist')));

// API endpoint to search audiobooks
app.post('/api/search', (req, res) => {
  const { query, searchType } = req.body;
  
  if (!query) {
    return res.status(400).json({ error: 'Search query is required' });
  }

  // We'll execute the Python script with our search parameters
  const pythonProcess = spawn('python3', [
    '-c', 
    `import sys; sys.path.append('${PYTHON_PATH}'); from audible import search_audible; import json; print(json.dumps(search_audible('${query}', search_type='${searchType || 'author'}')))`
  ]);
  
  let dataString = '';
  
  pythonProcess.stdout.on('data', data => {
    dataString += data.toString();
  });
  
  pythonProcess.stderr.on('data', data => {
    console.error(`Python stderr: ${data}`);
  });
  
  pythonProcess.on('close', code => {
    if (code !== 0) {
      return res.status(500).json({ error: 'Search failed', code });
    }
    
    try {
      const results = JSON.parse(dataString);
      res.json(results);
    } catch (e) {
      console.error('Error parsing results:', e);
      res.status(500).json({ error: 'Failed to parse search results', details: dataString });
    }
  });
});

// API endpoint to get feed list
app.get('/api/feeds', (req, res) => {
  // For now, we'll read the audiobooks.yaml file to get the feed list
  const yamlPath = path.join(PYTHON_PATH, 'config', 'audiobooks.yaml');
  
  const pythonProcess = spawn('python3', [
    '-c', 
    `import sys; sys.path.append('${PYTHON_PATH}'); from utils import load_yaml; import json; print(json.dumps(load_yaml('${yamlPath}')))`
  ]);
  
  let dataString = '';
  
  pythonProcess.stdout.on('data', data => {
    dataString += data.toString();
  });
  
  pythonProcess.stderr.on('data', data => {
    console.error(`Python stderr: ${data}`);
  });
  
  pythonProcess.on('close', code => {
    if (code !== 0) {
      return res.status(500).json({ error: 'Failed to load feeds', code });
    }
    
    try {
      const feeds = JSON.parse(dataString);
      res.json(feeds);
    } catch (e) {
      console.error('Error parsing feeds:', e);
      res.status(500).json({ error: 'Failed to parse feeds', details: dataString });
    }
  });
});

// API endpoint to create/update a feed
app.post('/api/feeds', (req, res) => {
  const { author, series, books } = req.body;
  
  if (!author) {
    return res.status(400).json({ error: 'Author is required' });
  }
  
  // We'll update the audiobooks.yaml file with the new feed
  // This is a simplified implementation - in a real app, you'd want more validation and error handling
  const yamlPath = path.join(PYTHON_PATH, 'config', 'audiobooks.yaml');
  
  const pythonProcess = spawn('python3', [
    '-c', 
    `
import sys; sys.path.append('${PYTHON_PATH}');
from utils import load_yaml; 
import yaml;
import json;

# Load current feeds
feeds = load_yaml('${yamlPath}')

# Add or update feed
new_feed = ${JSON.stringify({ author, series, books })}
author_name = new_feed["author"]

# Check if author already exists
author_exists = False
for idx, feed in enumerate(feeds):
    if feed.get("author") == author_name:
        feeds[idx] = new_feed
        author_exists = True
        break

if not author_exists:
    feeds.append(new_feed)

# Save back to YAML
with open('${yamlPath}', 'w') as f:
    yaml.dump(feeds, f)

print(json.dumps({"success": True}))`
  ]);
  
  let dataString = '';
  
  pythonProcess.stdout.on('data', data => {
    dataString += data.toString();
  });
  
  pythonProcess.stderr.on('data', data => {
    console.error(`Python stderr: ${data}`);
  });
  
  pythonProcess.on('close', code => {
    if (code !== 0) {
      return res.status(500).json({ error: 'Failed to update feed', code });
    }
    
    try {
      const result = JSON.parse(dataString);
      res.json(result);
    } catch (e) {
      console.error('Error saving feed:', e);
      res.status(500).json({ error: 'Failed to save feed', details: dataString });
    }
  });
});

// Catch-all route to serve Vue.js app (for client-side routing)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/dist/index.html'));
});

// Start the server
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
