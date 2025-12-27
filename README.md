# Catch It - AI-Powered Flashcard Generator

#### Video Demo: https://youtu.be/7JA0wTWTGMI

#### Description:

Catch It is an AI-powered web application that automatically generates study flashcards from any text material. Students paste their notes, textbooks, or lecture transcripts, and GPT-4o-mini creates question-answer flashcards instantly. The app includes an interactive study mode with progress tracking and a unique "error flagging" feature that turns AI imperfection into a learning opportunity.

The app simply does what a highlighter used to be for me with pen and paper.

## Tech Stack

**Backend**: Flask (Python), SQLite with CS50's SQL library
**Frontend**: Bootstrap 5, Vanilla JavaScript
**AI**: OpenAI GPT-4o-mini API
**Authentication**: Flask-Session, Werkzeug password hashing

## Core Functionality

### 1. User Authentication (`/register`, `/login`)
Standard session-based authentication with hashed passwords. Users must register and login to access the application, ensuring data privacy and deck ownership.

### 2. Flashcard Generation (`/create`)
The heart of the application. Users can:
- Create a new deck or add to existing decks
- Paste study material (up to 3000 characters)
- Specify number of cards (10-20)
- Optionally provide a description

The route sends the content to OpenAI's API with a system prompt instructing it to return only JSON-formatted flashcards. Includes retry logic with exponential backoff for rate limiting, JSON parsing with markdown cleanup, and error handling.

Generated flashcards are immediately saved to the database with the associated deck_id.

### 3. Study Mode (`/deck/<int:deck_id>`)
Interactive flashcard interface with:
- Click-to-flip cards showing front (question) then back (answer)
- "I Know This" button marks cards as mastered
- "AI Made a Mistake" button flags incorrect cards for critical evaluation
- "Next Card" advances without marking
- Real-time progress counter showing mastered/total cards
- Visual feedback (green borders for mastered cards)

The JavaScript maintains card state client-side and syncs with the server via fetch API calls.

### 4. Progress Tracking (`/deck/<int:deck_id>/progress`)
JSON endpoint that returns current mastery statistics. Called by the study interface after marking cards, enabling real-time UI updates without page reloads.

### 5. Deck Management (`/`, `/delete/<int:deck_id>`)
Dashboard displays all user decks with titles, descriptions, and card counts. Users can study or delete decks. Deletion removes cards first (respecting foreign key constraints), then removes the deck.

## Database Schema

**users**: id, username, hash
**decks**: id, user_id (FK), title, description, created_at
**cards**: id, deck_id (FK), front, back, mastered, has_error

Foreign keys ensure data integrity. Cards must belong to decks, decks must belong to users.

## Key Design Decisions

**GPT-4o-mini over GPT-4**: 200x cheaper ($0.15 vs $30 per million tokens) with no quality difference for simple flashcard generation. Makes the app economically viable.

**Error flagging over editing**: Instead of allowing users to edit AI mistakes, they simply flag errors. This forces critical engagement with material—identifying errors is pedagogically more valuable than passive card review.

**Session-based authentication**: Server-side sessions are simpler and more secure than JWTs for a traditional web app. Matches CS50 patterns.

**Hybrid progress updates**: Database is source of truth, but frontend fetches fresh data via API after updates. Balances accuracy with responsive UX.

## Files Overview

**app.py**: All routes and business logic. Handles authentication, flashcard generation with OpenAI API, study mode, and deck management.

**helpers.py**: Utility functions including `login_required` decorator and `apology` error handler.

**templates/**: Jinja2 templates extending `layout.html`. Key templates are `create.html` (generation form), `study.html` (interactive flashcards with JavaScript), and `index.html` (deck dashboard).

**flashcards.db**: SQLite database with three tables as described above.

## Challenges Overcome

**OpenAI Rate Limiting**: Implemented retry logic with exponential backoff (2s, 4s, 8s delays) and added mock mode for development testing.

**JSON Parsing**: AI sometimes wraps JSON in markdown code blocks. Added preprocessing to strip ```json``` wrappers and handle variations.

**Foreign Key Constraints**: Cards must be deleted before decks. Implemented two-step deletion process.

**Real-time Updates**: Created `/progress` API endpoint so JavaScript can fetch fresh statistics after marking cards, updating UI without reload.


## Why This Project Matters

Often we read "AI can make mistakes" or "What's the point if AI can make everything, faster". AI is still a tool, a tool which goes full circle. AI is the source, and we are its source. Not all us, but some in the future might write the papers that'll be used to once more, train a newer model.

---

**Built for CS50x 2025**
