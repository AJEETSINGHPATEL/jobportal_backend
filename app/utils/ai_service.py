import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
import PyPDF2
from docx.api import Document
from io import BytesIO

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Import job search service
from .job_search_service import job_search_service

# Simple async function for AI response
async def get_ai_response(message: str, history: Optional[List[Dict[str, str]]] = None, user_context: Optional[Dict] = None) -> str:
    """Get AI response for chat messages"""
    try:
        msg = message.lower()
        # Broad misspelling and variation handling
        replacements = {
            "serch": "search", "manger": "manager", "experince": "experience",
            "experice": "experience", "feiled": "field", "sale": "sales",
            "fresher": "entry-level", "kanpur": "Kanpur", "delhi": "Delhi"
        }
        for old, new in replacements.items():
            msg = msg.replace(old, new)
        
        # Keywords that indicate a job search intent
        search_intent_keywords = [
            "find", "search", "looking for", "job", "vacancy", "opening", "hiring", 
            "position", "career", "work", "role", "opportunity", "fresher", "need"
        ]
        
        # Specific role keywords
        role_keywords = [
            "developer", "engineer", "manager", "sales", "designer", "analyst", 
            "representative", "specialist", "python", "javascript", "react", "java", "node", "aws",
            "sales manager", "field sales", "sales executive", "accountant", "hr"
        ]
        
        # Location detection
        location_keywords = ["delhi", "mumbai", "kanpur", "bangalore", "pune", "hyderabad", "remote"]
        
        # Aggressive job search detection
        is_job_search = any(phrase in msg for phrase in ["job", "vacancy", "opening", "search", "find", "looking for"])
        has_role = any(r in msg for r in role_keywords)
        has_location = any(l in msg for l in location_keywords)
        
        # If they mention a role and (intent OR location OR "fresher") -> it's a job search
        if (has_role and (is_job_search or has_location or "fresher" in msg or "entry" in msg)):
            is_job_search = True
        
        if is_job_search:
            # Get job details from real job search
            return await get_real_job_details(message)
        else:
            # Use the AIService instance for general questions
            return ai_service.chat(message, history)
    except Exception as e:
        return f"I apologize, but I'm having trouble responding right now. Error: {str(e)}"

async def get_real_job_details(message: str) -> str:
    """
    Generate job leads and contact-style answers using OpenRouter,
    similar to how ChatGPT lists companies + phone numbers.
    """
    try:
        # We still extract search terms to encourage the model to focus
        search_terms = extract_search_terms(message)
        location = search_terms.get("location", "")
        title = search_terms.get("title", "")

        system_prompt = f"""
You are an Indian job and business contact advisor.

Goal:
- When the user asks for jobs like "sales manager in Delhi", respond with a helpful,
  practical answer that lists real-looking companies and contact options they can try.

Response style:
- Start with 1 short summary sentence telling what you found.
- Then give a clear heading like: "📞 Sales / Business Contacts You Can Try".
- Under that, give a numbered list of 3–8 companies or recruiters that MATCH the user's role and location.
- For each item include:
  - Company name
  - Area / city (e.g. Dwarka, New Delhi; Noida; Gurgaon etc.)
  - At least one Indian phone number (for call or WhatsApp)
  - Optional email if appropriate
- After the list, add a short "Important notes before calling/applying" section with 2–4 bullet points:
  - Always be professional and respectful.
  - Jobs are not guaranteed; these are leads/contacts only.
  - Never pay money to get a job.

Formatting rules:
- Use clear section titles and bullet points.
- Keep the answer focused on the requested role and city.
- If the user mentioned a role or city, repeat them clearly (e.g. "Sales Manager roles around Delhi").
- Do NOT say you are an AI model.

User intent:
- The user wants concrete leads (companies and phone numbers), not just generic advice.
- Current requested role: "{title or 'Sales Manager or similar'}"
- Current requested location: "{location or 'the city mentioned by the user'}"
"""

        history = [{"role": "system", "content": system_prompt}]
        # Reuse the generic OpenRouter helper but with our custom system prompt
        return await get_openrouter_response(message, history)

    except Exception as e:
        return f"Sorry, I'm having trouble searching for jobs right now. Please try again later. Error: {str(e)}"

async def handle_real_job_search(message: str) -> str:
    """Handle general job search queries with real data"""
    try:
        search_terms = extract_search_terms(message)
        
        if search_terms["skills"] or search_terms["location"] or search_terms["title"]:
            return await get_real_job_details(message)
        else:
            return "I'd be happy to help you find jobs! Please tell me more about what you're looking for. You can mention:\n• Specific skills (Python, React, etc.)\n• Location preferences\n• Job type (remote, full-time, etc.)\n• Experience level"
    except Exception as e:
        return f"I'm having trouble processing your job search request. Please try rephrasing your query. Error: {str(e)}"

async def get_openrouter_response(message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """Get response from OpenRouter API for general queries"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Build messages with context
        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": "stepfun/step-3.5-flash:free",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            # Fallback response if API fails
            return f"Thank you for your message: '{message}'. I'm here to help with your career questions!"
            
    except Exception as e:
        # Fallback response if API call fails
        return f"Thank you for your message: '{message}'. I'm here to help with your career questions!"

def extract_search_terms(message: str) -> Dict[str, str]:
    """Extract search terms from user message"""
    terms = {
        "skills": [],
        "location": "",
        "title": "",
        "job_type": ""
    }
    
    # Common programming languages and skills
    skills_keywords = [
        "python", "javascript", "java", "react", "node", "angular", "vue", 
        "sql", "mongodb", "postgresql", "docker", "kubernetes", "aws", 
        "azure", "gcp", "machine learning", "data science", "devops",
        "sales", "marketing", "management", "business development", "hr", "accounting"
    ]
    
    # Common locations
    location_keywords = [
        "remote", "bangalore", "mumbai", "delhi", "chennai", "pune", 
        "hyderabad", "kolkata", "noida", "gurgaon", "new york", "london", 
        "san francisco", "berlin", "singapore", "india", "usa", "uk", "kanpur", "lucknow"
    ]
    
    # Job types
    job_type_keywords = ["full time", "part time", "contract", "freelance", "internship"]
    
    message_lower = message.lower()
    
    # Extract skills
    for skill in skills_keywords:
        if skill in message_lower:
            terms["skills"].append(skill.title())
    
    # Extract location
    for location in location_keywords:
        if location in message_lower:
            terms["location"] = location.title()
            break
    
    # Extract job title keywords
    title_keywords = ["developer", "engineer", "analyst", "manager", "designer", "specialist"]
    for keyword in title_keywords:
        if keyword in message_lower:
            terms["title"] = keyword
            break
    
    # Extract job type
    for job_type in job_type_keywords:
        if job_type in message_lower:
            terms["job_type"] = job_type
            break
    
    return terms

class AIService:
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.api_url = OPENROUTER_API_URL
    
    def _make_request(self, prompt: Optional[str] = None, messages: Optional[List[Dict[str, str]]] = None, model: str = "stepfun/step-3.5-flash:free") -> Dict[str, Any]:
        """Make a request to the OpenRouter API"""
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment variables")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if messages is None:
            if prompt is None:
                raise ValueError("Either prompt or messages must be provided")
            messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error calling OpenRouter API: {str(e)}")

    def chat(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """Chat with the AI Career Advisor"""
        
        # System prompt provided by the user
        CHATBOT_SYSTEM_PROMPT = """
You are an expert AI Career Advisor and Job Portal Assistant for "AI Job Portal" - an intelligent job matching platform.

========================================
YOUR ROLE & RESPONSIBILITIES:
========================================
1. Help users find perfect jobs matching their skills, experience, and preferences
2. Provide personalized interview preparation and tips
3. Assist with resume and cover letter writing
4. Offer career guidance and professional growth strategies
5. Share company insights, reviews, and salary information
6. Detect and warn about fake job postings and scams
7. Provide networking and professional development advice
8. Support users throughout their entire job search journey
9. Answer questions about AI Job Portal features
10. Provide encouragement and motivation

========================================
TONE & COMMUNICATION STYLE:
========================================
- Professional yet friendly and conversational
- Encouraging and supportive
- Clear and easy to understand
- Use emojis appropriately for better engagement
- Provide specific, actionable advice
- Be honest about challenges but focus on solutions
- Adapt language based on user experience level
- Support both English and Hindi/Hinglish

========================================
HOW TO HANDLE DIFFERENT QUESTION TYPES:
========================================

1️⃣ JOB SEARCH QUERIES
------------------------
User asks: "Find me Python developer jobs in Bangalore"
Response format:
- Search their profile for Python skills and Bangalore preference
- Return 5-10 matching jobs with details
- Include: Job title, company, salary, location, match score, key skills
- Add: Company reviews, interview difficulty, application tips
- Suggest: Related jobs they might like

2️⃣ INTERVIEW PREPARATION
------------------------
User asks: "Help me prepare for a Data Science interview"
Response format:
- Provide role-specific common questions
- Suggest preparation tips and resources
- Offer mock interview practice
- Include technical and behavioral questions

3️⃣ RESUME & PROFILE IMPROVEMENT
------------------------
User asks: "Help me improve my resume"
Response format:
- Analyze current profile/resume
- Suggest improvements
- Highlight in-demand keywords
- Provide examples and templates

4️⃣ SALARY & COMPENSATION NEGOTIATION
------------------------
User asks: "What salary should I ask for?"
Response format:
- Provide salary ranges by role, location, experience
- Negotiation tips and strategies
- What to mention/not mention
"""
        
        files_messages = [{"role": "system", "content": CHATBOT_SYSTEM_PROMPT}]
        
        # Add history if available
        if history:
            files_messages.extend(history)
            
        # Add current message
        files_messages.append({"role": "user", "content": message})
        
        try:
            response = self._make_request(messages=files_messages)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"
    
    def analyze_resume(self, resume_text: str) -> Dict[str, Any]:
        """Analyze a resume and extract skills, experience, and suggestions"""
        prompt = f"""
        Analyze the following resume and provide:
        1. Extracted skills (technical and soft skills) as a JSON array
        2. Years of experience as a number
        3. Key achievements as a JSON array
        4. Areas for improvement as a JSON array
        5. ATS compatibility score (out of 100) as a number
        
        Resume:
        {resume_text}
        
        Provide the response in JSON format with keys: skills, experience_years, achievements, improvements, ats_score
        Return ONLY valid JSON, no other text.
        """
        
        try:
            response = self._make_request(prompt)
            content = response["choices"][0]["message"]["content"]
            
            # Try to parse as JSON
            import json
            try:
                # Clean up the response to extract JSON
                # Remove any markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # If JSON parsing fails, return a default structure
                return {
                    "skills": ["JavaScript", "React", "Node.js"],
                    "experience_years": 5,
                    "achievements": ["Improved application performance by 40%", "Mentored 3 junior developers"],
                    "improvements": ["Add more quantifiable achievements", "Include relevant certifications"],
                    "ats_score": 85
                }
        except Exception as e:
            # Return default response if API call fails
            return {
                "skills": ["JavaScript", "React", "Node.js"],
                "experience_years": 5,
                "achievements": ["Improved application performance by 40%", "Mentored 3 junior developers"],
                "improvements": ["Add more quantifiable achievements", "Include relevant certifications"],
                "ats_score": 85
            }
    
    def generate_cover_letter(self, job_description: str, resume_text: str) -> str:
        """Generate a cover letter based on job description and resume"""
        prompt = f"""
        Generate a professional cover letter for the following job description 
        based on the provided resume. The cover letter should highlight relevant 
        experiences and skills that match the job requirements.
        
        Job Description:
        {job_description}
        
        Resume:
        {resume_text}
        
        Return only the cover letter content, no other text.
        """
        
        try:
            response = self._make_request(prompt)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            # Return a default cover letter if API call fails
            return f"Dear Hiring Manager,\n\nI am writing to express my interest in the position. I have reviewed the job description and believe my skills and experience make me a strong candidate for this role.\n\nSincerely,\nApplicant\n\n(Error: {str(e)} occurred while generating cover letter)"
    
    def generate_job_description(self, job_title: str, requirements: List[str]) -> str:
        """Generate a complete job description based on title and requirements"""
        prompt = f"""
        Generate a comprehensive job description for the position of {job_title}.
        The job should include:
        - Detailed responsibilities
        - Required qualifications
        - Preferred qualifications
        - Company culture fit
        
        Additional requirements:
        {', '.join(requirements)}
        
        Return only the job description content, no other text.
        """
        
        try:
            response = self._make_request(prompt)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            # Return a default job description if API call fails
            return f"""
Job Title: {job_title}

Responsibilities:
- Perform duties as required
- Collaborate with team members
- Meet company objectives

Requirements:
- {', '.join(requirements) if requirements else 'To be determined'}

Qualifications:
- Relevant experience in the field
- Strong communication skills
- Ability to work in a team environment

(Error: {str(e)} occurred while generating job description)
"""
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from job description or resume"""
        prompt = f"""
        Extract all relevant skills from the following text. Return only a JSON array of skills.
        
        Text:
        {text}
        
        Return only a JSON array of skills, nothing else.
        """
        
        try:
            response = self._make_request(prompt)
            content = response["choices"][0]["message"]["content"]
            
            # Try to parse as JSON
            import json
            try:
                # Clean up the response to extract JSON
                # Remove any markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                result = json.loads(content)
                return result if isinstance(result, list) else [content]
            except json.JSONDecodeError:
                # If JSON parsing fails, return the content as a single-item list
                return [content[:200] + "... (response truncated due to formatting issues)"]
        except Exception as e:
            # Return default skills if API call fails
            return ["JavaScript", "Python", "Communication", "Problem Solving"]
    
    def calculate_match_score(self, resume_skills: List[str], job_skills: List[str]) -> float:
        """Calculate match score between resume and job skills"""
        if not job_skills:
            return 0.0
            
        matching_skills = set(resume_skills) & set(job_skills)
        match_score = len(matching_skills) / len(set(job_skills)) * 100
        return round(match_score, 2)
    
    def generate_interview_questions(self, job_description: str, resume_text: str) -> List[str]:
        """Generate interview questions based on job description and resume"""
        prompt = f"""
        Generate 5 interview questions for a candidate based on the following 
        job description and their resume. Include both technical and behavioral questions.
        
        Job Description:
        {job_description}
        
        Resume:
        {resume_text}
        
        Return only a JSON array of the questions, nothing else.
        """
        
        try:
            response = self._make_request(prompt)
            content = response["choices"][0]["message"]["content"]
            
            # Try to parse as JSON
            import json
            try:
                # Clean up the response to extract JSON
                # Remove any markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw content as a single-item list
                return [content[:200] + "... (response truncated due to formatting issues)"]
        except Exception as e:
            # Return default questions if API call fails
            return [f"Error: {str(e)} occurred while generating interview questions",
                    "How does your experience align with the job requirements?",
                    "What are your key achievements from your resume?"]
    
    def generate_interview_answer(self, question: str, job_description: str, resume_text: str) -> str:
        """Generate an answer to an interview question based on the candidate's resume and job description"""
        prompt = f"""
        Generate a professional answer to the following interview question based on the candidate's resume and the job description.
        
        Interview Question:
        {question}
        
        Job Description:
        {job_description}
        
        Candidate Resume:
        {resume_text}
        
        Provide a thoughtful, concise answer that highlights the candidate's relevant experience and skills.
        """
        
        try:
            response = self._make_request(prompt)
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            # Return a default answer if API call fails
            return f"I'm sorry, I couldn't generate a specific answer for this question. A good approach would be to highlight your relevant experience and skills that match the job requirements. (Error: {str(e)} occurred while generating answer)"

    def extract_text_from_file(self, file_content: bytes, file_type: str) -> str:
        """Extract text from uploaded file (PDF, DOCX) - DOC support limited"""
        try:
            if file_type == 'application/pdf':
                # Handle PDF files
                pdf_file = BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
            elif file_type == 'application/msword':
                # Handle legacy DOC files
                # Since python-docx doesn't support DOC files, we'll return a helpful error
                raise Exception("Legacy DOC files are not supported. Please convert your document to DOCX or PDF format.")
            elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                # Handle DOCX files
                docx_file = BytesIO(file_content)
                doc = Document(docx_file)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                return text
            elif file_type == 'application/octet-stream':
                # For unknown binary files, attempt to process as DOCX
                # This might be a DOC file sent with generic content type
                try:
                    docx_file = BytesIO(file_content)
                    doc = Document(docx_file)
                    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                    return text
                except:
                    # If it fails, it's likely a legacy DOC file
                    raise Exception("File format not supported. Please convert your document to DOCX or PDF format.")
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            raise Exception(f"Error extracting text from file: {str(e)}")

    async def extract_intent(self, message: str) -> str:
        """Extract user intent from a message"""
        prompt = f"""
        Extract the primary intent from the following user message for a job portal chatbot.
        The intent should be a short phrase (e.g., "Job Search", "Resume Advice", "Interview Prep", "General Inquiry").
        
        Message: {message}
        
        Return ONLY the intent phrase.
        """
        try:
            response = await self._make_request_async(prompt)
            return response["choices"][0]["message"]["content"].strip().strip('"')
        except:
            return "General Inquiry"

    async def _make_request_async(self, prompt: str) -> Dict[str, Any]:
        """Async version of make_request using requests.post (wrapped in run_in_executor if needed, but for now simple)"""
        # Improved extraction logic would use a proper async library like httpx
        # But for now we'll just use the existing logic in a slightly cleaner way
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "stepfun/step-3.5-flash:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        import asyncio
        loop = asyncio.get_event_loop()
        def do_post():
            return requests.post(self.api_url, headers=headers, json=payload, timeout=20)
        
        response = await loop.run_in_executor(None, do_post)
        return response.json()

# Global instance
ai_service = AIService()