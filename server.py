from flask import Flask, jsonify, request
import asyncio
import hashlib
import datetime
from flask_cors import CORS, cross_origin
from bllengine import resume_parser_function
import re
# resume_parsing 
#Resume Parsing
#Parsing the resume===============================================>>>>>>>>>>>>>>>>>>>>>>
app = Flask(__name__)
@app.route('/resume', methods=['POST'])
async def parse_resume():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        if file and file.filename.endswith('.pdf'):
            file_content = file.read()
            
            result = await resume_parser_function({
                'file_content': file_content,
                'skills_file_path': 'skills.txt',
                'education_file_path':'education.txt'
            })

            return jsonify(result)
        else:
            return jsonify({"error": "Invalid file format. Only PDF files are allowed."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

async def main():
    asyncio.get_event_loop()

if __name__ == "__main__":
    asyncio.run(main())
    app.run(host="0.0.0.0",debug=True)
   
