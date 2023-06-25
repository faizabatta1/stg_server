from flask import Flask, request, jsonify
import os
from script import translate

from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins='*', methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers='*')

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.post('/translate-image')
def translate_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'})

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'No selected image file'})

    # Save the image file in the static folder
    image_path = os.path.join('static', image_file.filename)
    image_file.save(image_path)

    # Execute the translate function using the image path
    translation = translate(image_path)
    print(translation)

    # Return the translation as a response
    return translation

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5020,debug=True)