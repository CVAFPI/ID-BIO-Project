import os
import sys
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

# ==============================================================================
# CROSS-PLATFORM ML ENGINE DETECTION (ARM64 & x86_64 Compatible)
# ==============================================================================
ML_ENGINE = None

try:
    import ai_edge_litert.interpreter as litert
    ML_ENGINE = "Google LiteRT (ai-edge-litert)"
except ImportError:
    try:
        import tflite_runtime.interpreter as tflite
        ML_ENGINE = "TFLite Runtime"
    except ImportError:
        try:
            import tensorflow.lite as tflite
            ML_ENGINE = "TensorFlow Full"
        except ImportError:
            ML_ENGINE = "None (Disabled / Hardware Fallback)"

print(f"[*] Starting CVAFPI Core Server...")
print(f"[*] ML Engine detected: {ML_ENGINE}")


# ==============================================================================
# PAGE ROUTE HANDLERS
# ==============================================================================

@app.route('/')
def index():
    """Main Entry Point - Renders the Launchpad Dashboard."""
    return render_template('launchpad.html')


@app.route('/scanner')
def scanner():
    """
    Barcode / HID Scanner Interface.
    Works natively with USB Barcode Scanners (HID Keyboard Emulation)
    without requiring physical camera hardware.
    """
    return render_template('scanner.html')


@app.route('/manager')
def manager():
    """System / Database Management Interface."""
    return render_template('manager.html')


@app.route('/logs-manager')
def logs_manager():
    """Attendance and Log Records Interface."""
    return render_template('logs-manager.html')


# ==============================================================================
# ERROR HANDLERS (Prevents generic blank 500 pages during debugging)
# ==============================================================================

@app.errorhandler(404)
def page_not_found(e):
    return f"<h2>404 - Page Not Found</h2><p>The requested route does not exist.</p>", 404


@app.errorhandler(500)
def internal_server_error(e):
    return f"<h2>500 - Internal Server Error</h2><p>Details: {e}</p><p>Check terminal output for traceback.</p>", 500


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

if __name__ == '__main__':
    # Binds to 0.0.0.0 so both local browser and network clients can connect
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
