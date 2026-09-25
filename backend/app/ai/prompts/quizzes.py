QUIZ_SYSTEM = """You create grounded multiple-choice learning quizzes from supplied chapter text.
Return one JSON object only. Use no markdown or commentary outside JSON.
Use only facts and concepts explicitly present in SOURCE. Never use outside knowledge.
Each question must be unambiguous, answerable from SOURCE, and have exactly one correct option.
Create plausible distractors, avoid trick questions, and avoid "all of the above".
Explanations must state why the correct answer follows from the supplied chapter."""


def quiz_prompt(title: str, source: str, difficulty: str, question_count: int) -> str:
    levels = {
        "EASY": "Focus on recall and basic understanding.",
        "MEDIUM": "Focus on comprehension and application of chapter concepts.",
        "HARD": "Focus on deeper reasoning and relationships between chapter concepts.",
    }
    return f"""Chapter: {title}
Difficulty: {difficulty}. {levels[difficulty]}
Create exactly {question_count} questions covering different parts of SOURCE.

Required JSON shape:
{{
  "title": "Chapter Review",
  "questions": [
    {{
      "question": "...",
      "question_type": "MULTIPLE_CHOICE",
      "options": [
        {{"text": "...", "is_correct": true}},
        {{"text": "...", "is_correct": false}}
      ],
      "explanation": "..."
    }}
  ]
}}

SOURCE
{source}"""
