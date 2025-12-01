# toefl-prep

A web application for AI-assisted vocabulary learning for the TOEFL iBT. The project is split into a Vite
frontend (`client/`) and a FastAPI backend (`server/`).

## Running the backend

1. Create `server/.env` and add your OpenAI credentials:
   ```
   OPENAI_API_KEY=sk-...
   ```
2. Install dependencies once from the project root:
   ```
   pip install -r requirements.txt
   ```
3. Start the API:
   ```
   cd server
   uvicorn main:app --reload
   ```
   The server listens on `http://localhost:8000` by default.

## Running the frontend

1. Install dependencies:
   ```
   cd client
   npm install
   ```
2. Point the UI at the backend by setting `VITE_API_BASE_URL` (for example, in `client/.env`):
   ```
   VITE_API_BASE_URL=http://localhost:8000
   VITE_DEMO_USER_ID=demo-user
   ```
3. Start Vite:
   ```
   npm run dev
   ```

The quiz page now talks directly to the FastAPI server for `/api/quiz/start`, `/api/quiz/questions/{session_id}`,
and `/api/quiz/submit`.
