const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const AudiobookMatcher = require('./matching');

// Create Express app
const app = express();
const port = process.env.PORT || 5005;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Path to Python module
const PYTHON_PATH = path.resolve(__dirname, '../../audiostracker');

// Initialize matcher
const matcher = new AudiobookMatcher();

// Serve static Vue files (only in production mode when dist exists)
const distPath = path.join(__dirname, '../frontend/dist');
if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
}

// API endpoint to search audiobooks - functionality removed
app.post('/api/search', (req, res) => {
  res.status(410).json({ 
    message: 'Search functionality has been removed',
    status: 'deprecated' 
  });

  // First, execute the Python script to get raw search results
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
      
      // Apply confidence-based matching if enabled
      let processedResults = results;
      if (useMatching && Array.isArray(results)) {
        console.log(`Applying confidence-based matching to ${results.length} raw results`);
        
        // Create a "wanted" search criteria based on the query
        const wanted = {};
        switch (searchType) {
          case 'author':
            wanted.author = query;
            break;
          case 'title':
            wanted.title = query;
            break;
          case 'series':
            wanted.series = query;
            break;
          case 'narrator':
            wanted.narrator = query;
            break;
          default:
            wanted.author = query;
        }
        
        // Apply confidence-based filtering
        processedResults = matcher.findAllGoodMatches(results, wanted, minConfidence);
        console.log(`Confidence matching filtered to ${processedResults.length} good matches`);
      }
      
      // Format the results for the frontend
      const formattedResults = {
        authors: [],
        series: [],
        books: [],
        narrators: [],
        meta: {
          totalRawResults: Array.isArray(results) ? results.length : 0,
          totalFilteredResults: Array.isArray(processedResults) ? processedResults.length : 0,
          matchingEnabled: useMatching,
          minConfidence: minConfidence
        }
      };
      
      // Process the results based on the type
      if (Array.isArray(processedResults)) {
        processedResults.forEach(item => {
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
              asin: item.asin,
              // Include confidence scoring metadata if available
              confidenceScore: item.confidenceScore || null,
              needsReview: item.needsReview || false
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

// AudioStacker uses the database-based watchlist system as the primary mechanism
// for tracking audiobook releases. The feeds system has been removed to simplify
// the application and focus on the core functionality.

// COMMENTED OUT - duplicate fallback route
// Catch-all route to serve Vue.js app (for client-side routing)
/*
app.get('*', (req, res) => {
  const distPathFallback = path.join(__dirname, '../frontend/dist/index.html');
  if (fs.existsSync(distPathFallback)) {
    res.sendFile(distPathFallback);
  } else {
    // In development mode, just return a simple message for non-API routes
    if (req.path.startsWith('/api/')) {
      res.status(404).json({ error: 'API endpoint not found' });
    } else {
      res.status(200).json({ 
        message: 'Backend is running', 
        note: 'Frontend is running separately on port 5006' 
      });
    }
  }
});
*/

// API endpoint to apply confidence-based matching to results - functionality removed
app.post('/api/match', (req, res) => {
  console.log('Match endpoint called, but functionality has been removed');
  res.status(410).json({ 
    message: 'Matching functionality has been removed',
    status: 'deprecated' 
  });
});

// AudioStacker Core API Endpoints

// Get system status and database stats
app.get('/api/status', async (req, res) => {
  try {
    const tempScriptPath = path.join(os.tmpdir(), `status_script_${Date.now()}.py`);
    const scriptContent = `
import sys
import os
import json
import sqlite3
from datetime import datetime

sys.path.insert(0, '${PYTHON_PATH}')
os.chdir('${PYTHON_PATH}')

try:
    # Get database stats
    db_path = 'audiobooks.db'
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Count total books
        cursor.execute("SELECT COUNT(*) FROM audiobooks")
        total_books = cursor.fetchone()[0]
        
        # Count upcoming releases (future release dates)
        cursor.execute("SELECT COUNT(*) FROM audiobooks WHERE release_date >= date('now')")
        upcoming_releases = cursor.fetchone()[0]
        
        # Count notified books
        cursor.execute("SELECT COUNT(*) FROM audiobooks WHERE notified_channels != '{}'")
        notified_books = cursor.fetchone()[0]
        
        # Get most recent check
        cursor.execute("SELECT MAX(last_checked) FROM audiobooks")
        last_check = cursor.fetchone()[0] or "Never"
        
        conn.close();
        
        status = {
            "database": {
                "total_books": total_books,
                "upcoming_releases": upcoming_releases,
                "notified_books": notified_books,
                "last_check": last_check
            },
            "system": {
                "current_time": datetime.now().isoformat(),
                "database_exists": True
            }
        }
    else:
        status = {
            "database": {
                "total_books": 0,
                "upcoming_releases": 0,
                "notified_books": 0,
                "last_check": "Never"
            },
            "system": {
                "current_time": datetime.now().isoformat(),
                "database_exists": False
            }
        }
    
    print(json.dumps(status))
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
      try {
        fs.unlinkSync(tempScriptPath);
      } catch (err) {
        console.error('Error deleting temp script:', err);
      }
      
      if (code !== 0) {
        return res.status(500).json({ error: 'Status check failed', code });
      }
      
      try {
        const status = JSON.parse(dataString);
        if (status.error) {
          return res.status(500).json({ error: status.error });
        }
        res.json(status);
      } catch (e) {
        console.error('Error parsing status:', e);
        res.status(500).json({ error: 'Failed to parse status', details: dataString });
      }
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to get status', details: error.message });
  }
});

// Get watch-list (authors from audiobooks.yaml)
app.get('/api/watchlist', (req, res) => {
  try {
    const audiobooksYamlPath = path.join(PYTHON_PATH, 'config', 'audiobooks.yaml');
    
    if (!fs.existsSync(audiobooksYamlPath)) {
      return res.json({ audiobooks: { author: {} } });
    }
    
    const tempScriptPath = path.join(os.tmpdir(), `watchlist_script_${Date.now()}.py`);
    const scriptContent = `
import sys
import os
import json
import yaml

sys.path.insert(0, '${PYTHON_PATH}')
os.chdir('${PYTHON_PATH}')

try:
    with open('config/audiobooks.yaml', 'r') as f:
        data = yaml.safe_load(f)
    print(json.dumps(data or {}))
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
      try {
        fs.unlinkSync(tempScriptPath);
      } catch (err) {
        console.error('Error deleting temp script:', err);
      }
      
      if (code !== 0) {
        return res.status(500).json({ error: 'Watchlist load failed', code });
      }
      
      try {
        const watchlist = JSON.parse(dataString);
        if (watchlist.error) {
          return res.status(500).json({ error: watchlist.error });
        }
        res.json(watchlist);
      } catch (e) {
        console.error('Error parsing watchlist:', e);
        res.status(500).json({ error: 'Failed to parse watchlist', details: dataString });
      }
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to get watchlist', details: error.message });
  }
});

// Run AudioStacker workflow manually
app.post('/api/audiostacker/run', (req, res) => {
  const { dryRun = false } = req.body;
  
  console.log(`Starting AudioStacker run (dry run: ${dryRun})`);
  
  const tempScriptPath = path.join(os.tmpdir(), `run_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
import json
from datetime import datetime

# Fix Python path to avoid relative import issues
parent_dir = os.path.dirname('${PYTHON_PATH}')
sys.path.insert(0, parent_dir)
os.chdir('${PYTHON_PATH}')

try:
    # Fix relative imports by importing from the parent package
    from audiostracker import main
    
    # Capture the run results
    start_time = datetime.now()
    
    if ${dryRun ? 'True' : 'False'}:
        # For dry run, just load config and show what would be processed
        from audiostracker import utils
        from audiostracker import database
        # The config file is in the config subdirectory
        config_path = os.path.join('${PYTHON_PATH}', 'config', 'config.yaml')
        config = utils.load_yaml(config_path) if os.path.exists(config_path) else {}
        watchlist = database.get_watchlist()
        
        result = {
            "dry_run": True,
            "watchlist": watchlist,
            "config_loaded": True,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    else:
        # Run the actual main function
        result = main.main();
        if result is None:
            result = {"status": "completed", "message": "AudioStacker run completed successfully"}
        
        result.update({
            "dry_run": False,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        })
    
    print(json.dumps(result))
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    result = {
        "error": str(e),
        "traceback": error_details,
        "dry_run": ${dryRun ? 'True' : 'False'},
        "start_time": start_time.isoformat() if 'start_time' in locals() else None,
        "end_time": datetime.now().isoformat()
    }
    print(json.dumps(result))
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
    try {
      fs.unlinkSync(tempScriptPath);
    } catch (err) {
      console.error('Error deleting temp script:', err);
    }
    
    // Only try to parse JSON from the last line, in case there's other output
    const lines = dataString.trim().split('\n');
    const lastLine = lines[lines.length - 1];
    
    try {
      const result = JSON.parse(lastLine);
      res.json(result);
    } catch (e) {
      console.error('Error parsing run result:', e);
      console.error('Raw output:', dataString);
      
      // If the script ran successfully but didn't return valid JSON
      if (code === 0) {
        res.json({ 
          status: "completed", 
          message: "AudioStacker run completed successfully",
          raw_output: dataString.substring(0, 1000) // Limit size of raw output
        });
      } else {
        res.status(500).json({ 
          error: 'Failed to run AudioStacker', 
          details: dataString.substring(0, 1000), // Limit size of raw output
          exit_code: code 
        });
      }
    }
  });
});

// Get database contents
app.get('/api/database', (req, res) => {
  const { filter = 'all', limit = 100, offset = 0 } = req.query;
  
  const tempScriptPath = path.join(os.tmpdir(), `database_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
import json
import sqlite3
from datetime import datetime, date

sys.path.insert(0, '${PYTHON_PATH}')
os.chdir('${PYTHON_PATH}')

try:
    db_path = 'audiobooks.db'
    if not os.path.exists(db_path):
        print(json.dumps({"books": [], "total": 0, "message": "Database not found"}))
        exit()
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor();
    
    # Build query based on filter
    base_query = "SELECT * FROM audiobooks"
    count_query = "SELECT COUNT(*) FROM audiobooks"
    
    if "${filter}" == "upcoming":
        where_clause = " WHERE release_date >= date('now')"
    elif "${filter}" == "notified":
        where_clause = " WHERE notified_channels != '{}'"
    elif "${filter}" == "unnotified":
        where_clause = " WHERE notified_channels = '{}'"
    else:
        where_clause = ""
    
    # Get total count
    cursor.execute(count_query + where_clause);
    total = cursor.fetchone()[0];
    
    # Get paginated results
    query = base_query + where_clause + " ORDER BY release_date DESC LIMIT ${limit} OFFSET ${offset}"
    cursor.execute(query);
    
    books = [];
    for row in cursor.fetchall():
        book = dict(row);
        # Parse notified_channels JSON
        try:
            book['notified_channels'] = json.loads(book['notified_channels'] or '{}');
        except:
            book['notified_channels'] = {};
        books.append(book);
    
    conn.close();
    
    result = {
        "books": books,
        "total": total,
        "filter": "${filter}",
        "limit": ${limit},
        "offset": ${offset}
    };
    
    print(json.dumps(result));
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
    try {
      fs.unlinkSync(tempScriptPath);
    } catch (err) {
      console.error('Error deleting temp script:', err);
    }
    
    if (code !== 0) {
      return res.status(500).json({ error: 'Database query failed', code });
    }
    
    try {
      const result = JSON.parse(dataString);
      if (result.error) {
        return res.status(500).json({ error: result.error });
      }
      res.json(result);
    } catch (e) {
      console.error('Error parsing database result:', e);
      res.status(500).json({ error: 'Failed to parse database result', details: dataString });
    }
  });
});

// AudioStacker API endpoints - mirroring the Python workflow
console.log('Registering AudioStacker API endpoints...');

// Get AudioStacker status and configuration
app.get('/api/audiostacker/status', (req, res) => {
  console.log('AudioStacker status endpoint called');
  try {
    const configPath = path.join(PYTHON_PATH, 'config', 'config.yaml');
    const audioConfigPath = path.join(PYTHON_PATH, 'config', 'audiobooks.yaml');
    
    const status = {
      configExists: fs.existsSync(configPath),
      audiobooksConfigExists: fs.existsSync(audioConfigPath),
      databasePath: path.join(PYTHON_PATH, 'audiobooks.db'),
      databaseExists: fs.existsSync(path.join(PYTHON_PATH, 'audiobooks.db')),
      lastRun: null, // Will implement with proper logging
      uptime: process.uptime(),
      version: "1.0.0"
    };
    
    res.json(status);
  } catch (error) {
    console.error('Error getting AudioStacker status:', error);
    res.status(500).json({ error: 'Failed to get status' });
  }
});

// Get watch-list from database
app.get('/api/audiostacker/watchlist', (req, res) => {
  try {
    const tempScriptPath = path.join(os.tmpdir(), `read_watchlist_${Date.now()}.py`);
    const scriptContent = `
import sys
import os
import json

# Fix Python path to avoid relative import issues
parent_dir = os.path.dirname('${PYTHON_PATH}')
sys.path.insert(0, parent_dir)
os.chdir('${PYTHON_PATH}')

try:
    from audiostracker.database import get_watchlist, convert_watchlist_to_yaml_format
    
    # Get watchlist in both formats
    db_watchlist = get_watchlist()
    yaml_format = convert_watchlist_to_yaml_format()
    
    # Convert to frontend-expected format and merge duplicate authors
    audiobooks_author = {}
    for entry in db_watchlist:
        author_name = entry['author_name']
        
        # Initialize author if not exists
        if author_name not in audiobooks_author:
            audiobooks_author[author_name] = {}
        
        # Parse and merge criteria
        if entry.get('title_filter'):
            include_items = entry['title_filter'].split(',')
            if 'include' not in audiobooks_author[author_name]:
                audiobooks_author[author_name]['include'] = []
            audiobooks_author[author_name]['include'].extend(include_items)
            
        if entry.get('series_filter'):
            series_items = entry['series_filter'].split(',')
            if 'series' not in audiobooks_author[author_name]:
                audiobooks_author[author_name]['series'] = []
            audiobooks_author[author_name]['series'].extend(series_items)
            
        if entry.get('publisher_filter'):
            publisher_items = entry['publisher_filter'].split(',')
            if 'publisher' not in audiobooks_author[author_name]:
                audiobooks_author[author_name]['publisher'] = []
            audiobooks_author[author_name]['publisher'].extend(publisher_items)
            
        if entry.get('narrator_filter'):
            narrator_items = entry['narrator_filter'].split(',')
            if 'narrator' not in audiobooks_author[author_name]:
                audiobooks_author[author_name]['narrator'] = []
            audiobooks_author[author_name]['narrator'].extend(narrator_items)
    
    # Remove duplicates from all criteria arrays
    for author_name in audiobooks_author:
        for criteria_type in audiobooks_author[author_name]:
            audiobooks_author[author_name][criteria_type] = list(set(audiobooks_author[author_name][criteria_type]))
    
    result = {
        "audiobooks": {
            "author": audiobooks_author
        },
        "watchlist": db_watchlist,
        "yaml_format": yaml_format,
        "total_entries": len(db_watchlist),
        "authors": list(set(entry['author_name'] for entry in db_watchlist))
    }
    
    print(json.dumps(result, default=str))
    
except Exception as e:
    import traceback
    print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
`;

    fs.writeFileSync(tempScriptPath, scriptContent);
    const pythonProcess = spawn('python3', [tempScriptPath]);
    
    let dataString = '';
    let errorString = '';
    
    pythonProcess.stdout.on('data', data => {
      dataString += data.toString();
    });
    
    pythonProcess.stderr.on('data', data => {
      errorString += data.toString();
    });
    
    pythonProcess.on('close', code => {
      fs.unlinkSync(tempScriptPath);
      
      if (code !== 0) {
        console.error('Python stderr:', errorString);
        return res.status(500).json({ error: 'Failed to read watchlist', stderr: errorString });
      }
      
      try {
        const result = JSON.parse(dataString);
        if (result.error) {
          return res.status(500).json({ error: result.error, traceback: result.traceback });
        }
        res.json(result);
      } catch (e) {
        console.error('Parse error:', e, 'Raw data:', dataString);
        res.status(500).json({ error: 'Failed to parse watchlist response' });
      }
    });
  } catch (error) {
    console.error('Error reading watchlist:', error);
    res.status(500).json({ error: 'Failed to read watchlist' });
  }
});

// Add watchlist entry
app.post('/api/audiostacker/watchlist', (req, res) => {
  try {
    // Extract data from the new frontend format
    const { author, criteria } = req.body;
    
    if (!author) {
      return res.status(400).json({ error: 'Author name is required' });
    }
    
    // Extract criteria fields
    let title_filter = null;
    let series_filter = null;
    let publisher_filter = null;
    let narrator_filter = null;
    
    if (criteria) {
      // Convert arrays to comma-separated strings for database storage
      if (criteria.include && Array.isArray(criteria.include)) {
        title_filter = criteria.include.join(',');
      }
      if (criteria.series && Array.isArray(criteria.series)) {
        series_filter = criteria.series.join(',');
      }
      if (criteria.publisher && Array.isArray(criteria.publisher)) {
        publisher_filter = criteria.publisher.join(',');
      }
      if (criteria.narrator && Array.isArray(criteria.narrator)) {
        narrator_filter = criteria.narrator.join(',');
      }
    }
    
    const tempScriptPath = path.join(os.tmpdir(), `add_watchlist_${Date.now()}.py`);
    const scriptContent = `
import sys
import os
import json

# Fix Python path to avoid relative import issues
parent_dir = os.path.dirname('${PYTHON_PATH}')
sys.path.insert(0, parent_dir)
os.chdir('${PYTHON_PATH}')

try:
    from audiostracker.database import add_watchlist_entry, get_watchlist, convert_watchlist_to_yaml_format, check_author_exists, get_author_criteria_summary
    
    # Check if author already exists
    author_check = check_author_exists("${author.replace(/"/g, '\\"')}")
    
    if author_check["exists"]:
        # Author exists, get their current criteria
        existing_criteria = get_author_criteria_summary("${author.replace(/"/g, '\\"')}")
        result = {
            "success": False,
            "author_exists": True,
            "author_name": "${author.replace(/"/g, '\\"')}",
            "existing_criteria": existing_criteria or {},
            "existing_entries_count": author_check["count"],
            "message": "Author already exists in watchlist. Use 'Update' to modify their criteria.",
            "suggestion": "Click 'Update' to modify the existing entry instead of creating a duplicate."
        }
        print(json.dumps(result))
    else:
        # Author doesn't exist, add them
        entry_id = add_watchlist_entry(
            "${author.replace(/"/g, '\\"')}",
            ${title_filter ? `"${title_filter.replace(/"/g, '\\"')}"` : 'None'},
            ${series_filter ? `"${series_filter.replace(/"/g, '\\"')}"` : 'None'},
            ${publisher_filter ? `"${publisher_filter.replace(/"/g, '\\"')}"` : 'None'},
            ${narrator_filter ? `"${narrator_filter.replace(/"/g, '\\"')}"` : 'None'}
        )
        
        # Return the updated watchlist in frontend-expected format
        db_watchlist = get_watchlist()
        yaml_format = convert_watchlist_to_yaml_format()
        
        # Convert to frontend-expected format and merge duplicate authors
        audiobooks_author = {}
        for entry in db_watchlist:
            author_name = entry['author_name']
            
            # Initialize author if not exists
            if author_name not in audiobooks_author:
                audiobooks_author[author_name] = {}
            
            # Parse and merge criteria
            if entry.get('title_filter'):
                include_items = entry['title_filter'].split(',')
                if 'include' not in audiobooks_author[author_name]:
                    audiobooks_author[author_name]['include'] = []
                audiobooks_author[author_name]['include'].extend(include_items)
                
            if entry.get('series_filter'):
                series_items = entry['series_filter'].split(',')
                if 'series' not in audiobooks_author[author_name]:
                    audiobooks_author[author_name]['series'] = []
                audiobooks_author[author_name]['series'].extend(series_items)
                
            if entry.get('publisher_filter'):
                publisher_items = entry['publisher_filter'].split(',')
                if 'publisher' not in audiobooks_author[author_name]:
                    audiobooks_author[author_name]['publisher'] = []
                audiobooks_author[author_name]['publisher'].extend(publisher_items)
                
            if entry.get('narrator_filter'):
                narrator_items = entry['narrator_filter'].split(',')
                if 'narrator' not in audiobooks_author[author_name]:
                    audiobooks_author[author_name]['narrator'] = []
                audiobooks_author[author_name]['narrator'].extend(narrator_items)
        
        # Remove duplicates from all criteria arrays
        for author_name in audiobooks_author:
            for criteria_type in audiobooks_author[author_name]:
                audiobooks_author[author_name][criteria_type] = list(set(audiobooks_author[author_name][criteria_type]))
        
        result = {
            "success": True,
            "entry_id": entry_id,
            "message": "Entry updated" if entry_id is None else "Entry added",
            "audiobooks": {
                "author": audiobooks_author
            },
            "watchlist": db_watchlist,
        "yaml_format": yaml_format,
        "total_entries": len(db_watchlist),
        "authors": list(set(entry['author_name'] for entry in db_watchlist))
    }
    print(json.dumps(result))
    
except Exception as e:
    import traceback
    print(json.dumps({"success": False, "error": str(e), "traceback": traceback.format_exc()}))
`;

    fs.writeFileSync(tempScriptPath, scriptContent);
    const pythonProcess = spawn('python3', [tempScriptPath]);
    
    let dataString = '';
    let errorString = '';
    
    pythonProcess.stdout.on('data', data => {
      dataString += data.toString();
    });
    
    pythonProcess.stderr.on('data', data => {
      errorString += data.toString();
    });
    
    pythonProcess.on('close', code => {
      fs.unlinkSync(tempScriptPath);
      
      try {
        const result = JSON.parse(dataString);
        if (result.success) {
          res.json(result);
        } else {
          console.error('Python error:', result.error);
          res.status(500).json({ error: result.error, traceback: result.traceback });
        }
      } catch (e) {
        console.error('Parse error:', e, 'Raw data:', dataString, 'Stderr:', errorString);
        res.status(500).json({ error: 'Failed to parse response' });
      }
    });
  } catch (error) {
    console.error('Error adding watchlist entry:', error);
    res.status(500).json({ error: 'Failed to add watchlist entry' });
  }
});

// Update watchlist entry - change from ID-based to author-based
app.put('/api/audiostacker/watchlist', (req, res) => {
  try {
    const { author, criteria } = req.body;
    
    if (!author) {
      return res.status(400).json({ error: 'Author name is required' });
    }
    
    // Extract criteria fields
    let title_filter = null;
    let series_filter = null;
    let publisher_filter = null;
    let narrator_filter = null;
    
    if (criteria) {
      // Convert arrays to comma-separated strings for database storage
      if (criteria.include && Array.isArray(criteria.include)) {
        title_filter = criteria.include.join(',');
      }
      if (criteria.series && Array.isArray(criteria.series)) {
        series_filter = criteria.series.join(',');
      }
      if (criteria.publisher && Array.isArray(criteria.publisher)) {
        publisher_filter = criteria.publisher.join(',');
      }
      if (criteria.narrator && Array.isArray(criteria.narrator)) {
        narrator_filter = criteria.narrator.join(',');
      }
    }
    
    const tempScriptPath = path.join(os.tmpdir(), `update_watchlist_${Date.now()}.py`);
    const scriptContent = `
import sys
import os
import json

# Fix Python path to avoid relative import issues
parent_dir = os.path.dirname('${PYTHON_PATH}')
sys.path.insert(0, parent_dir)
os.chdir('${PYTHON_PATH}')

try:
    from audiostracker.database import update_watchlist_entry_by_author
    
    success = update_watchlist_entry_by_author(
        "${author.replace(/"/g, '\\"')}",
        ${title_filter ? `"${title_filter.replace(/"/g, '\\"')}"` : 'None'},
        ${series_filter ? `"${series_filter.replace(/"/g, '\\"')}"` : 'None'},
        ${publisher_filter ? `"${publisher_filter.replace(/"/g, '\\"')}"` : 'None'},
        ${narrator_filter ? `"${narrator_filter.replace(/"/g, '\\"')}"` : 'None'}
    )
    
    print(json.dumps({"success": success}))
    
except Exception as e:
    import traceback
    print(json.dumps({"success": False, "error": str(e), "traceback": traceback.format_exc()}))
`;

    fs.writeFileSync(tempScriptPath, scriptContent);
    const pythonProcess = spawn('python3', [tempScriptPath]);
    
    let dataString = '';
    
    pythonProcess.stdout.on('data', data => {
      dataString += data.toString();
    });
    
    pythonProcess.on('close', code => {
      fs.unlinkSync(tempScriptPath);
      
      try {
        const result = JSON.parse(dataString);
        if (result.success) {
          res.json({ success: true });
        } else {
          res.status(500).json({ error: result.error, traceback: result.traceback });
        }
      } catch (e) {
        res.status(500).json({ error: 'Failed to parse response' });
      }
    });
  } catch (error) {
    console.error('Error updating watchlist entry:', error);
    res.status(500).json({ error: 'Failed to update watchlist entry' });
  }
});

// Delete watchlist entry - change from ID-based to author-based
app.delete('/api/audiostacker/watchlist', (req, res) => {
  try {
    const author = req.query.author;
    
    if (!author) {
      return res.status(400).json({ error: 'Author name is required' });
    }
    
    const tempScriptPath = path.join(os.tmpdir(), `delete_watchlist_${Date.now()}.py`);
    const scriptContent = `
import sys
import os
import json

# Fix Python path to avoid relative import issues
parent_dir = os.path.dirname('${PYTHON_PATH}')
sys.path.insert(0, parent_dir)
os.chdir('${PYTHON_PATH}')

try:
    from audiostracker.database import delete_watchlist_entry_by_author
    
    success = delete_watchlist_entry_by_author("${author.replace(/"/g, '\\"')}")
    
    print(json.dumps({"success": success}))
    
except Exception as e:
    import traceback
    print(json.dumps({"success": False, "error": str(e), "traceback": traceback.format_exc()}))
`;

    fs.writeFileSync(tempScriptPath, scriptContent);
    const pythonProcess = spawn('python3', [tempScriptPath]);
    
    let dataString = '';
    
    pythonProcess.stdout.on('data', data => {
      dataString += data.toString();
    });
    
    pythonProcess.on('close', code => {
      fs.unlinkSync(tempScriptPath);
      
      try {
        const result = JSON.parse(dataString);
        if (result.success) {
          res.json({ success: true });
        } else {
          res.status(500).json({ error: result.error, traceback: result.traceback });
        }
      } catch (e) {
        res.status(500).json({ error: 'Failed to parse response' });
      }
    });
  } catch (error) {
    console.error('Error deleting watchlist entry:', error);
    res.status(500).json({ error: 'Failed to delete watchlist entry' });
  }
});

// Prune database (remove old releases)
app.post('/api/audiostacker/prune', (req, res) => {
  try {
    const tempScriptPath = path.join(os.tmpdir(), `prune_database_${Date.now()}.py`);
    const scriptContent = `
import sys
import os
import json
import sqlite3
from datetime import datetime

# Fix Python path to avoid relative import issues
parent_dir = os.path.dirname('${PYTHON_PATH}')
sys.path.insert(0, parent_dir)
os.chdir('${PYTHON_PATH}')

try:
    db_path = 'audiobooks.db'
    if not os.path.exists(db_path):
        print(json.dumps({"success": False, "error": "Database not found"}))
        exit(0)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count before pruning
    cursor.execute("SELECT COUNT(*) FROM audiobooks")
    before_count = cursor.fetchone()[0]
    
    # Prune released books (day after release)
    cursor.execute("DELETE FROM audiobooks WHERE release_date < DATE('now', '-1 day')")
    deleted_count = cursor.rowcount
    
    conn.commit();
    conn.close();
    
    result = {
        "success": True,
        "before_count": before_count,
        "deleted_count": deleted_count,
        "remaining_count": before_count - deleted_count
    }
    
    print(json.dumps(result))
    
except Exception as e:
    import traceback
    result = {
        "success": False,
        "error": str(e),
        "traceback": traceback.format_exc()
    }
    print(json.dumps(result))
`;

    fs.writeFileSync(tempScriptPath, scriptContent);
    const pythonProcess = spawn('python3', [tempScriptPath]);
    
    let dataString = '';
    
    pythonProcess.stdout.on('data', data => {
      dataString += data.toString();
    });
    
    pythonProcess.on('close', code => {
      fs.unlinkSync(tempScriptPath);
      
      try {
        const result = JSON.parse(dataString);
        res.json(result);
      } catch (e) {
        console.error('Error parsing prune results:', e);
        res.status(500).json({ success: false, error: 'Failed to parse prune results' });
      }
    });
  } catch (error) {
    console.error('Error pruning database:', error);
    res.status(500).json({ success: false, error: 'Failed to prune database' });
  }
});

// DELETE endpoint to remove an audiobook from the database by ASIN
app.delete('/api/database/:asin', (req, res) => {
  const asin = req.params.asin;
  
  if (!asin) {
    return res.status(400).json({ error: 'ASIN is required' });
  }

  const tempScriptPath = path.join(os.tmpdir(), `delete_audiobook_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
sys.path.insert(0, '${PYTHON_PATH}')
sys.path.insert(0, '${path.dirname(PYTHON_PATH)}')
os.chdir('${PYTHON_PATH}')

try:
    import json
    from audiostracker.database import delete_audiobook_by_asin
    
    success = delete_audiobook_by_asin("${asin.replace(/"/g, '\\"')}")
    print(json.dumps({"success": success}))
    sys.exit(0 if success else 1)
except Exception as e:
    import traceback
    import json
    print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
    sys.exit(1)
`;

  fs.writeFileSync(tempScriptPath, scriptContent);

  const python = spawn('python', [tempScriptPath]);
  
  let outputData = '';

  python.stdout.on('data', (data) => {
    outputData += data.toString();
  });

  python.on('close', (code) => {
    try {
      fs.unlinkSync(tempScriptPath);
    } catch (err) {
      console.error('Error deleting temporary script:', err);
    }

    if (code !== 0) {
      console.error(`Python script exited with code ${code}`);
      return res.status(500).json({ error: 'Failed to delete audiobook', output: outputData });
    }

    try {
      // Get the last line which should contain our JSON output
      const jsonLine = outputData.trim().split('\n').pop();
      const result = JSON.parse(jsonLine);
      
      if (result.success) {
        res.json({ success: true, message: `Audiobook with ASIN ${asin} deleted successfully` });
      } else {
        res.status(404).json({ success: false, message: `Audiobook with ASIN ${asin} not found` });
      }
    } catch (err) {
      console.error('Error parsing Python output:', err);
      res.status(500).json({ error: 'Error processing response', output: outputData });
    }
  });

  python.stderr.on('data', (data) => {
    console.error(`Python stderr: ${data}`);
  });
});

// Fallback route to handle SPA routing - only serve index.html if dist exists
app.get('*', (req, res) => {
  console.log(`Fallback route hit for: ${req.path}`);
  
  // Debug info about all routes
  console.log('DEBUG: Looking for route match among all registered routes:');
  app._router.stack.forEach((layer) => {
    if (layer.route) {
      const path = layer.route.path;
      const methods = Object.keys(layer.route.methods).map(m => m.toUpperCase()).join(',');
      console.log(`  ${methods} ${path}`);
    }
  });
  
  const distPath = path.join(__dirname, '../frontend/dist/index.html');
  if (fs.existsSync(distPath)) {
    res.sendFile(distPath);
  } else {
    // In development mode, just return a simple message for non-API routes
    if (req.path.startsWith('/api/')) {
      res.status(404).json({ error: 'API endpoint not found', path: req.path });
    } else {
      res.status(200).json({ 
        message: 'Backend is running', 
        note: 'Frontend is running separately on port 5006' 
      });
    }
  }
});

const PORT = process.env.PORT || 5005;

// Debug: Print all registered routes
console.log('\n\n=========================================');
console.log('DEBUG: REGISTERED ROUTES:');
console.log('=========================================');
let routeFound = false;
app._router.stack.forEach((layer) => {
  if (layer.route) {
    routeFound = true;
    const path = layer.route.path;
    const methods = Object.keys(layer.route.methods).map(m => m.toUpperCase()).join(',');
    console.log(`${methods} ${path}`);
  }
});

if (!routeFound) {
  console.log('WARNING: NO ROUTES FOUND! Check route registration.');
}
console.log('=========================================\n\n');

// Debug middleware to log all requests
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
