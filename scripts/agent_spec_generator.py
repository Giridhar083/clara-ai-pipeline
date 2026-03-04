"""
agent_spec_generator.py
-----------------------
Takes an Account Memo JSON and generates a complete Retell Agent Spec.
Includes a full system prompt following required conversation hygiene.
No LLM call needed here - fully template-driven.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def generate_agent_spec(memo: dict, version: str = "v1") -> dict:
    """
    Generate a Retell-compatible agent spec from an Account Memo.
    
    Args:
        memo: Validated Account Memo dict
        version: "v1" (from demo) or "v2" (after onboarding)
    
    Returns:
        Complete agent spec dict
    """
    company = memo.get("company_name") or "the company"
    account_id = memo.get("account_id", "unknown")

    biz_hours = memo.get("business_hours") or {}
    days = biz_hours.get("days", "Monday through Friday")
    start = biz_hours.get("start", "8:00 AM")
    end = biz_hours.get("end", "5:00 PM")
    timezone = biz_hours.get("timezone", "local time")
    tz_abbr = _timezone_abbr(timezone)
    exceptions = biz_hours.get("exceptions")

    address = memo.get("office_address") or "our office"
    services = memo.get("services_supported") or []
    services_str = ", ".join(services) if services else "a range of services"

    emrg_def = memo.get("emergency_definition") or []
    emrg_def_str = "; ".join(emrg_def) if emrg_def else "urgent situations requiring immediate attention"

    emrg_routing = memo.get("emergency_routing_rules") or {}
    primary_name = emrg_routing.get("primary_contact_name", "our on-call technician")
    primary_phone = emrg_routing.get("primary_contact_phone", "")
    secondary_name = emrg_routing.get("secondary_contact_name")
    secondary_phone = emrg_routing.get("secondary_contact_phone")
    rings = emrg_routing.get("rings_before_fallback", 3)
    fallback_msg = emrg_routing.get("fallback_instruction",
                                     "let the caller know we will return their call as quickly as possible")

    transfer = memo.get("call_transfer_rules") or {}
    transfer_num = transfer.get("transfer_number", "")
    transfer_name = transfer.get("transfer_contact_name", "our team")
    transfer_fail_msg = transfer.get("message_if_transfer_fails",
                                     "I was unable to connect you, but a team member will call you back shortly")
    callback_window = transfer.get("callback_window_if_fails", "as soon as possible")

    non_emrg = memo.get("non_emergency_routing_rules") or {}
    non_emrg_action = non_emrg.get("action", "take a detailed message")
    non_emrg_window = non_emrg.get("callback_window", "as soon as possible during business hours")

    special_rules = memo.get("special_routing_rules") or []

    constraints = memo.get("integration_constraints") or []
    pricing_instr = memo.get("pricing_instructions") or (
        "do not quote specific prices; let callers know pricing varies and a team member will provide an exact quote"
    )

    tone = memo.get("tone_instructions") or "professional, friendly, and helpful"

    hours_summary = _build_hours_summary(days, start, end, tz_abbr, exceptions)
    special_routing_text = _build_special_routing_text(special_rules)
    secondary_transfer_text = _build_secondary_transfer(secondary_name, secondary_phone)

    system_prompt = _build_system_prompt(
        company=company,
        hours_summary=hours_summary,
        services_str=services_str,
        address=address,
        emrg_def_str=emrg_def_str,
        primary_name=primary_name,
        primary_phone=primary_phone,
        secondary_transfer_text=secondary_transfer_text,
        rings=rings,
        fallback_msg=fallback_msg,
        transfer_num=transfer_num,
        transfer_name=transfer_name,
        transfer_fail_msg=transfer_fail_msg,
        callback_window=callback_window,
        non_emrg_action=non_emrg_action,
        non_emrg_window=non_emrg_window,
        special_routing_text=special_routing_text,
        pricing_instr=pricing_instr,
        tone=tone
    )

    agent_spec = {
        "agent_name": f"{company} - Clara AI Agent",
        "account_id": account_id,
        "version": version,
        "voice_style": {
            "provider": "elevenlabs",
            "voice_id": "rachel",
            "style": "friendly and professional",
            "speed": 1.0,
            "custom_note": tone
        },
        "system_prompt": system_prompt,
        "key_variables": {
            "company_name": company,
            "timezone": timezone,
            "timezone_abbr": tz_abbr,
            "business_hours_days": days,
            "business_hours_start": start,
            "business_hours_end": end,
            "business_hours_exceptions": exceptions,
            "office_address": address,
            "primary_emergency_contact_name": primary_name,
            "primary_emergency_contact_phone": primary_phone,
            "secondary_emergency_contact_name": secondary_name,
            "secondary_emergency_contact_phone": secondary_phone,
            "transfer_number": transfer_num,
            "transfer_contact_name": transfer_name
        },
        "tool_invocation_placeholders": {
            "note": "Do NOT mention tool calls, function names, or system actions to callers.",
            "transfer_call": {
                "trigger": "caller needs to reach dispatch or a specific team member",
                "action": "transfer_call",
                "number": transfer_num,
                "caller_message": f"One moment while I connect you with {transfer_name}."
            },
            "send_sms": {
                "trigger": "caller needs a callback or agent takes a message",
                "action": "send_sms_to_team",
                "note": "Send message to team without disclosing this to caller"
            }
        },
        "call_transfer_protocol": {
            "primary_transfer_number": transfer_num,
            "contact_name": transfer_name,
            "timeout_rings": transfer.get("timeout_rings", 4),
            "on_transfer_fail": transfer_fail_msg,
            "callback_window_if_fails": callback_window,
            "what_to_collect_before_transfer": [
                "caller full name",
                "callback phone number",
                "service address",
                "brief description of issue or request"
            ]
        },
        "fallback_protocol": {
            "trigger": "transfer fails after timeout_rings",
            "action": [
                "Apologize for the inconvenience",
                f"Say: '{transfer_fail_msg}'",
                f"Confirm their name and number",
                f"Assure callback within {callback_window}",
                "Ask if there is anything else before closing"
            ]
        },
        "emergency_protocol": {
            "definition": emrg_def,
            "qualifying_questions": [
                "Is the issue happening right now?",
                "Is there any safety risk?"
            ],
            "primary_transfer": {
                "name": primary_name,
                "phone": primary_phone,
                "rings_before_fallback": rings
            },
            "secondary_transfer": {
                "name": secondary_name,
                "phone": secondary_phone
            } if secondary_phone else None,
            "if_no_answer": fallback_msg
        },
        "conversation_hygiene": {
            "max_info_to_collect": ["name", "callback number", "address", "issue description"],
            "never_say": [
                "function call", "tool", "transfer function",
                "system", "I'm an AI", "I'm a bot"
            ],
            "pricing_policy": pricing_instr,
            "always_end_with": "Is there anything else I can help you with before I let you go?"
        }
    }

    return agent_spec


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _timezone_abbr(timezone: str) -> str:
    tz_map = {
        "America/Chicago": "CT",
        "America/New_York": "ET",
        "America/Denver": "MT",
        "America/Los_Angeles": "PT",
        "America/Phoenix": "MST",
        "America/Anchorage": "AKT",
        "Pacific/Honolulu": "HT"
    }
    return tz_map.get(timezone, timezone)


def _build_hours_summary(days, start, end, tz_abbr, exceptions) -> str:
    base = f"{days} from {start} to {end} {tz_abbr}"
    if exceptions:
        base += f", with {exceptions}"
    return base


def _build_special_routing_text(special_rules: list) -> str:
    if not special_rules:
        return ""
    lines = ["\n\nSPECIAL ROUTING RULES:"]
    for rule in special_rules:
        trigger = rule.get("trigger", "")
        action = rule.get("action", "")
        name = rule.get("contact_name", "")
        phone = rule.get("contact_phone", "")
        entry = f"- If caller mentions {trigger}: {action}"
        if name:
            entry += f" (Contact: {name}"
            if phone:
                entry += f" at {phone}"
            entry += ")"
        lines.append(entry)
    return "\n".join(lines)


def _build_secondary_transfer(name, phone) -> str:
    if name and phone:
        return f"If {name} does not answer, try {phone}."
    return ""


def _build_system_prompt(
    company, hours_summary, services_str, address,
    emrg_def_str, primary_name, primary_phone,
    secondary_transfer_text, rings, fallback_msg,
    transfer_num, transfer_name, transfer_fail_msg,
    callback_window, non_emrg_action, non_emrg_window,
    special_routing_text, pricing_instr, tone
) -> str:
    return f"""# {company} AI Receptionist — System Prompt

## IDENTITY
You are a professional, friendly receptionist for {company}. You answer calls on their behalf, help callers with their needs, and connect them with the right team. You sound warm and natural — not robotic or scripted.

## TONE
{tone}

## BUSINESS INFORMATION
- Company: {company}
- Address: {address}
- Services offered: {services_str}
- Business Hours: {hours_summary}

## PRICING POLICY
{pricing_instr}

---

## DURING BUSINESS HOURS — CALL FLOW

**Step 1 — Greeting**
Answer warmly: "Thank you for calling {company}, this is [your name]. How can I help you today?"

**Step 2 — Understand the purpose**
Listen to the caller's reason for calling. Acknowledge it briefly and empathetically.

**Step 3 — Collect required information (only what is needed)**
Collect the following — do not ask for more than this:
- Caller's full name
- Best callback phone number
- Service address
- Brief description of the issue or request

Do not ask multiple questions at once. Collect information naturally in conversation.

**Step 4 — Route or Transfer**
Once you have the required information, tell the caller: "Let me connect you with {transfer_name} right now."
Initiate the call transfer to {transfer_num}.

**Step 5 — If Transfer Fails**
If the transfer does not connect after waiting:
Say: "{transfer_fail_msg}. I've noted your information and someone will reach you within {callback_window}."
Confirm the caller's name and phone number before closing.

**Step 6 — Confirm next steps**
Before ending, confirm: "I have your name as [name] and your number as [number]. Someone from our team will be in touch within {callback_window}."

**Step 7 — Anything else**
Always ask: "Is there anything else I can help you with before I let you go?"

**Step 8 — Close**
Close warmly: "Thank you for calling {company}. Have a great day!"

---

## AFTER HOURS — CALL FLOW

**Step 1 — Greeting**
Answer warmly: "Thank you for calling {company}. Our office is currently closed. I'm here to help — what's going on?"

**Step 2 — Understand the situation**
Listen to the caller's reason for calling. Ask gently: "Can you tell me a bit more about what's happening?"

**Step 3 — Determine if it is an emergency**
Emergencies include: {emrg_def_str}

Ask: "Is this something that needs immediate attention tonight, or can it wait until we open?"

**Step 4a — IF EMERGENCY:**

Collect immediately:
- Full name
- Callback phone number  
- Service address
- Brief description of the emergency

Say: "I understand, let me get you connected with our on-call team right now. Please stay on the line."

Initiate transfer to {primary_name} at {primary_phone}.
{secondary_transfer_text}
Wait up to {rings} rings before falling back.

**If emergency transfer fails:**
Say: "I was unable to connect you directly, but I am alerting our on-call team right now. {fallback_msg}. Is it safe where you are right now?"
Assure them: "Our technician will reach you as quickly as possible."

**Step 4b — IF NOT AN EMERGENCY:**
Say: "I understand. Since this isn't an emergency, I want to make sure our team can take care of you properly during business hours. Let me take your information."
Collect name, phone number, and brief description.
{non_emrg_action}. Confirm: "Our team will be in touch {non_emrg_window}."

**Step 5 — Anything else**
Ask: "Is there anything else I can help you with tonight?"

**Step 6 — Close**
Close warmly: "Thank you for calling {company}. Take care and we'll be in touch soon."

---
{special_routing_text}
---

## RULES — ALWAYS FOLLOW

1. Never mention function calls, tool names, or any system actions to callers.
2. Never quote specific prices or commit to specific appointment times unless you have confirmed availability.
3. Never say "I understand your frustration" or similar scripted empathy phrases that sound fake.
4. Always sound like a knowledgeable human receptionist.
5. Only collect: name, phone number, address, and issue. Do not ask unnecessary questions.
6. If you do not know the answer to a specific question, say "That's a great question — let me make a note so our team can address it when they call you back."
7. Always confirm collected information before ending the call.
8. Always end with "Is there anything else I can help you with?"
"""
