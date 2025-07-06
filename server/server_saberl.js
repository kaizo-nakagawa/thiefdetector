const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

// Create Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Configure upload settings
const UPLOAD_FOLDER = path.join(__dirname, 'uploads');
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB limit

// Create uploads directory if it doesn't exist
if (!fs.existsSync(UPLOAD_FOLDER)) {
    fs.mkdirSync(UPLOAD_FOLDER, { recursive: true });
}

// Configure multer storage
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, UPLOAD_FOLDER);
    },
    filename: (req, file, cb) => {
        const label = req.headers['x-label'] || 'unknown';
        const timestamp = req.headers['x-timestamp'] || new Date().toISOString().replace(/:/g, '-');
        const ext = path.extname(file.originalname);
        const filename = `${label}_${timestamp}${ext}`;
        cb(null, filename);
    }
});

// Configure multer upload
const upload = multer({
    storage: storage,
    limits: { fileSize: MAX_FILE_SIZE }
});

// Middleware for JSON and form data
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Endpoint for receiving images
app.post('/recv-image', upload.single('image'), (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({
                success: false,
                message: 'No image file in request'
            });
        }

        const label = req.headers['x-label'] || 'unknown';
        const timestamp = req.headers['x-timestamp'] || new Date().toISOString();

        // Log information
        console.log(`[${new Date().toISOString()}] Detection received:`);
        console.log(`- Label: ${label}`);
        console.log(`- Timestamp: ${timestamp}`);
        console.log(`- File saved: ${req.file.path}`);

        // Send success response
        res.json({
            success: true,
            message: 'Image received and saved successfully',
            metadata: {
                label: label,
                timestamp: timestamp,
                filename: req.file.filename
            }
        });

    } catch (error) {
        console.error(`Error handling image upload: ${error.message}`);
        res.status(500).json({
            success: false,
            message: 'Error processing image upload',
            error: error.message
        });
    }
});

// Endpoint for receiving text data
app.post('/print-text', (req, res) => {
    try {
        const data = req.body;

        // Log the received data
        console.log(`[${new Date().toISOString()}] Text data received:`);
        console.log(JSON.stringify(data, null, 2));

        // Send success response
        res.json({
            success: true,
            message: 'Text data received successfully',
            receivedData: data
        });

    } catch (error) {
        console.error(`Error handling text data: ${error.message}`);
        res.status(500).json({
            success: false,
            message: 'Error processing text data',
            error: error.message
        });
    }
});

// Simple health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: new Date().toISOString()
    });
});

// Serve uploaded files
app.use('/uploads', express.static(UPLOAD_FOLDER));

// Start the server
app.listen(PORT, () => {
    console.log(`Detection server running on port ${PORT}`);
    console.log(`- Image endpoint: http://localhost:${PORT}/recv-image`);
    console.log(`- Text endpoint: http://localhost:${PORT}/print-text`);
    console.log(`- Health check: http://localhost:${PORT}/health`);
    console.log(`- View uploads: http://localhost:${PORT}/uploads`);
});