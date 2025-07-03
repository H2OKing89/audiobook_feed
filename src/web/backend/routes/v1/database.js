const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Path to Python module
const PYTHON_PATH = path.resolve(__dirname, '../../../../audiostracker');

/**
 * Get all audiobooks from the database
 */
router.get('/', (req, res) => {
  const filter = req.query.filter || 'all';
  const limit = parseInt(req.query.limit) || 1000;

  const tempScriptPath = path.join(os.tmpdir(), `database_script_${Date.now()}.py`);
  const scriptContent = `
import sys
import os
import json
sys.path.insert(0, '${PYTHON_PATH}')
sys.path.insert(0, '${path.dirname(PYTHON_PATH)}')
os.chdir('${PYTHON_PATH}')

try:
    from database import get_all_audiobooks, count_audiobooks, get_last_checked_time
    
    # Get books from database
    filter_type = "${filter}"
    limit = ${limit}
    
    # Get all audiobooks with the specified filter
    books = get_all_audiobooks(filter_type=filter_type, limit=limit)
    
    # Get total count and last updated time
    total = count_audiobooks()
    last_updated = get_last_checked_time()
    
    # Format the response
    result = {
        "books": books,
        "total": total,
        "cache_info": {
            "last_updated": last_updated,
            "upcoming_releases": sum(1 for book in books if 'release_date' in book and book['release_date'] > last_updated)
        }
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
      return res.status(500).json({ error: 'Failed to get database books' });
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
      res.status(500).json({ error: 'Failed to parse database output', output: dataString });
    }
  });
});

/**
 * Delete an audiobook from the database
 */
router.delete('/:asin', (req, res) => {
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
    from database import delete_audiobook_by_asin
    
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

  const pythonProcess = spawn('python', [tempScriptPath]);
  
  let outputData = '';

  pythonProcess.stdout.on('data', (data) => {
    outputData += data.toString();
  });

  pythonProcess.on('close', (code) => {
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
      
      if (result.error) {
        return res.status(500).json({ error: result.error, details: result.traceback });
      }
      
      res.json(result);
    } catch (error) {
      console.error('Error parsing Python output:', error);
      res.status(500).json({ error: 'Failed to parse delete output', output: outputData });
    }
  });
});

module.exports = router;
