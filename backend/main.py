import firebase_admin
from firebase_admin import credentials, storage
from google.cloud import aiplatform
from flask import Flask, request, jsonify
import os
import base64
import uuid

# Initialize Flask app
app = Flask(__name__)


def initialize_firebase():
    """Initializes Firebase Admin SDK."""
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(
            os.path.join(os.path.dirname(__file__), "ndou-dev-test-83775e3696cf.json")
        )  # Path to your key inside 'backend'
        firebase_admin.initialize_app(cred,
        {'storageBucket':'ndou-dev-test.appspot.com'}
        )


def upload_image(file):
    """Uploads image to Firebase Storage and returns public URL"""
    bucket = storage.bucket()
    blob_name = f"user_images/{str(uuid.uuid4())}-{file.filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_file(file)

    public_url = blob.generate_signed_url(
        version="v4",
         expiration=None,
         method="GET"
      )
    return public_url

def call_gemini_api(image_data):
  """Calls the Gemini API to extract text from image data"""
  aiplatform.init(project="ndou-dev-test", location="us-central1") # Replace with your project and location

  model = aiplatform.GenerativeModel("gemini-pro-vision") #Use correct name for your project
  prompt = "Extract all relevant information from the document"

  contents = [
      {
      "parts": [
              {"text": prompt},
            {
                "inline_data": {
                   "data":base64.b64encode(image_data).decode("utf-8"),
                   "mime_type": "image/png"
                  }
               },
              ],
      }
  ]

  response = model.generate_content(contents=contents)

  return response.text


@app.route('/api/extract-info', methods=['POST'])
def extract_info():
    initialize_firebase()

    if 'images' not in request.files:
        return jsonify({'error': 'No images uploaded'}), 400

    uploaded_files = request.files.getlist('images')

    if not uploaded_files:
        return jsonify({'error':'No file selected'})

    extracted_texts = []
    for image_file in uploaded_files:
        try:
            # Upload image to firebase
            url = upload_image(image_file)
            # Get contents of the file
            image_file.seek(0)
            image_data = image_file.read()
            # Call Gemini to extract the data
            extracted_text = call_gemini_api(image_data)
            extracted_texts.append(extracted_text)
        except Exception as e:
            print(e)
            return jsonify({'error': f'Error processing image: {e}'}), 500

    return jsonify({'extracted_text': '\n'.join(extracted_texts)})

if __name__ == '__main__':
   app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)
