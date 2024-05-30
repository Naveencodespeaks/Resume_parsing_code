import re
import spacy
import asyncio
import aiofiles
import fitz  # This imports the PyMuPDF library correctly
import os
import hashlib
import datetime
import requests
from main import parse_resume

# resume_parsing 
# Read skills from a text file
async def read_skills_from_file(file_path):
    try:
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as file:
            skills = await file.read()
        return skills.splitlines()
    except Exception as e:
        print(f"Error reading skills file: {e}")
        return []

# Read education from a text file
async def read_education_details_from_file(file_path):
    try:
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as file:
            education_details = await file.readlines()
        unique_education_details = set()
        for detail in education_details:
            detail = detail.strip()
            if detail not in unique_education_details:
                unique_education_details.add(detail)
        return list(unique_education_details)
    except Exception as e:
        print(f"Error reading education details file: {e}")
        return []


# Deduplicate skills
# This helps only to return the skills which are occurs once
def deduplicate_skills(skills):
    return list(set(skills))

# Deduplicate skills
# This helps only to return the Education which are occurs once
def deduplicate_education(education_details):
    return list(set(education_details))


# This extract the Total_years from the resume.
async def extract_experience_from_resume(text):
    # Regular expression patterns to match different formats of experience
    patterns = [
        r'(\d+(\.\d+)?)\s*(?:year|yr)s?(?:\s*(?:and|&)?\s*(\d+)\s*(?:month|mo)s?)?',  # Matches '2.6 years', '4 years 8 months'
        r'(\d+)\s*(?:year|yr)s?\s*(\d+)\s*(?:month|mo)s?',  # Matches '4 years 8 months'
        r'(\d+)\s*(?:year|yr)s?',  # Matches '4 years'
        r'(\d+)\s*[-–]\s*(\d+)\s*(?:year|yr)s?',  # Matches '2 - 5 years'
        r'(\d+)\s*(?:to)\s*(\d+)\s*(?:year|yr)s?',  # Matches '2 to 5 years'
        r'(\d+)\s*\+?\s*(?:year|yr)s?',  # Matches '1+ years'
        r'(\d+)\s*(?:Year(?:s)?)\s*(\d+)\s*(?:Month(?:s)?)',  # Matches '3 Year 6 Months'
        r'(\d+)\s*(?:Year(?:s)?)\s*and\s*(\d+)\s*(?:Month(?:s)?)',  # Matches '3 Years and 6 Months'
        r'(\d+)\s*(?:Year(?:s)?)\s*(\d+)\s*to\s*(\d+)\s*(?:Year(?:s)?)\s*(\d+)\s*(?:Month(?:s)?)',  # Matches '2 Years 6 Months to 4 Years 3 Months'
        r'(\d+)\s*to\s*(\d+)\s*Years\s*(\d+)\s*Months',  # Matches '2 to 5 Years 6 Months'
        r'(\d+)\s*Years?\s*(\d+)\s*Months?',  # Matches '5 Years 6 Months'
        r'(\d+)\s*Years?\s*(?:and)?\s*(\d+)\s*Months?',  # Matches '5 Years and 6 Months'
        r'(\d+)\s*Years?\s*(\d+)\s*to\s*(\d+)\s*Years?\s*(\d+)\s*Months?',  # Matches '5 Years 3 to 7 Years 6 Months'
        r'(\d+)\s*Years?\s*(?:of)?\s*(?:experience)?',  # Matches '5 Years of experience'
        r'(\d+)\s*Years?\s*(?:of)?\s*(?:professional)?\s*(?:experience)?',  # Matches '5 Years of professional experience'
    ]
    
    # Loop through each pattern and try to match with the text
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Get the matched groups
            groups = match.groups()
            if len(groups) == 1:  # If only one group matched
                return groups[0] + ' years'
            elif len(groups) == 2:  # If two groups matched
                years = groups[0] if groups[0] else '0'
                months = groups[1] if groups[1] and int(groups[1]) > 0 else None
                if months:
                    return years + ' years ' + months + ' months'
                else:
                    return years + ' years'
            elif len(groups) == 3:  # If three groups matched
                years = groups[0] if groups[0] else '0'
                months = groups[2] if groups[2] and int(groups[2]) > 0 else None
                if months:
                    return years + ' years ' + months + ' months'
                else:
                    return years + ' years'
            elif len(groups) == 4:  # If four groups matched
                years1 = groups[0] if groups[0] else '0'
                years2 = groups[2] if groups[2] else '0'
                months = groups[3] if groups[3] and int(groups[3]) > 0 else None
                if months:
                    return f'{years1} years {years2} years ' + months + ' months'
                else:
                    return f'{years1} years {years2} years'
    
    # If no match found, return "Fresher"
    return "Fresher"

# extracting name from the resume.
# Load the English language model
nlp = spacy.load("en_core_web_sm")

async def extract_name_from_resume(file_content):
    # Split the file content by newline characters
    lines = file_content.strip().split("\n")
    
    # Extract the name from the first line
    name = lines[0].strip()
    
    return name

async def extract_contact_number_from_resume(text):
    try:
        pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        matches = re.findall(pattern, text)
        if matches:
            ph_num = clean_phone_number(matches[-1:-6])  # Return the last match
        return ph_num
    except Exception as e:
        print(f"Error extracting contact number: {e}")
        return ''

# Extract email from resume text
async def extract_email_from_resume(text):
    try:
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        match = re.search(pattern, text)
        if match:
            return match.group()
        return ''
    except Exception as e:
        print(f"Error extracting email: {e}")
        return ''

# Extract Education_details  from education.txt file(which matches the resume)
async def extract_education_from_resume(text, education_file_path):
    try:
        education_patterns = await read_education_details_from_file(education_file_path)

        education_found = []
        for skill in education_patterns:
            # Use word boundaries to ensure skill matches whole words
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                education_found.append(skill)

        return deduplicate_education(education_found)
    except Exception as e:
        print(f"Error extracting skills: {e}")
        return []
    
# Extract the candidate skill from the skill.txt(which are present in the resume)
async def extract_skills_from_resume(text, skills_file_path):
    try:
        skills_patterns = await read_skills_from_file(skills_file_path)

        skills_found = []
        for skill in skills_patterns:
            # Use word boundaries to ensure skill matches whole words
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                skills_found.append(skill)

        return deduplicate_skills(skills_found)
    except Exception as e:
        print(f"Error extracting skills: {e}")
        return []
    
# Extract candidate_Name from the resume from the email_id
# async def extract_name(text):
#     try:
#         pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
#         match = re.search(pattern, text)
        
#         # If email address is found, extract the name from it
#         if match:
#             email = match.group()
#             name = email.split('@')[0]  # Extract name before '@'
#             # Remove numbers and symbols from the name
#             name = re.sub(r'[^A-Za-z\s]', '', name)
#             return  ' ' #name.strip() ##This will give the name which is present in the mail_id 
#         else:
#             return ''
#     except Exception as e:
#         print(f"Error extracting name: {e}")
#         return ''

# Extract phone number from resume text
async def extract_phone_from_resume(text):
    try:
        pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        matches = re.findall(pattern, text)
        if matches:
            return clean_phone_number(matches[-1])  # Return the last match
        return ''
    except Exception as e:
        print(f"Error extracting contact number: {e}")
        return ''

def clean_phone_number(phone_number):
    # Clean the phone number if needed, for example, remove spaces, dots, etc.
    cleaned = phone_number[len(phone_number)-10:]
    return cleaned


# Extract links to Git and LinkedIn profiles from resume text
async def extract_social_links_from_resume(text):
    try:
        pattern_git = r"github.com/([A-Za-z0-9_-]+)"
        match_git = re.search(pattern_git, text)
        git_link = f"https://github.com/{match_git.group(1)}" if match_git else ''

        pattern_linkedin = r"linkedin.com/in/([A-Za-z0-9_-]+)"
        match_linkedin = re.search(pattern_linkedin, text)
        linkedin_link = f"https://linkedin.com/in/{match_linkedin.group(1)}" if match_linkedin else ''

        return {'git_link': git_link, 'linkedin_link': linkedin_link}
    except Exception as e:
        print(f"Error extracting social links: {e}")
        return {'git_link': '', 'linkedin_link': ''}
   
# Extract the text from the pdf
async def extract_text_from_pdf(file_content):
    try:
        # Open the PDF from the bytes content
        pdf_document = fitz.open(stream=file_content, filetype="pdf")
        text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ''

async def resume_parser_function(request_data):
    try:
        file_content = request_data['file_content']
        skills_file_path = request_data['skills_file_path']
        education_file_path = request_data['education_file_path']
        request_id = request_data.get('request_id', '')
        request_src = request_data.get('request_src', '')

        # Ensure file_content is a string
        if isinstance(file_content, bytes):
            try:
                # Attempt to decode as text
                file_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                # If it's a PDF, extract the text from the PDF
                file_content = await extract_text_from_pdf(file_content)

#print the content for debugging purpose.
        # Print the file content for debugging
        #print("File Content:", file_content)
        # print("Skills File Path:", skills_file_path)
        # print("Education File Path:", education_file_path)

        # name = await extract_name(file_content)
        email = await extract_email_from_resume(file_content)
        phone = await extract_phone_from_resume(file_content)
        skills = await extract_skills_from_resume(file_content, skills_file_path)
        social_link = await extract_social_links_from_resume(file_content)
        education = await extract_education_from_resume(file_content, education_file_path)
        experience = await extract_experience_from_resume(file_content)
        Name = await extract_name_from_resume(file_content)
        
        response_success = {
            "response_id": request_id,
            "response_for": "Resume_Parser",
            "response_set_to": request_src,
            "response": {
                "message": "Fetched the data successfully!",
                "data": {
                    # "name": name,
                    "email": email,
                    "phone": phone,
                    "skills": skills,
                    "Education": education,
                    "experience": experience,
                    "Name_of_candidate": Name,
                    "social_media_links":social_link
                }
            }
        }
        return response_success
    except Exception as e:
        print(f"Error in resume_parser_function: {e}")
        return {"error": f"An error occurred: {str(e)}"}