import os
import csv
import json
import requests
from dotenv import load_dotenv

load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
if not PERPLEXITY_API_KEY:
    raise ValueError("PERPLEXITY_API_KEY not found — did you create a .env file?")

def load_first_contact(path="data/challenge_contacts.csv"):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return next(reader)

def build_system_prompt():
    return """You are an expert LP (limited partner) analyst for PaceZero Capital Partners, a sustainability-focused private credit firm raising Fund II.

PaceZero profile:
* Strategy: Private credit / direct lending (NOT equity, NOT venture)
* Focus: Climate mitigation, sustainability, impact (Agriculture & Ecosystems, Energy Transition, Health & Education)
* Status: Emerging manager, Fund II (~$3M–$20M deal sizes)
* Based in Toronto

CRITICAL DISTINCTION: An LP allocates capital INTO funds managed by external GPs. Organizations that originate loans, broker deals, manage assets for others, or provide advisory services are GPs or service providers — NOT LPs. Score them 1–2 on Sector Fit.
Exception: Some orgs both manage internal strategies AND allocate to external managers. If there is clear evidence of external fund allocations, treat as LP-eligible.

For FOUNDATIONS, ENDOWMENTS, and PENSIONS: focus on INVESTMENT OFFICE activity — fund commitments, alternatives allocations, ESG mandates — NOT charitable programs.

DIMENSION 1 — Sector & Mandate Fit (default 4 if unknown)
* 9–10: Confirmed LP + explicit private credit allocation + explicit ESG/impact mandate
* 7–8: Strong evidence of both, one implied
* 5–6: One box checked, the other unclear
* 3–4: Allocator but no ESG signal, or ESG present but no credit allocation
* 1–2: NOT an LP — GP, service provider, lender, broker

DIMENSION 3 — Halo & Strategic Value (default 3 if unknown)
* 9–10: Globally recognized sustainability/impact brand
* 7–8: Well-known in impact/climate or Canadian allocator circles
* 5–6: Regionally known or niche-recognized
* 3–4: Private, limited public profile
* 1–2: No public profile or potentially damaging association

DIMENSION 4 — Emerging Manager Fit (default 4 if unknown)
* 9–10: Documented emerging manager program
* 7–8: Org type commonly backs emerging managers + flexibility signal
* 5–6: No program but org type is flexible (SFO, MFO)
* 3–4: Org type prefers established managers
* 1–2: Explicit preference for large GPs, or is itself an emerging manager"""

def build_user_prompt(contact):
    return f"""Research and score this LP prospect. Return ONLY valid JSON, no markdown, no preamble.

Contact: {contact['Contact Name']}
Organization: {contact['Organization']}
Org Type: {contact['Org Type']}
Role: {contact['Role']}
Region: {contact['Region']}

Return this exact JSON structure:
{{
  "org": "string",
  "contact": "string",
  "enrichment_summary": "2-3 sentence summary of what you found",
  "aum_estimated": "string or null",
  "is_lp_eligible": true/false,
  "sector_fit": {{
    "score": number,
    "confidence": "high|medium|low",
    "reasoning": "1-2 sentences"
  }},
  "halo_value": {{
    "score": number,
    "confidence": "high|medium|low",
    "reasoning": "1-2 sentences"
  }},
  "emerging_fit": {{
    "score": number,
    "confidence": "high|medium|low",
    "reasoning": "1-2 sentences"
  }},
  "check_size_range": "string or null",
  "flags": ["array of any anomalies or concerns"]
}}"""

def call_perplexity(system_prompt, user_prompt):
    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sonar",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
    )
    response.raise_for_status()
    return response.json()

def parse_response(raw):
    content = raw["choices"][0]["message"]["content"]
    content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(content)

def enrich_contact(contact):
    raw = call_perplexity(build_system_prompt(), build_user_prompt(contact))
    result = parse_response(raw)
    usage = raw.get("usage", {})
    return result, usage

if __name__ == "__main__":
    contact = load_first_contact()
    print(f"Enriching: {contact['Contact Name']} @ {contact['Organization']}\n")
    result, usage = enrich_contact(contact)
    print(json.dumps(result, indent=2))
    print(f"\n--- Token Usage ---")
    print(f"Input:  {usage.get('prompt_tokens', '?')}")
    print(f"Output: {usage.get('completion_tokens', '?')}")