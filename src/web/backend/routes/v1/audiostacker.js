const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Path to Python module
const PYTHON_PATH = path.resolve(__dirname, '../../../../audiostracker');

/**
 * Get AudioStacker status
 */
router.get('/status', async (req, res) => {
  const tempScriptPath = path.join(os.tmpdir(), `status_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
import json
sys.path.insert(0, '${PYTHON_PATH}')
sys.path.insert(0, '${path.dirname(PYTHON_PATH)}')
os.chdir('${PYTHON_PATH}')

try:
    import database
    import utils
    
    # Get some basic stats about the database
    stats = {
        "total_books": database.count_audiobooks(),
        "upcoming_releases": database.count_upcoming_audiobooks(),
        "last_updated": database.get_last_checked_time()
    }
    
    # Get system information
    system_info = utils.get_system_info()
    
    # Combine the data
    result = {
        "database": stats,
        "system": system_info
    }
    
    print(json.dumps(result))
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    print(json.dumps({"error": str(e), "traceback": error_details}))
`;

  fs.writeFileSync(tempScriptPath, scriptContent);

  const pythonProcess = spawn('python', [tempScriptPath]);
  
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
      console.error(`Python script exited with code ${code}`);
      return res.status(500).json({ error: 'Failed to get AudioStacker status' });
    }

    try {
      // Get the last line which should contain our JSON output
      const jsonLine = dataString.trim().split('\n').pop();
      const result = JSON.parse(jsonLine);
      
      if (result.error) {
        console.error('Error in Python script:', result.error);
        return res.status(500).json({ error: result.error, details: result.traceback });
      }
      
      res.json(result);
    } catch (error) {
      console.error('Error parsing Python output:', error);
      res.status(500).json({ error: 'Failed to parse AudioStacker status output', output: dataString });
    }
  });
});

/**
 * Get AudioStacker watchlist
 */
router.get('/watchlist', (req, res) => {
  const tempScriptPath = path.join(os.tmpdir(), `watchlist_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
import json
sys.path.insert(0, '${PYTHON_PATH}')
sys.path.insert(0, '${path.dirname(PYTHON_PATH)}')
os.chdir('${PYTHON_PATH}')

try:
    from database import get_watchlist
    
    # Get the watchlist from the database
    watchlist = get_watchlist()
    
    # Structure the data into the format expected by the frontend
    # In particular, group the entries by author name
    authors = {}
    for entry in watchlist:
        author_name = entry['author_name']
        if author_name not in authors:
            authors[author_name] = {}
        
        # For each filter type that's not None, add it to the author's criteria
        for filter_type in ['title_filter', 'series_filter', 'publisher_filter', 'narrator_filter']:
            if entry[filter_type]:
                # Remove _filter suffix
                key = filter_type.replace('_filter', '')
                if key not in authors[author_name]:
                    authors[author_name][key] = entry[filter_type]
    
    # Format the watchlist in the expected structure
    formatted_watchlist = {
        "audiobooks": {
            "author": authors
        }
    }
    
    print(json.dumps(formatted_watchlist))
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    print(json.dumps({"error": str(e), "traceback": error_details}))
`;

  fs.writeFileSync(tempScriptPath, scriptContent);

  const pythonProcess = spawn('python', [tempScriptPath]);
  
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
      console.error(`Python script exited with code ${code}`);
      return res.status(500).json({ error: 'Failed to get AudioStacker watchlist' });
    }

    try {
      // Get the last line which should contain our JSON output
      const jsonLine = dataString.trim().split('\n').pop();
      const result = JSON.parse(jsonLine);
      
      if (result.error) {
        console.error('Error in Python script:', result.error);
        return res.status(500).json({ error: result.error, details: result.traceback });
      }
      
      res.json(result);
    } catch (error) {
      console.error('Error parsing Python output:', error);
      res.status(500).json({ error: 'Failed to parse AudioStacker watchlist output', output: dataString });
    }
  });
});

/**
 * Add author to watchlist
 */
router.post('/watchlist', (req, res) => {
  const { author, criteria } = req.body;
  
  if (!author) {
    return res.status(400).json({ error: 'Author name is required' });
  }

  const tempScriptPath = path.join(os.tmpdir(), `add_watchlist_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
import json
sys.path.insert(0, '${PYTHON_PATH}')
sys.path.insert(0, '${path.dirname(PYTHON_PATH)}')
os.chdir('${PYTHON_PATH}')

try:
    from database import add_watchlist_entry, get_watchlist
    
    # Parse the criteria
    author_name = ${JSON.stringify(author)}
    
    # Extract criteria values directly
    title_filter = ${JSON.stringify((criteria || {}).title || null)}
    series_filter = ${JSON.stringify((criteria || {}).series || null)}
    publisher_filter = ${JSON.stringify((criteria || {}).publisher || null)}
    narrator_filter = ${JSON.stringify((criteria || {}).narrator || null)}
    
    # Filters are already extracted above
    
    # Check if the author already exists
    watchlist = get_watchlist()
    author_exists = any(entry['author_name'] == author_name for entry in watchlist)
    
    if author_exists:
        # Get the existing criteria for this author
        existing_criteria = {}
        for entry in watchlist:
            if entry['author_name'] == author_name:
                for filter_type in ['title_filter', 'series_filter', 'publisher_filter', 'narrator_filter']:
                    if entry[filter_type]:
                        # Remove _filter suffix
                        key = filter_type.replace('_filter', '')
                        if key not in existing_criteria:
                            existing_criteria[key] = entry[filter_type]
        
        print(json.dumps({
            "success": False,
            "author_exists": True,
            "author_name": author_name,
            "existing_criteria": existing_criteria
        }))
    else:
        # Add the new entry
        add_watchlist_entry(
            author_name=author_name, 
            title_filter=title_filter, 
            series_filter=series_filter,
            publisher_filter=publisher_filter,
            narrator_filter=narrator_filter
        )
        print(json.dumps({
            "success": True,
            "author": author_name,
            "criteria": criteria
        }))
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    print(json.dumps({"error": str(e), "traceback": error_details}))
`;

  fs.writeFileSync(tempScriptPath, scriptContent);

  const pythonProcess = spawn('python', [tempScriptPath]);
  
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
    
    if (code !== 0 && !dataString.includes('"author_exists": true')) {
      console.error(`Python script exited with code ${code}`);
      return res.status(500).json({ error: 'Failed to add author to watchlist' });
    }

    try {
      // Get the last line which should contain our JSON output
      const jsonLine = dataString.trim().split('\n').pop();
      const result = JSON.parse(jsonLine);
      
      if (result.error) {
        console.error('Error in Python script:', result.error);
        return res.status(500).json({ error: result.error, details: result.traceback });
      }
      
      res.json(result);
    } catch (error) {
      console.error('Error parsing Python output:', error);
      res.status(500).json({ error: 'Failed to parse add watchlist output', output: dataString });
    }
  });
});

/**
 * Update watchlist entry
 */
router.put('/watchlist', (req, res) => {
  const { author, criteria } = req.body;
  
  if (!author) {
    return res.status(400).json({ error: 'Author name is required' });
  }

  const tempScriptPath = path.join(os.tmpdir(), `update_watchlist_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
import json
sys.path.insert(0, '${PYTHON_PATH}')
sys.path.insert(0, '${path.dirname(PYTHON_PATH)}')
os.chdir('${PYTHON_PATH}')

try:
    from database import delete_watchlist_entry_by_author, add_watchlist_entry
    
    # Parse the criteria
    author_name = ${JSON.stringify(author)}
    
    # Extract criteria values directly
    title_filter = ${JSON.stringify((criteria || {}).title || null)}
    series_filter = ${JSON.stringify((criteria || {}).series || null)}
    publisher_filter = ${JSON.stringify((criteria || {}).publisher || null)}
    narrator_filter = ${JSON.stringify((criteria || {}).narrator || null)}
    
    # Filters are already extracted above
    
    # First, delete any existing entries for this author
    delete_watchlist_entry_by_author(author_name)
    
    # Then, add the new entry with updated criteria
    add_watchlist_entry(
        author_name=author_name, 
        title_filter=title_filter, 
        series_filter=series_filter,
        publisher_filter=publisher_filter,
        narrator_filter=narrator_filter
    )
    
    print(json.dumps({
        "success": True,
        "author": author_name,
        "criteria": criteria
    }))
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    print(json.dumps({"error": str(e), "traceback": error_details}))
`;

  fs.writeFileSync(tempScriptPath, scriptContent);

  const pythonProcess = spawn('python', [tempScriptPath]);
  
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
      console.error(`Python script exited with code ${code}`);
      return res.status(500).json({ error: 'Failed to update author in watchlist' });
    }

    try {
      // Get the last line which should contain our JSON output
      const jsonLine = dataString.trim().split('\n').pop();
      const result = JSON.parse(jsonLine);
      
      if (result.error) {
        console.error('Error in Python script:', result.error);
        return res.status(500).json({ error: result.error, details: result.traceback });
      }
      
      res.json(result);
    } catch (error) {
      console.error('Error parsing Python output:', error);
      res.status(500).json({ error: 'Failed to parse update watchlist output', output: dataString });
    }
  });
});

/**
 * Delete author from watchlist
 */
router.delete('/watchlist', (req, res) => {
  const author = req.query.author;
  
  if (!author) {
    return res.status(400).json({ error: 'Author name is required' });
  }

  const tempScriptPath = path.join(os.tmpdir(), `delete_watchlist_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
import json
sys.path.insert(0, '${PYTHON_PATH}')
sys.path.insert(0, '${path.dirname(PYTHON_PATH)}')
os.chdir('${PYTHON_PATH}')

try:
    from database import delete_watchlist_entry_by_author
    
    # Delete all entries for this author
    success = delete_watchlist_entry_by_author(${JSON.stringify(author)})
    
    print(json.dumps({
        "success": success,
        "author": ${JSON.stringify(author)}
    }))
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    print(json.dumps({"error": str(e), "traceback": error_details}))
`;

  fs.writeFileSync(tempScriptPath, scriptContent);

  const pythonProcess = spawn('python', [tempScriptPath]);
  
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
      console.error(`Python script exited with code ${code}`);
      return res.status(500).json({ error: 'Failed to delete author from watchlist' });
    }

    try {
      // Get the last line which should contain our JSON output
      const jsonLine = dataString.trim().split('\n').pop();
      const result = JSON.parse(jsonLine);
      
      if (result.error) {
        console.error('Error in Python script:', result.error);
        return res.status(500).json({ error: result.error, details: result.traceback });
      }
      
      res.json(result);
    } catch (error) {
      console.error('Error parsing Python output:', error);
      res.status(500).json({ error: 'Failed to parse delete watchlist output', output: dataString });
    }
  });
});

/**
 * Run AudioStacker to check for new audiobooks
 */
router.post('/run', (req, res) => {
  const dryRun = req.body.dryRun === true;

  const tempScriptPath = path.join(os.tmpdir(), `run_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
import json
import time
import importlib.util

# Add paths to system path
sys.path.insert(0, '${PYTHON_PATH}')
sys.path.insert(0, '${path.dirname(PYTHON_PATH)}')
os.chdir('${PYTHON_PATH}')

try:
    # Import main module directly from file path
    spec = importlib.util.spec_from_file_location("main", os.path.join('${PYTHON_PATH}', 'main.py'))
    main_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_module)
    main = main_module.main
    
    # Run AudioStacker with the appropriate options
    start_time = time.time()
    result = main(dry_run=${dryRun ? 'True' : 'False'})
    end_time = time.time()
    
    # Add timing information
    result['execution_time'] = round(end_time - start_time, 2)
    result['success'] = True
    
    # Convert to JSON and print
    print(json.dumps(result))
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    print(json.dumps({
        "error": str(e), 
        "traceback": error_details,
        "success": False,
        "error_type": str(type(e).__name__)
    }))
`;

  fs.writeFileSync(tempScriptPath, scriptContent);

  const pythonProcess = spawn('python', [tempScriptPath]);
  
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
      console.error(`Python script exited with code ${code}`);
      return res.status(500).json({ 
        error: 'Failed to run AudioStacker', 
        success: false,
        dry_run: dryRun 
      });
    }

    try {
      // Get the last line which should contain our JSON output
      const jsonLine = dataString.trim().split('\n').pop();
      const result = JSON.parse(jsonLine);
      
      if (result.error) {
        console.error('Error in Python script:', result.error);
        console.error('Traceback:', result.traceback);
        return res.status(500).json({ 
          error: result.error, 
          details: result.traceback,
          error_type: result.error_type,
          success: false,
          dry_run: dryRun
        });
      }
      
      res.json(result);
    } catch (error) {
      console.error('Error parsing Python output:', error);
      res.status(500).json({ 
        error: 'Failed to parse AudioStacker run output', 
        output: dataString,
        success: false,
        dry_run: dryRun
      });
    }
  });
});

/**
 * Prune old database entries
 */
router.post('/prune', (req, res) => {
  const days = parseInt(req.body.days) || 90;

  const tempScriptPath = path.join(os.tmpdir(), `prune_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
import json
sys.path.insert(0, '${PYTHON_PATH}')
sys.path.insert(0, '${path.dirname(PYTHON_PATH)}')
os.chdir('${PYTHON_PATH}')

try:
    from database import prune_old_books
    
    # Prune old books
    removed_count = prune_old_books(days=${days})
    
    print(json.dumps({
        "success": True,
        "removed_count": removed_count,
        "days": ${days}
    }))
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    print(json.dumps({"error": str(e), "traceback": error_details}))
`;

  fs.writeFileSync(tempScriptPath, scriptContent);

  const pythonProcess = spawn('python', [tempScriptPath]);
  
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
      console.error(`Python script exited with code ${code}`);
      return res.status(500).json({ error: 'Failed to prune database' });
    }

    try {
      // Get the last line which should contain our JSON output
      const jsonLine = dataString.trim().split('\n').pop();
      const result = JSON.parse(jsonLine);
      
      if (result.error) {
        console.error('Error in Python script:', result.error);
        return res.status(500).json({ error: result.error, details: result.traceback });
      }
      
      res.json(result);
    } catch (error) {
      console.error('Error parsing Python output:', error);
      res.status(500).json({ error: 'Failed to parse prune output', output: dataString });
    }
  });
});

module.exports = router;
