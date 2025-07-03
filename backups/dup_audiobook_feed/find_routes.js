const fs = require('fs');
const path = require('path');

// Read the app.js file
const appPath = path.join(__dirname, 'src', 'web', 'backend', 'app.js');
const appContent = fs.readFileSync(appPath, 'utf8');

// Find all route declarations
const routePattern = /app\.(get|post|put|delete|patch)\(['"]([^'"]+)['"]/g;
let match;
const routes = [];

while ((match = routePattern.exec(appContent)) !== null) {
  routes.push({
    method: match[1].toUpperCase(),
    path: match[2]
  });
}

// Sort routes by path
routes.sort((a, b) => a.path.localeCompare(b.path));

// Print routes
console.log("AVAILABLE API ROUTES:");
console.log("====================");
routes.forEach(route => {
  console.log(`${route.method.padEnd(6)} ${route.path}`);
});
