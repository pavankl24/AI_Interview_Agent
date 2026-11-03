# COGNIV AI
### Think Beyond. Perform Better.
*Intelligent Interview Experience*

version 2:            
             AI INTERVIEW AGENT
                    │
             Select interview
                    │
       ┌────────────┼────────────┐
       ↓            ↓            ↓
    Python         SQL         AI/ML
       │
       ↓
   Ask Question
       │
       ↓
 Candidate Answer
       │
       ↓
    Evaluate
       │
       ↓
  Next Question
       │
       ↓
  Interview Ends
       │
       ↓
 Final Report 
version 3:
                    Groq
                     ↓
             ┌───────────────┐
             │ AI Response   │
             └───────────────┘
                ↓         ↓
          Evaluation    Question
                ↓         ↓
          evaluations   questions
                ↓         ↓
                └────┬────┘
                     ↓
               Final Report

✅ V1 — Basic AI interviewer
✅ V2 — Interview types
✅ V3 — Structured JSON
✅ V3 — Final report
⬜ V4 — Better scoring/report logic
✅ V5 — FastAPI backend
✅ V6 — Responsive web frontend
⬜ V7 — MSSQL database
⬜ V8 — Authentication/history

## Run the React + TypeScript app

Install the JavaScript dependencies once with `npm install`.

### Mock UI preview

1. Build the frontend with `npm run build`.
2. Run `npm run preview` from this folder.
3. Open `http://127.0.0.1:4174` in a browser.

This local preview uses scripted sample interview questions and a sample report.
If the preview is already running, the command prints its URL and exits cleanly.

Interview setup includes a saved format preference: **Balanced**, **Technical conversation**, or **Coding & problem solving**. The selected format changes the questions in both preview and live API sessions.

### Run with the live FastAPI interview API

1. Build the frontend with `npm run build`.
2. Activate a Python virtual environment with the packages in `requirements.txt` installed and set `GROQ_API_KEY` in `.env`.
3. Start FastAPI from this folder: `uvicorn api:app --reload`.
4. Open `http://127.0.0.1:8000` in a browser.

For frontend hot reload while FastAPI runs, use `npm run dev` and open `http://127.0.0.1:5173`.

The web app uses the interview API for live question, answer, and report generation. Set `GROQ_API_KEY` in `.env` to use live interviews. The dashboard, profile preferences, and practice history are UI features saved in the browser on this device.

### Supabase report history

1. Create a Supabase project, then run `supabase/migrations/001_interview_sessions.sql` in its SQL Editor.
2. Copy `.env.example` to `.env` and set `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, and `GROQ_API_KEY`.
3. Install backend dependencies with `pip install -r requirements.txt`, rebuild the frontend, then start FastAPI with `uvicorn api:app --reload`.

When the server Supabase settings are present, completed interview reports and their topic, difficulty, format, score, and question count are saved to Postgres and history loads from Supabase. Interview answers/transcripts are not stored. Without Supabase settings, the UI continues using browser-local history. Keep `SUPABASE_SECRET_KEY` only in the server `.env`; never put it in React or commit `.env`.

The current history owner is a random browser ID, not a login. It is suitable for a single-user prototype, not secure multi-user access. Add Supabase Auth and user-scoped ownership/RLS policies before deploying for multiple users.
