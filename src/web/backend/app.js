const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Create Express app
const app = express();
const port = process.env.PORT || 5005;

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

  console.log(`Searching for "${query}" with type "${searchType || 'author'}"`);

  // We'll execute the Python script with our search parameters
  // Use a Python file for better error handling and escaping of special characters
  const tempScriptPath = path.join(os.tmpdir(), `search_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
sys.path.insert(0, '${PYTHON_PATH}')
sys.path.insert(0, '${path.dirname(PYTHON_PATH)}')
os.chdir('${PYTHON_PATH}')

# Import with absolute imports to avoid relative import issues
try:
    import audible
    import utils
    import json
    
    # Monkey patch the imports to avoid relative import issues
    audible.retry_with_exponential_backoff = utils.retry_with_exponential_backoff
    audible.normalize_string = utils.normalize_string
    audible.normalize_list = utils.normalize_list
    audible.fuzzy_ratio = utils.fuzzy_ratio
    
    # Map frontend search types to backend field names
    search_field_map = {
        "author": "author",
        "title": "title", 
        "series": "title",  # Search in title for series
        "narrator": "narrator"
    }
    
    search_field = search_field_map.get("${searchType || 'author'}", "author")
    results = audible.search_audible("${query.replace(/"/g, '\\"')}", search_field=search_field)
    print(json.dumps(results))
except ImportError as ie:
    # Fallback: try to import everything directly without relative imports
    import json
    print(json.dumps({"error": f"Import error: {str(ie)}", "message": "Search functionality temporarily unavailable"}))
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    print(json.dumps({"error": str(e), "traceback": error_details}))
`;

  fs.writeFileSync(tempScriptPath, scriptContent);
  const pythonProcess = spawn('python3', [tempScriptPath]);
  
  let dataString = '';
  
  pythonProcess.stdout.on('data', data => {
    dataString += data.toString();
  });
  
  pythonProcess.stderr.on('data', data => {
    console.error(`Python stderr: ${data}`);
  });
  
  pythonProcess.on('close', code => {
    // Clean up the temp file
    try {
      fs.unlinkSync(tempScriptPath);
    } catch (err) {
      console.error('Error deleting temp script:', err);
    }
    
    if (code !== 0) {
      return res.status(500).json({ error: 'Search failed', code });
    }
    
    try {
      const results = JSON.parse(dataString);
      
      // If Python returned an error
      if (results.error) {
        return res.status(500).json({ error: results.error });
      }
      
      // Format the results for the frontend
      const formattedResults = {
        authors: [],
        series: [],
        books: [],
        narrators: []
      };
      
      // Process the results based on the type
      if (Array.isArray(results)) {
        results.forEach(item => {
          if (item.asin) {
            const book = {
              title: item.title || 'Unknown Title',
              author: item.author || 'Unknown Author',
              narrator: item.narrator || 'Unknown Narrator',
              publisher: item.publisher || 'Unknown Publisher',
              series: item.series || '',
              seriesNumber: item.series_number || '',
              releaseDate: item.release_date || '',
              cover: item.image_url || '',
              summary: item.summary || '',
              asin: item.asin
            };
            
            formattedResults.books.push(book);
            
            // Add author if not already in list
            if (item.author && !formattedResults.authors.find(a => a.name === item.author)) {
              formattedResults.authors.push({
                name: item.author,
                bookCount: 1
              });
            } else if (item.author) {
              const authorIndex = formattedResults.authors.findIndex(a => a.name === item.author);
              if (authorIndex !== -1) {
                formattedResults.authors[authorIndex].bookCount += 1;
              }
            }
            
            // Add series if not already in list
            if (item.series && !formattedResults.series.find(s => s.name === item.series)) {
              formattedResults.series.push({
                name: item.series,
                author: item.author || 'Unknown',
                bookCount: 1
              });
            } else if (item.series) {
              const seriesIndex = formattedResults.series.findIndex(s => s.name === item.series);
              if (seriesIndex !== -1) {
                formattedResults.series[seriesIndex].bookCount += 1;
              }
            }
            
            // Add narrator if not already in list
            if (item.narrator && !formattedResults.narrators.find(n => n.name === item.narrator)) {
              formattedResults.narrators.push({
                name: item.narrator,
                bookCount: 1
              });
            } else if (item.narrator) {
              const narratorIndex = formattedResults.narrators.findIndex(n => n.name === item.narrator);
              if (narratorIndex !== -1) {
                formattedResults.narrators[narratorIndex].bookCount += 1;
              }
            }
          }
        });
      }
      
      res.json(formattedResults);
    } catch (e) {
      console.error('Error parsing results:', e);
      res.status(500).json({ error: 'Failed to parse search results', details: dataString });
    }
  });
});

// Setup feed storage
const FEEDS_DB_PATH = path.join(__dirname, 'feeds.json');

// Initialize feeds database if it doesn't exist
if (!fs.existsSync(FEEDS_DB_PATH)) {
  fs.writeFileSync(FEEDS_DB_PATH, JSON.stringify([
    {
      id: 1,
      name: "Fantasy Favorites",
      description: "My favorite fantasy authors and series",
      content: [
        { type: "author", name: "Brandon Sanderson" },
        { type: "series", name: "The Stormlight Archive" }
      ]
    },
    {
      id: 2,
      name: "Sci-Fi Collection",
      description: "Science fiction books I follow",
      content: [
        { type: "author", name: "Andy Weir" },
        { type: "series", name: "Bobiverse", author: "Dennis E. Taylor" }
      ]
    }
  ]));
}

// Helper function to read feeds
function getFeeds() {
  try {
    return JSON.parse(fs.readFileSync(FEEDS_DB_PATH, 'utf8'));
  } catch (err) {
    console.error('Error reading feeds database:', err);
    return [];
  }
}

// Helper function to save feeds
function saveFeeds(feeds) {
  try {
    fs.writeFileSync(FEEDS_DB_PATH, JSON.stringify(feeds, null, 2));
    return true;
  } catch (err) {
    console.error('Error saving feeds database:', err);
    return false;
  }
}

// API endpoint to get feed list
app.get('/api/feeds', (req, res) => {
  try {
    const feeds = getFeeds();
    res.json(feeds);
  } catch (err) {
    res.status(500).json({ error: 'Failed to load feeds', details: err.message });
  }
});

// API endpoint to create/update a feed
app.post('/api/feeds', (req, res) => {
  const { id, name, description, content } = req.body;
  
  if (!name) {
    return res.status(400).json({ error: 'Feed name is required' });
  }
  
  try {
    const feeds = getFeeds();
    
    if (id) {
      // Update existing feed
      const index = feeds.findIndex(feed => feed.id === id);
      if (index !== -1) {
        feeds[index] = { 
          ...feeds[index], 
          name, 
          description, 
          content,
          updatedAt: new Date().toISOString()
        };
      } else {
        return res.status(404).json({ error: 'Feed not found' });
      }
    } else {
      // Create new feed
      const newId = feeds.length > 0 ? Math.max(...feeds.map(feed => feed.id)) + 1 : 1;
      feeds.push({
        id: newId,
        name,
        description,
        content: content || [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      });
    }
    
    if (saveFeeds(feeds)) {
      // Also update the audiobooks.yaml file with the feed data if needed
      try {
        updateAudiobooksYaml(feeds);
      } catch (err) {
        console.warn('Warning: Failed to update audiobooks.yaml:', err);
      }
      
      res.json({ success: true, feeds });
    } else {
      res.status(500).json({ error: 'Failed to save feeds' });
    }
  } catch (err) {
    res.status(500).json({ error: 'Failed to process feed', details: err.message });
  }
});

// API endpoint to delete a feed
app.delete('/api/feeds/:id', (req, res) => {
  const feedId = parseInt(req.params.id);
  
  try {
    let feeds = getFeeds();
    const initialLength = feeds.length;
    
    feeds = feeds.filter(feed => feed.id !== feedId);
    
    if (feeds.length === initialLength) {
      return res.status(404).json({ error: 'Feed not found' });
    }
    
    if (saveFeeds(feeds)) {
      res.json({ success: true });
    } else {
      res.status(500).json({ error: 'Failed to delete feed' });
    }
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete feed', details: err.message });
  }
});

// Helper function to update the audiobooks.yaml file with feed data
function updateAudiobooksYaml(feeds) {
  // Convert feeds to the format expected by audiobooks.yaml
  const audiobookEntries = [];
  
  feeds.forEach(feed => {
    // For each author in the feed
    const authorEntries = feed.content.filter(item => item.type === 'author');
    
    authorEntries.forEach(authorEntry => {
      const authorName = authorEntry.name;
      
      // Find all series and books for this author in the feed
      const authorSeries = feed.content
        .filter(item => item.type === 'series' && (!item.author || item.author === authorName))
        .map(item => item.name);
        
      const authorBooks = feed.content
        .filter(item => item.type === 'book' && (!item.author || item.author === authorName))
        .map(item => item.name);
        
      audiobookEntries.push({
        author: authorName,
        series: authorSeries.length > 0 ? authorSeries : undefined,
        title: authorBooks.length > 0 ? authorBooks : undefined
      });
    });
  });
  
  // Write to a temp Python script to update the YAML file
  const yamlPath = path.join(PYTHON_PATH, 'config', 'audiobooks.yaml');
  const tempScriptPath = path.join(os.tmpdir(), `update_yaml_${Date.now()}.py`);
  
  const scriptContent = `
import sys
sys.path.append('${PYTHON_PATH}')
import yaml
import json

audiobook_entries = ${JSON.stringify(audiobookEntries)}

with open('${yamlPath}', 'w') as f:
    yaml.dump(audiobook_entries, f)

print(json.dumps({"success": True}))
`;

  fs.writeFileSync(tempScriptPath, scriptContent);
  
  return new Promise((resolve, reject) => {
    const pythonProcess = spawn('python3', [tempScriptPath]);
    
    let dataString = '';
    
    pythonProcess.stdout.on('data', data => {
      dataString += data.toString();
    });
    
    pythonProcess.stderr.on('data', data => {
      console.error(`Python stderr: ${data}`);
    });
    
    pythonProcess.on('close', code => {
      // Clean up the temp file
      try {
        fs.unlinkSync(tempScriptPath);
      } catch (err) {
        console.error('Error deleting temp script:', err);
      }
      
      if (code !== 0) {
        reject(new Error(`Python process exited with code ${code}`));
      } else {
        try {
          const result = JSON.parse(dataString);
          resolve(result);
        } catch (e) {
          reject(e);
        }
      }
    });
  });
}

// Catch-all route to serve Vue.js app (for client-side routing)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/dist/index.html'));
});

// Start the server
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
