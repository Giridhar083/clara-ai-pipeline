"""
extractor.py
------------
Extracts structured Account Memo JSON from a call transcript.
Uses Groq free-tier API (llama-3.3-70b-versatile).

Zero-cost: Groq free tier does not require payment.
Sign up at https://console.groq.com to get a free API key.
"""

import os
import json
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "llama-3.3-70b-versatile"  # Free on Groq

EXTRACTION_SYSTEM_PROMPT = """You are an expert at extracting structured business data from call transcripts for AI voice agent configuration.

Your job is to read a call transcript and extract ONLY the information that was explicitly stated. 
NEVER invent or infer data that was not mentioned. If something is unknown, use null.
Flag genuinely missing but important fields under questions_or_unknowns.

Return ONLY a valid JSON object. No markdown, no explanation, no code fences."""

EXTRACTION_USER_PROMPT = """Extract all available information from this call transcript and return a JSON object with exactly these fields:

{{
  "account_id": "{account_id}",
  "company_name": "<string>",
  "business_hours": {{
    "days": "<e.g. Monday-Friday>",
    "start": "<e.g. 8:00 AM>",
    "end": "<e.g. 5:00 PM>",
    "timezone": "<e.g. America/Chicago>",
    "exceptions": "<e.g. Saturday 9AM-2PM or null>"
  }},
  "office_address": "<full address or null>",
  "services_supported": ["<service1>", "<service2>"],
  "emergency_definition": ["<trigger1>", "<trigger2>"],
  "emergency_routing_rules": {{
    "primary_contact_name": "<name or null>",
    "primary_contact_phone": "<phone or null>",
    "secondary_contact_name": "<name or null>",
    "secondary_contact_phone": "<phone or null>",
    "rings_before_fallback": <number or null>,
    "fallback_instruction": "<what to tell caller if no answer>"
  }},
  "non_emergency_routing_rules": {{
    "action": "<e.g. take message, schedule callback>",
    "callback_window": "<e.g. within 1 hour>",
    "message_destination": "<where messages go>"
  }},
  "call_transfer_rules": {{
    "transfer_number": "<main transfer number>",
    "transfer_contact_name": "<person or team name or null>",
    "timeout_rings": <number or null>,
    "message_if_transfer_fails": "<what to say>",
    "callback_window_if_fails": "<e.g. within 45 minutes or null>"
  }},
  "special_routing_rules": [
    {{
      "trigger": "<what triggers this>",
      "action": "<what to do>",
      "contact_name": "<name or null>",
      "contact_phone": "<phone or null>"
    }}
  ],
  "integration_constraints": ["<constraint1>"],
  "pricing_instructions": "<what to say about pricing or null>",
  "after_hours_flow_summary": "<brief description>",
  "office_hours_flow_summary": "<brief description>",
  "tone_instructions": "<any tone/style guidance given or null>",
  "questions_or_unknowns": ["<genuinely missing field or question>"],
  "notes": "<anything important that doesn't fit elsewhere>"
}}

TRANSCRIPT:
{transcript}

Return ONLY the JSON object."""


def extract_from_transcript(transcript: str, account_id: str) -> dict:
    """
    Extract structured Account Memo from transcript via Groq LLM.
    Returns validated memo dict.
    """
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com"
        )

    prompt = EXTRACTION_USER_PROMPT.format(
        account_id=account_id,
        transcript=transcript.strip()
    )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 2500
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    logger.info(f"Calling Groq API for account {account_id}...")
    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=90)
    response.raise_for_status()

    raw = response.json()["choices"][0]["message"]["content"].strip()

    # Strip any accidental markdown code fences
    raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        memo = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"Raw LLM output: {raw}")
        raise ValueError(f"LLM returned invalid JSON for account {account_id}: {e}")

    memo["account_id"] = account_id
    return validate_memo(memo)


def apply_patch(v1_memo: dict, onboarding_transcript: str) -> dict:
    """
    Extract updates from onboarding transcript and patch into existing memo.
    Returns updated (v2) memo.
    """
    if not GROQ_API_KEY:
        raise EnvironmentError("GROQ_API_KEY is not set.")

    patch_prompt = f"""You are updating an existing AI voice agent configuration based on a new onboarding call.

Here is the EXISTING configuration (v1):
{json.dumps(v1_memo, indent=2)}

Here is the ONBOARDING CALL TRANSCRIPT with updates:
{onboarding_transcript.strip()}

Instructions:
1. Apply ALL changes mentioned in the onboarding transcript to the existing configuration.
2. Keep all fields that were NOT changed in the onboarding call exactly as they are.
3. Return the complete updated JSON object (not just the changes).
4. Use null for any field that was explicitly removed or cleared.
5. Do NOT invent any new information not mentioned in the onboarding call.

Return ONLY the updated JSON object. No markdown, no explanation."""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": patch_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 2500
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    account_id = v1_memo.get("account_id", "unknown")
    logger.info(f"Calling Groq API for onboarding patch - account {account_id}...")

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=90)
    response.raise_for_status()

    raw = response.json()["choices"][0]["message"]["content"].strip()
    raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        v2_memo = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON during patch for {account_id}: {e}")

    v2_memo["account_id"] = account_id
    return validate_memo(v2_memo)


def validate_memo(memo: dict) -> dict:
    """Ensure all required fields exist; fill missing with null."""
    required_top_level = [
        "account_id", "company_name", "business_hours", "office_address",
        "services_supported", "emergency_definition", "emergency_routing_rules",
        "non_emergency_routing_rules", "call_transfer_rules", "special_routing_rules",
        "integration_constraints", "pricing_instructions", "after_hours_flow_summary",
        "office_hours_flow_summary", "tone_instructions", "questions_or_unknowns", "notes"
    ]

    for field in required_top_level:
        if field not in memo:
            memo[field] = None

    # Ensure list fields are lists
    for list_field in ["services_supported", "emergency_definition",
                       "integration_constraints", "questions_or_unknowns",
                       "special_routing_rules"]:
        if not isinstance(memo.get(list_field), list):
            memo[list_field] = [] if memo.get(list_field) is None else [memo[list_field]]

    return memo
