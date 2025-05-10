import express from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

// Get current directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Create Express app
const app = express();
const PORT = process.env.PORT || 3000;

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    // Create uploads directory if it doesn't exist
    const uploadDir = path.join(__dirname, 'uploads');
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: function (req, file, cb) {
    // Use original filename or create one from headers
    const label = req.headers['x-label'] || 'unknown';
    const timestamp =
      req.headers['x-timestamp'] || new Date().toISOString().replace(/:/g, '-');
    cb(null, `${label}_${timestamp}${path.extname(file.originalname)}`);
  },
});

const upload = multer({
  storage: storage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
});

// Middleware for parsing JSON and URL-encoded data
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Endpoint for receiving images
app.post('/recv-image', upload.single('image'), (req, res) => {
  try {
    // Get metadata from headers
    const label = req.headers['x-label'] || 'unknown';
    const timestamp = req.headers['x-timestamp'] || new Date().toISOString();

    console.log(`[${new Date().toISOString()}] Detection received:`);
    console.log(`- Label: ${label}`);
    console.log(`- Timestamp: ${timestamp}`);
    console.log(`- File saved: ${req.file.path}`);

    // Send success response
    res.status(200).json({
      success: true,
      message: 'Image received and saved successfully',
      metadata: {
        label,
        timestamp,
        filename: req.file.filename,
      },
    });
  } catch (error) {
    console.error('Error handling image upload:', error);
    res.status(500).json({
      success: false,
      message: 'Error processing image upload',
      error: error.message,
    });
  }
});

// Endpoint for receiving text data
app.post('/print-text', (req, res) => {
  try {
    // Log the received data
    console.log(`[${new Date().toISOString()}] Text data received:`);
    console.log(req.body);

    // Send success response
    res.status(200).json({
      success: true,
      message: 'Text data received successfully',
      receivedData: req.body,
    });
  } catch (error) {
    console.error('Error handling text data:', error);
    res.status(500).json({
      success: false,
      message: 'Error processing text data',
      error: error.message,
    });
  }
});

// Simple health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Serve uploaded files (optional, for viewing uploads in browser)
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Start the server
app.listen(PORT, () => {
  console.log(`Detection server running on port ${PORT}`);
  console.log(`- Image endpoint: http://localhost:${PORT}/recv-image`);
  console.log(`- Text endpoint: http://localhost:${PORT}/print-text`);
  console.log(`- Health check: http://localhost:${PORT}/health`);
  console.log(`- View uploads: http://localhost:${PORT}/uploads`);
});
