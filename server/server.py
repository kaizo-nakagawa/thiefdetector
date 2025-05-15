from flask import Flask, request, jsonify, send_from_directory
import os
import datetime
import json
from werkzeug.utils import secure_filename

# Create Flask app
app = Flask(__name__)
PORT = int(os.environ.get("PORT", 3000))

# Configure upload settings
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB limit

# Create uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Flask app
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


# Endpoint for receiving images
@app.route("/recv-image", methods=["POST"])
def receive_image():
    try:
        # Get metadata from headers
        label = request.headers.get("X-Label", "unknown")
        timestamp = request.headers.get(
            "X-Timestamp", datetime.datetime.now().isoformat().replace(":", "-")
        )

        # Check if the post request has the file part
        if "image" not in request.files:
            return (
                jsonify({"success": False, "message": "No image file in request"}),
                400,
            )

        file = request.files["image"]

        # If user does not select file, browser might submit an empty file
        if file.filename == "":
            return jsonify({"success": False, "message": "No image selected"}), 400

        # Create filename with metadata
        file_ext = os.path.splitext(file.filename)[1]
        filename = f"{label}_{timestamp}{file_ext}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Save the file
        file.save(filepath)

        # Log information
        print(f"[{datetime.datetime.now().isoformat()}] Detection received:")
        print(f"- Label: {label}")
        print(f"- Timestamp: {timestamp}")
        print(f"- File saved: {filepath}")

        # Send success response
        return jsonify(
            {
                "success": True,
                "message": "Image received and saved successfully",
                "metadata": {
                    "label": label,
                    "timestamp": timestamp,
                    "filename": filename,
                },
            }
        )

    except Exception as e:
        print(f"Error handling image upload: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Error processing image upload",
                    "error": str(e),
                }
            ),
            500,
        )


# Endpoint for receiving text data
@app.route("/print-text", methods=["POST"])
def print_text():
    try:
        # Get request data
        data = request.get_json() if request.is_json else request.form.to_dict()

        # Log the received data
        print(f"[{datetime.datetime.now().isoformat()}] Text data received:")
        print(json.dumps(data, indent=2))

        # Send success response
        return jsonify(
            {
                "success": True,
                "message": "Text data received successfully",
                "receivedData": data,
            }
        )

    except Exception as e:
        print(f"Error handling text data: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Error processing text data",
                    "error": str(e),
                }
            ),
            500,
        )


# Simple health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.datetime.now().isoformat()})


# Serve uploaded files
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# Start the server
if __name__ == "__main__":
    print(f"Detection server running on port {PORT}")
    print(f"- Image endpoint: http://localhost:{PORT}/recv-image")
    print(f"- Text endpoint: http://localhost:{PORT}/print-text")
    print(f"- Health check: http://localhost:{PORT}/health")
    print(f"- View uploads: http://localhost:{PORT}/uploads")

    # Run the Flask app
    app.run(host="0.0.0.0", port=PORT, debug=True)
