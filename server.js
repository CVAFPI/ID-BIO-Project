const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware for parsing requests
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve all static files directly from the project directory
app.use(express.static(__dirname));

// API: List available log files
app.get('/api/logs/list', (req, res) => {
    fs.readdir(__dirname, (err, files) => {
        if (err) {
            return res.status(500).json({ error: 'Unable to scan directory' });
        }
        const logFiles = files.filter(file => file.startsWith('logs_') && file.endsWith('.csv'));
        res.json(logFiles);
    });
});

// API: Get today's active log
app.get('/api/logs/today', (req, res) => {
    const todayStr = new Date().toLocaleDateString('en-CA').replace(/-/g, '');
    const filename = `logs_${todayStr}.csv`;
    const filePath = path.join(__dirname, filename);

    if (fs.existsSync(filePath)) {
        parseCSV(filePath, res);
    } else {
        res.json([]);
    }
});

// API: View a specific log file
app.get('/api/logs/view', (req, res) => {
    const fileName = req.query.file;
    if (!fileName) {
        return res.status(400).json({ error: 'File parameter is missing' });
    }
    const safeName = path.basename(fileName);
    const filePath = path.join(__dirname, safeName);

    if (fs.existsSync(filePath)) {
        parseCSV(filePath, res);
    } else {
        res.status(404).json({ error: 'Log file not found' });
    }
});

// Helper function to parse CSV logs safely
function parseCSV(filePath, res) {
    fs.readFile(filePath, 'utf8', (err, data) => {
        if (err) {
            return res.status(500).json({ error: 'Failed to read log file' });
        }
        const rows = data.split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .map(line => line.split(',').map(val => val.replace(/^"|"$/g, '')));
        res.json(rows);
    });
}

// Safe fallback middleware (prevents path-to-regexp crashes)
app.use((req, res) => {
    const requestedPath = path.join(__dirname, req.path);
    if (fs.existsSync(requestedPath) && fs.statSync(requestedPath).isFile()) {
        res.sendFile(requestedPath);
    } else {
        res.sendFile(path.join(__dirname, 'launchpad.html'));
    }
});

app.listen(PORT, () => {
    console.log(`CVA Server running successfully at http://localhost:${PORT}`);
});
