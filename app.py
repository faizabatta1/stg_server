from flask import Flask, request, jsonify
import os
from script import translate

app = Flask(__name__)

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
    app.run()