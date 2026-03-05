# Changelog — PowerPro Electrical
**Account ID:** `account_004`  
**Version:** v1 → v2  
**Generated:** 2026-03-05T04:41:17.833178Z  
**Total Changes:** 9

---

## Changes

### `business_hours.days`
- **Change type:** Updated
- **Old value:** `Monday through Friday`
- **New value:** `Monday through Friday and Saturday 8 AM to 1 PM for emergencies`
- **Reason:** Updated during onboarding call

### `emergency_definition`
- **Change type:** Items added to list
- **Added:** ['Any electrical issue at a medical facility or care home']
- **Reason:** Added during onboarding update

### `non_emergency_routing_rules.action`
- **Change type:** Updated
- **Old value:** `Get their name, phone, address, and type of work, then transfer to scheduling line`
- **New value:** `Get their name, phone, address, and type of work, then transfer to scheduling line. If a caller mentions a referral from a specific company or contractor, capture the referral source in the message`
- **Reason:** Updated during onboarding call

### `services_supported`
- **Change type:** Items added to list
- **Added:** ['Commercial LED lighting retrofits']
- **Reason:** Added during onboarding update

### `services_supported`
- **Change type:** Items removed from list
- **Removed:** ['Smart home integration']
- **Reason:** Removed during onboarding update

### `special_routing_rules[0].action`
- **Change type:** Updated
- **Old value:** `Make a note and have the generator specialist call them back`
- **New value:** `Route to Sam Patel at 404-555-0155`
- **Reason:** Updated during onboarding call

### `special_routing_rules[0].contact_name`
- **Change type:** Updated
- **Old value:** `Generator specialist`
- **New value:** `Sam Patel`
- **Reason:** Updated during onboarding call

### `special_routing_rules[0].contact_phone`
- **Change type:** New field added
- **Value:** `404-555-0155`
- **Reason:** Updated during onboarding call

### `tone_instructions`
- **Change type:** New field added
- **Value:** `Acknowledge that electrical issues can feel scary or stressful for homeowners, be reassuring without making promises, and never use the phrase 'no problem'`
- **Reason:** Updated during onboarding call

---

## Summary

This changelog documents 9 change(s) applied during the onboarding call.
The v2 agent configuration reflects all updates confirmed by the client.
