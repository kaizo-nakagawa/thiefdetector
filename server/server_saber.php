<?php
header("Content-Type: application/json");

// Configuration
$UPLOAD_FOLDER = __DIR__ . '/uploads';
$MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
$ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif'];

// Create uploads directory if it doesn't exist
if (!file_exists($UPLOAD_FOLDER)) {
    mkdir($UPLOAD_FOLDER, 0777, true);
}

// Get the request method and path
$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// Route the request
switch ($path) {
    case '/recv-image':
        if ($method === 'POST') {
            handleImageUpload();
        } else {
            http_response_code(405);
            echo json_encode(['success' => false, 'message' => 'Method not allowed']);
        }
        break;
        
    case '/print-text':
        if ($method === 'POST') {
            handleTextData();
        } else {
            http_response_code(405);
            echo json_encode(['success' => false, 'message' => 'Method not allowed']);
        }
        break;
        
    case '/health':
        if ($method === 'GET') {
            healthCheck();
        } else {
            http_response_code(405);
            echo json_encode(['success' => false, 'message' => 'Method not allowed']);
        }
        break;
        
    default:
        // Check if it's a request for an uploaded file
        if (str_starts_with($path, '/uploads/')) {
            serveUploadedFile($path);
        } else {
            http_response_code(404);
            echo json_encode(['success' => false, 'message' => 'Endpoint not found']);
        }
}

function handleImageUpload() {
    global $UPLOAD_FOLDER, $MAX_FILE_SIZE, $ALLOWED_TYPES;
    
    try {
        // Get metadata from headers
        $label = $_SERVER['HTTP_X_LABEL'] ?? 'unknown';
        $timestamp = $_SERVER['HTTP_X_TIMESTAMP'] ?? date('Y-m-d\TH-i-s');
        
        // Check if file was uploaded
        if (!isset($_FILES['image'])) {
            http_response_code(400);
            echo json_encode(['success' => false, 'message' => 'No image file in request']);
            return;
        }
        
        $file = $_FILES['image'];
        
        // Check for errors
        if ($file['error'] !== UPLOAD_ERR_OK) {
            throw new RuntimeException('File upload error: ' . $file['error']);
        }
        
        // Check file size
        if ($file['size'] > $MAX_FILE_SIZE) {
            http_response_code(400);
            echo json_encode(['success' => false, 'message' => 'File too large']);
            return;
        }
        
        // Check file type
        $finfo = new finfo(FILEINFO_MIME_TYPE);
        $mime = $finfo->file($file['tmp_name']);
        if (!in_array($mime, $ALLOWED_TYPES)) {
            http_response_code(400);
            echo json_encode(['success' => false, 'message' => 'Invalid file type']);
            return;
        }
        
        // Create safe filename
        $ext = pathinfo($file['name'], PATHINFO_EXTENSION);
        $filename = sprintf('%s_%s.%s', $label, $timestamp, $ext);
        $filepath = $UPLOAD_FOLDER . '/' . $filename;
        
        // Move the file
        if (!move_uploaded_file($file['tmp_name'], $filepath)) {
            throw new RuntimeException('Failed to move uploaded file');
        }
        
        // Log information
        error_log(sprintf("[%s] Detection received:", date('Y-m-d\TH:i:s')));
        error_log(sprintf("- Label: %s", $label));
        error_log(sprintf("- Timestamp: %s", $timestamp));
        error_log(sprintf("- File saved: %s", $filepath));
        
        // Send success response
        echo json_encode([
            'success' => true,
            'message' => 'Image received and saved successfully',
            'metadata' => [
                'label' => $label,
                'timestamp' => $timestamp,
                'filename' => $filename
            ]
        ]);
        
    } catch (Exception $e) {
        http_response_code(500);
        error_log("Error handling image upload: " . $e->getMessage());
        echo json_encode([
            'success' => false,
            'message' => 'Error processing image upload',
            'error' => $e->getMessage()
        ]);
    }
}

function handleTextData() {
    try {
        // Get request data
        $data = $_POST;
        if (empty($data)) {
            $input = file_get_contents('php://input');
            $data = json_decode($input, true) ?? [];
        }
        
        // Log the received data
        error_log(sprintf("[%s] Text data received:", date('Y-m-d\TH:i:s')));
        error_log(print_r($data, true));
        
        // Send success response
        echo json_encode([
            'success' => true,
            'message' => 'Text data received successfully',
            'receivedData' => $data
        ]);
        
    } catch (Exception $e) {
        http_response_code(500);
        error_log("Error handling text data: " . $e->getMessage());
        echo json_encode([
            'success' => false,
            'message' => 'Error processing text data',
            'error' => $e->getMessage()
        ]);
    }
}

function healthCheck() {
    echo json_encode([
        'status' => 'ok',
        'timestamp' => date('Y-m-d\TH:i:s')
    ]);
}

function serveUploadedFile($path) {
    global $UPLOAD_FOLDER;
    
    $filename = basename($path);
    $filepath = $UPLOAD_FOLDER . '/' . $filename;
    
    if (!file_exists($filepath)) {
        http_response_code(404);
        echo json_encode(['success' => false, 'message' => 'File not found']);
        return;
    }
    
    $mime = mime_content_type($filepath);
    header("Content-Type: $mime");
    header("Content-Length: " . filesize($filepath));
    readfile($filepath);
}