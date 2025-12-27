import os

from cs50 import SQL
import json
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from openai import OpenAI, RateLimitError

from helpers import apology, login_required

app = Flask(__name__)

# Don't worry about the key I'll delete it on December 31st
OPENAI_API_KEY="openAIkey"

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///flashcards.db")
client = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_SETTINGS = {
    "system_role": {
        "role": "system",
        "content": "You are a helpful study assistant. Generate flashcards from study material. Return ONLY a JSON array of objects with 'front' and 'back' fields. No other text. Intentionally introduce subtle mistakes in a small, random subset of cards (e.g., incorrect dates, swapped terms, or slightly wrong definitions) so the student can identify and correct them."
    },
    "model": "gpt-4o-mini",
    "prompt": "Each flashcard should have a question/term on the front and answer/definition on the back",
    "max_tokens": 2000,
    "max_retries": 3,
    "retry_delay": 2
}


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "GET":
        decks = db.execute("SELECT id, title FROM decks")
        return render_template("create.html", decks=decks)


    title = request.form.get("title")
    number_of_cards = request.form.get("num_cards")
    content = request.form.get("content")
    selected_deck = request.form.get("deck")
    description = request.form.get("description")

    if not title and not selected_deck:
        return apology("You either need to update an existing deck or create a new one")

    if not number_of_cards:
        number_of_cards = 10


    for attempt in range(SYSTEM_SETTINGS["max_retries"]):
        try:
            response = client.chat.completions.create(
                model = SYSTEM_SETTINGS["model"],
                messages = [
                    SYSTEM_SETTINGS["system_role"],
                    {
                        "role": "user",
                        "content": f"Create exactly {number_of_cards} flashcards from this material. {SYSTEM_SETTINGS['prompt']}:\n\n{content[:3000]}"
                    },
                ],
                max_tokens=SYSTEM_SETTINGS["max_tokens"]
            )

            print(f"response: {response}")

            ai_response = response.choices[0].message.content.strip()

            if ai_response.startswith("```"):
                ai_response = ai_response.split("```")[1]
                if ai_response.startswith("json"):
                    ai_response = ai_response[4:]

            flashcards = json.loads(ai_response)
            print(f"flashcards: {flashcards}")

            if selected_deck == "deck" and title:
                if not description:
                    description = f"{number_of_cards} AI-generated flashcards"

                existing_list = db.execute("SELECT * FROM decks WHERE title=?", title)

                if len(existing_list) == 0:
                    deck_id = db.execute("INSERT INTO decks (user_id, title, description) VALUES (?, ?, ?)", session["user_id"], title, description)

            else:
                deck_id = int(deck_option)
                selected_deck = db.execute("SELECT id FROM decks WHERE title = ?", title)[0]["id"]
                deck = db.execute("SELECT * FROM decks WHERE id = ? AND user_id = ?", deck_id, session["user_id"])

                if not deck:
                    return apology("Invalid deck selected", 400)

                existing_count = db.execute("SELECT COUNT(*) as count FROM cards WHERE deck_id = ?", deck_id)[0]["count"]
                new_total = existing_count + number_of_cards

                db.execute("UPDATE decks SET description = ? WHERE id = ?", f"{new_total} cards", deck_id)

            for flashcard in flashcards:
                print(f"{flashcard}")
                front = flashcard["front"]
                print(f"{front}")
                back = flashcard["back"]
                print(f"{back}")

                db.execute("INSERT INTO cards (deck_id, front, back) VALUES(?, ?, ?)", deck_id, front, back)


            session["preview_title"] = title
            session["preview_cards"] = flashcards

            return redirect("/")
        except RateLimitError as e:
            if attempt < SYSTEM_SETTINGS["max_retries"]:
                wait_time = SYSTEM_SETTINGS["retry_delay"] * (2 ** attempt)
                print(f"Rate limit hit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                return "OpenAI rate limit exceeded. Please wait a minute and try again.", 429


@app.route("/study/<int:deck_id>", methods=["GET"])
@login_required
def study(deck_id):
    cards = db.execute("SELECT * FROM cards WHERE deck_id = ?", deck_id)
    mastered = len([c for c in cards if c["mastered"]])
    deck = db.execute("SELECT * FROM decks WHERE id = ? and user_id = ?", deck_id, session["user_id"])
    return render_template("study.html", deck=deck[0], cards=cards, mastered=mastered, total=len(cards))

@app.route("/study/mastered/<int:deck_id>", methods=["GET"])
@login_required
def mastered(deck_id):
    cards = db.execute("SELECT * FROM cards WHERE deck_id = ?", deck_id)
    mastered = len([c for c in cards if c["mastered"]])

    return jsonify({"mastered": mastered, "total": len(cards) })

@app.route("/mark_mastered/<int:card_id>", methods=["POST"])
@login_required
def mark_mastered(card_id):
    db.execute("UPDATE cards SET mastered = 1 WHERE id = ?", card_id)
    return "", 204


@app.route("/delete/<int:deck_id>", methods=["POST"])
@login_required
def delete_deck(deck_id):
    print(f"{deck_id}")
    db.execute("DELETE FROM cards WHERE deck_id = ?", deck_id)
    db.execute("DELETE FROM decks WHERE id = ?", deck_id)

    return "", 204


@app.route("/update", methods=["POST"])
@login_required
def update_card():
    id = request.form.get("card-id")
    back = request.form.get("back-content")

    db.execute("UPDATE cards SET back = ? WHERE id = ?", back, id)
    return "", 204


@app.route("/study/data/<int:deck_id>")
@login_required
def study_data(deck_id):
    cards = db.execute("SELECT * FROM cards WHERE deck_id = ?", deck_id)
    mastered = sum(1 for c in cards if c["mastered"])
    return jsonify(cards=cards, mastered=mastered)



@app.route("/")
@login_required
def index():
    decks = db.execute("SELECT * FROM decks")
    print(f"{decks}")
    return render_template("index.html", decks=decks)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide password", 403)

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    session.clear()

    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("username")
    password = request.form.get("password")
    confirm_password = request.form.get("confirmation")
    existing_name = db.execute("SELECT * FROM users WHERE username == ?", name)

    print(f"{name}")
    print(f"{password}")
    print(f"{confirm_password}")
    print(f"{existing_name}")

    if len(existing_name) > 0:
        return apology("Your selected username is not available", 400)
    elif not name or not password:
        return apology("You haven't submitted a proper register information", 400)
    elif password != confirm_password:
        return apology("Your passwords don't match", 400)

    hashed_password = generate_password_hash(password)

    db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", name, hashed_password)
    new_user = db.execute("SELECT * FROM users WHERE username == ?", name)
    session["user_id"] = new_user[0]["id"]

    return redirect("/")


