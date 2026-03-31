import json
import os
from typing import Any

import requests
from flask import Flask, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


class QuizGenerationError(Exception):
    """Erreur levée quand la génération du quiz échoue."""


def validate_form_data(theme: str, num_questions: str, difficulty: str) -> tuple[str, int, str]:
    """Valide et normalise les données reçues depuis le formulaire."""
    clean_theme = theme.strip()
    if not clean_theme:
        raise ValueError("Le thème ne peut pas être vide.")

    try:
        clean_count = int(num_questions)
    except ValueError as exc:
        raise ValueError("Le nombre de questions doit être un entier.") from exc

    if clean_count < 3 or clean_count > 10:
        raise ValueError("Le nombre de questions doit être compris entre 3 et 10.")

    allowed_difficulty = {"Facile", "Moyen", "Difficile"}
    if difficulty not in allowed_difficulty:
        raise ValueError("Le niveau de difficulté est invalide.")

    return clean_theme, clean_count, difficulty


def build_prompt(theme: str, num_questions: int, difficulty: str) -> str:
    """Construit le prompt envoyé au modèle LLM."""
    return f"""
Génère un quiz QCM sur le thème "{theme}".
Niveau: {difficulty}
Nombre de questions: {num_questions}

Contraintes strictes:
- Retourne uniquement du JSON valide, sans markdown et sans texte supplémentaire.
- Le JSON doit être un objet contenant la clé "questions".
- "questions" est une liste de {num_questions} objets.
- Chaque objet question doit contenir exactement:
  - "id": entier commençant à 1
  - "question": texte de la question
  - "options": objet avec exactement les clés "A", "B", "C", "D"
  - "answer": une seule lettre parmi "A", "B", "C", "D"

Exemple de structure:
{{
  "questions": [
    {{
      "id": 1,
      "question": "...",
      "options": {{
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
      }},
      "answer": "B"
    }}
  ]
}}
""".strip()


def extract_json_content(raw_content: str) -> dict[str, Any]:
    """Nettoie une réponse potentiellement entourée de balises markdown et la parse."""
    clean = raw_content.strip()
    if clean.startswith("```"):
        clean = clean.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise QuizGenerationError("La réponse de l'IA est mal formatée.") from exc

    if "questions" not in parsed or not isinstance(parsed["questions"], list):
        raise QuizGenerationError("Format JSON inattendu reçu depuis l'API.")

    return parsed


def generate_quiz_with_groq(theme: str, num_questions: int, difficulty: str) -> list[dict[str, Any]]:
    """Appelle l'API Groq et renvoie la liste des questions."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise QuizGenerationError(
            "Clé API Groq manquante. Définissez la variable d'environnement GROQ_API_KEY."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Tu es un assistant qui génère des quiz académiques précis en JSON strict.",
            },
            {"role": "user", "content": build_prompt(theme, num_questions, difficulty)},
        ],
        "temperature": 0.4,
        "max_tokens": 2000,
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = extract_json_content(content)
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code in {401, 403}:
            raise QuizGenerationError("Clé API Groq invalide ou non autorisée.") from exc
        raise QuizGenerationError("Erreur HTTP lors de l'appel à Groq.") from exc
    except requests.exceptions.RequestException as exc:
        raise QuizGenerationError("Problème réseau lors de l'appel à Groq.") from exc
    except (KeyError, TypeError) as exc:
        raise QuizGenerationError("Réponse inattendue reçue depuis l'API Groq.") from exc

    questions = parsed["questions"]
    if len(questions) != num_questions:
        raise QuizGenerationError(
            f"Le modèle a retourné {len(questions)} questions au lieu de {num_questions}."
        )

    for q in questions:
        if not isinstance(q, dict):
            raise QuizGenerationError("Une question reçue n'est pas un objet JSON valide.")

        if not {"id", "question", "options", "answer"}.issubset(q.keys()):
            raise QuizGenerationError("Une question ne contient pas toutes les clés attendues.")

        options = q["options"]
        if not isinstance(options, dict) or set(options.keys()) != {"A", "B", "C", "D"}:
            raise QuizGenerationError("Les options d'une question sont invalides.")

        if q["answer"] not in {"A", "B", "C", "D"}:
            raise QuizGenerationError("La bonne réponse d'une question est invalide.")

    return questions


@app.route("/", methods=["GET"])
def index() -> str:
    """Affiche la page d'accueil avec le formulaire de génération."""
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate() -> str:
    """Traite le formulaire puis affiche le quiz généré."""
    theme = request.form.get("theme", "")
    num_questions = request.form.get("num_questions", "")
    difficulty = request.form.get("difficulty", "")

    try:
        clean_theme, clean_count, clean_difficulty = validate_form_data(theme, num_questions, difficulty)
        questions = generate_quiz_with_groq(clean_theme, clean_count, clean_difficulty)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    except QuizGenerationError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))

    session["quiz_questions"] = questions
    session["quiz_meta"] = {
        "theme": clean_theme,
        "difficulty": clean_difficulty,
    }
    return render_template("quiz.html", questions=questions, meta=session["quiz_meta"])


@app.route("/submit", methods=["POST"])
def submit() -> str:
    """Corrige les réponses soumises et affiche le score."""
    questions = session.get("quiz_questions")
    meta = session.get("quiz_meta", {})
    if not questions:
        flash("Aucun quiz actif. Veuillez générer un quiz d'abord.", "error")
        return redirect(url_for("index"))

    details = []
    score = 0

    for question in questions:
        qid = str(question["id"])
        user_answer = request.form.get(f"question_{qid}")
        correct_answer = question["answer"]
        is_correct = user_answer == correct_answer
        if is_correct:
            score += 1

        details.append(
            {
                "question": question["question"],
                "options": question["options"],
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
            }
        )

    session.pop("quiz_questions", None)

    return render_template(
        "result.html",
        score=score,
        total=len(questions),
        details=details,
        meta=meta,
    )


if __name__ == "__main__":
    app.run(debug=True)
