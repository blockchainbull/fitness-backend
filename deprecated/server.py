from waitress import serve
from deprecated.api import app  # Import your Flask app

if __name__ == '__main__':
    print("Starting server on http://0.0.0.0:5000")
    serve(app, host='0.0.0.0', port=5000)