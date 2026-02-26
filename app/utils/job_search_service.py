import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class JobSearchService:
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.jobdata_api_key = os.getenv("JOBDATA_API_KEY")
        self.jobdata_url = os.getenv("JOBDATA_API_URL", "https://jobdataapi.com/api/jobs/")
        
    async def search_direct_jobs(self, query: str, location: str = "", job_type: str = "") -> List[Dict[str, Any]]:
        """
        Search for jobs.

        1. Prefer real jobs from JobDataAPI (via JOBDATA_API_KEY).
        2. Fallback to OpenRouter AI JSON generation if API is unavailable.
        """
        # First try real jobs API if configured
        if self.jobdata_api_key:
            try:
                real_jobs = await self._search_jobs_jobdata(query=query, location=location, job_type=job_type)
                if isinstance(real_jobs, list) and real_jobs:
                    return real_jobs
            except Exception as e:
                print(f"JobDataAPI search error: {e}")
                # continue to OpenRouter fallback

        # Fallback: use OpenRouter AI model to synthesize structured jobs
        try:
            # Create a simplified prompt for speed
            search_prompt = (
                "JSON ONLY: "
                "[{\"title\":\"Sales Manager\",\"company\":\"Example Corp\",\"location\":\"Delhi, India\","
                "\"salary\":\"₹10-15 LPA\",\"description\":\"Short description of the role.\","
                "\"skills\":[\"Sales\",\"B2B\",\"Team Management\"],"
                "\"experience\":\"5+ years\",\"work_mode\":\"On-site\","
                "\"apply_url\":\"https://example.com/jobs/123\","
                "\"posted_date\":\"2026-02-26\",\"employer_phone\":\"\",\"employer_email\":\"\"}]"
                f"\nSearch: {query} in {location}"
            )

            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aijobportal.com",
                "X-Title": "AI Job Portal"
            }
            
            payload = {
                "model": "google/gemma-3-4b-it:free",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a job search assistant. "
                            "Return ONLY a valid JSON array of jobs matching the query. No preamble."
                        ),
                    },
                    {"role": "user", "content": search_prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 1000,
            }
            
            response = requests.post(self.openrouter_url, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Parse the JSON response
                try:
                    import json
                    import re
                    
                    # More robust JSON extraction
                    clean_content = content.strip()
                    if "```" in clean_content:
                        json_match = re.search(r'\[\s*\{.*\}\s*\]', clean_content, re.DOTALL)
                        if json_match:
                            clean_content = json_match.group(0)
                        else:
                            # Try to strip markdown fences
                            clean_content = re.sub(r'```json\s*|```\s*', '', clean_content).strip()
                    
                    jobs = json.loads(clean_content)
                    return jobs if isinstance(jobs, list) else []
                except Exception as e:
                    print(f"Error parsing job search response: {e}")
                    # Return a specific error string that get_real_job_details can handle
                    return [{"error": "parsing_failed", "raw": content[:100]}]
            else:
                print(f"OpenRouter API error: {response.status_code} - {response.text}")
                return [{"error": f"api_error_{response.status_code}"}]
                
        except Exception as e:
            print(f"Error in job search: {e}")
            return self._get_sample_jobs(query, location, job_type)

    async def _search_jobs_jobdata(self, query: str, location: str = "", job_type: str = "") -> List[Dict[str, Any]]:
        """
        Search real jobs using JobDataAPI.
        Maps the external API fields into the internal job structure expected by the frontend.
        """
        if not self.jobdata_api_key:
            return []

        try:
            params = {
                "title": query or "Sales Manager",
            }
            if location:
                params["location"] = location

            # Basic page size to avoid huge payloads
            params["page_size"] = 10

            headers = {
                "Authorization": f"Api-Key {self.jobdata_api_key}",
            }

            response = requests.get(self.jobdata_url, headers=headers, params=params, timeout=15)

            if response.status_code != 200:
                print(f"JobDataAPI error: {response.status_code} - {response.text}")
                return []

            data = response.json() or {}
            results = data.get("results", [])
            jobs: List[Dict[str, Any]] = []

            for item in results:
                company_info = item.get("company") or {}
                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                salary_currency = item.get("salary_currency") or ""

                salary_str = ""
                if salary_min or salary_max:
                    if salary_min and salary_max:
                        salary_str = f"{salary_min} - {salary_max} {salary_currency}".strip()
                    else:
                        salary_value = salary_min or salary_max
                        salary_str = f"{salary_value} {salary_currency}".strip()

                job = {
                    "title": item.get("title") or "",
                    "company": company_info.get("name") or "",
                    "location": item.get("location") or "",
                    "salary": salary_str,
                    "description": item.get("description") or "",
                    "skills": [],
                    "experience": item.get("experience_level") or "",
                    "work_mode": "Remote" if item.get("has_remote") else "",
                    "apply_url": item.get("application_url") or company_info.get("website_url") or "",
                    "posted_date": item.get("published") or "",
                    "employer_phone": "",
                    "employer_email": "",
                }
                jobs.append(job)

            return jobs
        except Exception as e:
            print(f"Error calling JobDataAPI: {e}")
            return []
            
    async def search_real_jobs(self, query: str, location: str = "", job_type: str = "") -> List[Dict[str, Any]]:
        """Deprecated, use search_direct_jobs"""
        return await self.search_direct_jobs(query, location, job_type)
    
    def _get_sample_jobs(self, query: str, location: str, job_type: str) -> List[Dict[str, Any]]:
        """
        Mock data purged.
        """
        return []

# Global instance
job_search_service = JobSearchService()