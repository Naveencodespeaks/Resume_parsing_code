#Parsing the resume===============================================>>>>>>>>>>>>>>>>>>>>>>
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
                'skills_file_path': 'reqhandlers/skills.txt',
                'education_file_path':'reqhandlers/education.txt'
            })

            return jsonify(result)
        else:
            return jsonify({"error": "Invalid file format. Only PDF files are allowed."}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    asyncio.run(main())
    app.run(host="0.0.0.0",debug=True)
    #app.run(host="0.0.0.0",port=5012,debug=True,ssl_context=context)