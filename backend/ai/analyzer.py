"""
AI analyzer — handles communication with Gemini API.

KEY CONCEPT: Structured Output
-------------------------------
LLMs usually output raw text. By passing our Pydantic `EmailAnalysisResult` schema 
to `response_schema`, we FORCE Gemini to output perfectly formatted JSON matching 
our schema. This means no manual regex parsing or JSON fixing!

KEY CONCEPT: System Instructions
--------------------------------
The `system_instruction` is the foundational rulebook for the AI. We use it to 
enforce the strict "no hallucination" rules requested by the user.

KEY CONCEPT: Concurrency
-------------------------
Calling Gemini for 10 emails one by one would take 30+ seconds. We use `asyncio.gather` 
to analyze all 10 emails simultaneously in parallel, reducing total time to ~3-5 seconds.
"""

import asyncio
from google import genai
from google.genai import types
from fastapi import HTTPException, status

from backend.config import settings
from backend.schemas import EmailCardResponse, EmailAnalysisResult

async def analyze_emails(emails: list[EmailCardResponse]) -> list[EmailCardResponse]:
    """
    Takes a list of fetched emails, sends them to Gemini for structured analysis,
    and attaches the result to the `analysis` field of each email.
    """
    if not settings.GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not set. Skipping analysis.")
        return emails

    # Initialize the Gemini client
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    system_instruction = """
    You are an AI assistant for university students analyzing their inbox.
    Read the provided email and extract structured information.
    
    CRITICAL RULES:
    1. NEVER invent a deadline, URL, requirement, sender, event, or action.
    2. If a deadline is not EXPLICITLY stated, return an empty array for deadlines.
    3. If no action is explicitly required, set action_required to false and action_items to [].
    4. Distinguish facts from interpretation in 'what_this_means'.
    5. Properly categorize security, social, newsletters, and promotional emails. Do not automatically mark them as high priority unless they require urgent action.
    6. Ensure the date, subject, and sender fields reflect the provided email headers.
    """

    async def analyze_single(email: EmailCardResponse) -> bool:
        # Skip if there's no body to analyze
        if not email.full_body:
            return False
        
        # Build the prompt
        prompt = (
            f"Sender: {email.sender}\n"
            f"Subject: {email.subject}\n"
            f"Date: {email.received_at}\n\n"
            f"Body:\n{email.full_body}"
        )
        
        try:
            # Call Gemini using the async client wrapper
            # We enforce JSON output matching our Pydantic schema
            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EmailAnalysisResult,
                    system_instruction=system_instruction,
                    temperature=0.1, # Low temperature makes it factual and deterministic
                )
            )
            
            # Parse the JSON response back into our Pydantic model
            email.analysis = EmailAnalysisResult.model_validate_json(response.text)
            return True
            
        except Exception as e:
            print(f"Error analyzing email {email.gmail_message_id}: {str(e)}")
            # We will return the exception so we can inspect it if everything fails
            return e

    # Only analyze the first 10 emails for the prototype batch
    batch_to_analyze = emails[:10]
    
    # Run all API calls in parallel
    results = await asyncio.gather(*(analyze_single(email) for email in batch_to_analyze))
    
    # Check if we attempted to analyze at least one email, but ALL of them failed
    attempted = len([r for r in results if r is not False])
    successes = len([r for r in results if r is True])
    
    if attempted > 0 and successes == 0:
        # Get the first actual exception to return to the user
        first_error = next((r for r in results if isinstance(r, Exception)), "Unknown error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini AI analysis failed for all emails. Error: {str(first_error)}"
        )
    
    return emails
