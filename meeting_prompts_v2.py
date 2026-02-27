"""
LLM Prompt Templates for Meeting Analysis v2.0
Provides structured prompts for refinement (stories) vs general (action items) meetings
"""

SYSTEM_PROMPT = """
You are a structured assistant that turns meeting transcripts into JSON
for a product team.

You MUST:
- Obey the JSON schema exactly as specified.
- Never include commentary or explanations, only JSON.
- Leave fields null or empty arrays if the information is not clearly present.
- Do not invent owners, due dates, or acceptance criteria that are not implied in the transcript.

You will be told what kind of meeting this is via `meeting_type`.
Use that to decide whether to generate user stories or action items.
""".strip()


def build_refinement_user_prompt(meeting_title: str, transcript: str) -> str:
    """Build prompt for refinement meetings -> user stories"""
    return f"""
meeting_type: "refinement"

Project context:
- This meeting is primarily for backlog refinement and user story creation.

Inputs:
- Meeting title: "{meeting_title}"
- Meeting transcript (may be partial, automatic, or messy):
\"\"\" 
{transcript}
\"\"\"

Task:
1. Identify the main backlog items discussed that are suitable as user stories.
2. For each, generate:
   - summary: a concise, Jira-ready story title.
   - description: 2–6 sentences capturing context, problem, and any constraints.
   - acceptance_criteria:
       * A list of concrete, testable conditions.
       * Use either Given/When/Then or clear bullet points.
   - estimate_points:
       * If specific numbers were mentioned (e.g. "3 points", "5 SP"), use that integer.
       * Otherwise use null.
   - assignees:
       * Extract any names that were clearly assigned to this story; otherwise [].
   - labels:
       * ALWAYS include "AIGen-ReviewRqd" as the first label for all AI-generated stories.
       * Add additional tags if mentioned (e.g. "frontend", "backend", "spike").

3. Ignore generic meeting admin like "can you share this deck" unless clearly part of the story.

Output:
Return ONLY valid JSON in this exact shape:

{{
  "meeting_type": "refinement",
  "stories": [
    {{
      "summary": "string",
      "description": "string",
      "acceptance_criteria": ["string"],
      "estimate_points": null,
      "assignees": [],
      "labels": []
    }}
  ]
}}

If no clear stories are present, return:

{{
  "meeting_type": "refinement",
  "stories": []
}}
""".strip()


def build_general_user_prompt(meeting_title: str, transcript: str) -> str:
    """Build prompt for general meetings -> action items"""
    return f"""
meeting_type: "general"

Project context:
- This is a general meeting. The primary output is follow-up action items, not user stories.

Inputs:
- Meeting title: "{meeting_title}"
- Meeting transcript (may be partial, automatic, or messy):
\"\"\" 
{transcript}
\"\"\"

Task:
1. Identify concrete action items: things someone has agreed to do after the meeting.
2. For each action item, generate:
   - title: short imperative phrase (e.g. "Schedule follow-up with security team").
   - description: 1–3 sentences of context if needed, else "".
   - owner:
       * Person explicitly asked or volunteering to do it (name or email as it appears).
       * If unclear, use null.
   - due_date_hint:
       * If an explicit date or timeframe was given, convert to an ISO date if possible,
         or use the phrase; otherwise null.
   - related_decision:
       * If this action arises directly from a specific decision, briefly describe that decision.
       * Otherwise null.

3. Ignore vague comments that are not clearly actions.

Output:
Return ONLY valid JSON in this exact shape:

{{
  "meeting_type": "general",
  "actions": [
    {{
      "title": "string",
      "description": "string",
      "owner": null,
      "due_date_hint": null,
      "related_decision": null
    }}
  ]
}}

If no clear action items are present, return:

{{
  "meeting_type": "general",
  "actions": []
}}
""".strip()


def build_mixed_user_prompt(meeting_title: str, transcript: str) -> str:
    """Build prompt for mixed meetings -> both stories and action items"""
    return f"""
meeting_type: "mixed"

Project context:
- This meeting has both backlog refinement elements AND general action items.

Inputs:
- Meeting title: "{meeting_title}"
- Meeting transcript (may be partial, automatic, or messy):
\"\"\" 
{transcript}
\"\"\"

Task:
1. Identify BOTH user stories AND action items from this meeting.
2. For stories (same rules as refinement meetings):
   - summary, description, acceptance_criteria, estimate_points, assignees, labels
3. For actions (same rules as general meetings):
   - title, description, owner, due_date_hint, related_decision

Output:
Return ONLY valid JSON in this exact shape:

{{
  "meeting_type": "mixed",
  "stories": [
    {{
      "summary": "string",
      "description": "string",
      "acceptance_criteria": ["string"],
      "estimate_points": null,
      "assignees": [],
      "labels": []
    }}
  ],
  "actions": [
    {{
      "title": "string",
      "description": "string",
      "owner": null,
      "due_date_hint": null,
      "related_decision": null
    }}
  ]
}}

If no stories or actions are found, return empty arrays for each.
""".strip()
