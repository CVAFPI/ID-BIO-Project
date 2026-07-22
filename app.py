import os
import sys
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Load HTML files and static assets directly from root directory
app = Flask(__name__, template_folder='.', static_folder='.')

# ==============================================================================
# CROSS-PLATFORM ML ENGINE DETECTION
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
# PAGE ROUTE HANDLERS (Supports button links ending in .html)
# ==============================================================================

@app.route('/')
@app.route('/launchpad')
@app.route('/launchpad.html')
def launchpad():
    return render_template('launchpad.html')


@app.route('/scanner')
@app.route('/scanner.html')
def scanner():
    return render_template('scanner.html')


@app.route('/manager')
@app.route('/manager.html')
def manager():
    return render_template('manager.html')


@app.route('/logs-manager')
@app.route('/logs-manager.html')
def logs_manager():
    return render_template('logs-manager.html')


# ==============================================================================
# ERROR HANDLERS
# ==============================================================================

@app.errorhandler(404)
def page_not_found(e):
    return f"<h2>404 - Page Not Found</h2><p>The requested route does not exist.</p>", 404


@app.errorhandler(500)
def internal_server_error(e):
    return f"<h2>500 - Internal Server Error</h2><p>Details: {e}</p>", 500


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
