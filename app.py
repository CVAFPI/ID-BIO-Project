import os
import sys
import time
import signal
import subprocess
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response

# --- Optional Biometric & Computer Vision Libraries ---
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# --- Universal TFLite / LiteRT Engine Loader ---
tflite = None
TFLITE_ENGINE = "Disabled"

try:
    import ai_edge_litert.interpreter as tflite
    TFLITE_ENGINE = "Google LiteRT (ai-edge-litert)"
except ImportError:
    try:
        import tflite_runtime.interpreter as tflite
        TFLITE_ENGINE = "tflite-runtime"
    except ImportError:
        try:
            import tensorflow.lite as tflite
            TFLITE_ENGINE = "TensorFlow Lite"
        except ImportError:
            TFLITE_ENGINE = "None (OpenCV Only)"

# Initialize Flask App
app = Flask(__name__)

print(f"[*] Starting CVAFPI Core Server...")
print(f"[*] ML Engine detected: {TFLITE_ENGINE}")


# ==============================================================================
# Helper Functions & Model Loaders
# ==============================================================================

def load_tflite_model(model_path):
    """Safely loads a TFLite model using whichever interpreter is installed."""
    if not tflite or not os.path.exists(model_path):
        return None
    try:
        interpreter = tflite.Interpreter(model_path=model_path)
        interpreter.allocate_tensors()
        return interpreter
    except Exception as e:
        print(f"[!] Error loading TFLite model: {e}")
        return None


def generate_camera_feed():
    """Generates MJPEG stream for live webcam / biometric scanner UI."""
    if not CV2_AVAILABLE:
        return
    
    # Open default system camera (0)
    cap = cv2.VideoCapture(0)
    
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # Add basic visual overlay (e.g., target reticle for scanning)
        height, width, _ = frame.shape
        cv2.rectangle(frame, (int(width * 0.3), int(height * 0.2)),
                             (int(width * 0.7), int(height * 0.8)), (0, 255, 0), 2)
        
        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
    cap.release()


# ==============================================================================
# Web Routes (HTML UI)
# ==============================================================================

@app.route('/')
def index():
    """Renders the main system dashboard / kiosk menu."""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """Live MJPEG video feed route for biometrics/scanning UI."""
    return Response(generate_camera_feed(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ==============================================================================
# API Endpoints (Kiosk Button Actions)
# ==============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns engine and backend status."""
    return jsonify({
        "status": "online",
        "engine": TFLITE_ENGINE,
        "opencv": CV2_AVAILABLE,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route('/api/scan', methods=['POST'])
def trigger_scan():
    """Handles 'LAUNCH REGISTRY SCANNER' action."""
    print("[+] Triggering Registry Scanner...")
    # Add face detection or database matching logic here
    return jsonify({"status": "success", "message": "Scanner initialized"})


@app.route('/api/database', methods=['GET', 'POST'])
def handle_database():
    """Handles 'OPEN DATABASE MANAGER' action."""
    return jsonify({"status": "success", "message": "Database records loaded", "count": 0})


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Handles 'OPEN LOGS MANAGER' action."""
    sample_logs = [
        f"[{datetime.now().strftime('%H:%M:%S')}] System auto-launcher initialized.",
        f"[{datetime.now().strftime('%H:%M:%S')}] Active ML Engine: {TFLITE_ENGINE}"
    ]
    return jsonify({"status": "success", "logs": sample_logs})


@app.route('/api/reboot', methods=['POST'])
def reboot_system():
    """Handles 'REBOOT' button."""
    print("[!] Reboot command received...")
    try:
        subprocess.Popen(["sudo", "reboot"])
        return jsonify({"status": "rebooting", "message": "System is restarting..."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/shutdown', methods=['POST'])
def shutdown_system():
    """Handles 'SHUTDOWN' button."""
    print("[!] Shutdown command received...")
    try:
        subprocess.Popen(["sudo", "poweroff"])
        return jsonify({"status": "shutting_down", "message": "System is shutting down..."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/exit', methods=['POST'])
def exit_system():
    """Handles 'EXIT SYSTEM' button (kills Flask server cleanly)."""
    print("[!] Exit command received. Terminating backend...")
    
    # Schedule process termination after responding to client
    def kill_server():
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGINT)
        
    import threading
    threading.Thread(target=kill_server).start()
    
    return jsonify({"status": "exiting", "message": "Server process stopped."})


# ==============================================================================
# Application Entrypoint
# ==============================================================================

if __name__ == '__main__':
    # Listens locally on port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
