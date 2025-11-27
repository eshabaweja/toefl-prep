from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import json
import uuid
import os
import asyncio
from openai import AsyncOpenAI
import httpx
from dotenv import load_dotenv

load_dotenv()

class QuizStartRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    level: str = Field(..., description="Quiz difficulty level", 
                       pattern="^(beginner|intermediate|advanced)$")

class Question(BaseModel):
    question_number: int
    question: str
    options: List[str] = Field(..., min_items=4, max_items=4)

class QuizStartResponse(BaseModel):
    session_id: str
    level: str
    total_questions: int
    questions: List[Question]

class QuizSubmitRequest(BaseModel):
    session_id: str
    user_id: str
    answers: List[str] = Field(..., min_items=10, max_items=10)

class QuestionResult(BaseModel):
    question_number: int
    user_answer: str
    correct_answer: str
    is_correct: bool

class QuizSubmitResponse(BaseModel):
    session_id: str
    score: float
    total_questions: int
    correct_count: int
    results: List[QuestionResult]

class QuizHistoryItem(BaseModel):
    session_id: str
    date: str
    level: str
    score: float

class DashboardResponse(BaseModel):
    user_id: str
    current_level: str
    total_quizzes: int
    average_score: float
    recent_history: List[QuizHistoryItem]

app = FastAPI(
    title="TOEFL Vocabulary Training API",
    description="API for TOEFL vocabulary quiz generation and progress tracking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not found in environment variables")
else:
    print(f"INFO: OpenAI API key loaded (length: {len(OPENAI_API_KEY)})")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

quiz_sessions: dict[str, dict] = {}
quiz_results: dict[str, dict] = {}
user_stats: dict[str, dict] = {}

async def generate_quiz_questions(level: str) -> List[dict]:
    if not openai_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Question generation service unavailable - API key not configured"
        )
    
    prompt = f"""Generate 10 TOEFL vocabulary multiple-choice questions at {level} level. 
Each question should test vocabulary in context. 
Return ONLY a JSON array with this exact structure, no additional text:
[{{"question": "...", "options": ["A", "B", "C", "D"], "correct_answer": "A"}}]

Make sure:
- Questions test vocabulary understanding in context
- All 4 options are plausible
- Correct answer is clearly marked
- Questions are appropriate for {level} level TOEFL preparation"""

    try:
        print(f"INFO: Generating quiz questions for level: {level}")
        response = await asyncio.wait_for(
            openai_client.chat.completions.create(
                model="gpt-4o-mini",  
                messages=[
                    {"role": "system", "content": "You are a TOEFL vocabulary test expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7, 
                max_tokens=2000
            ),
            timeout=30.0  
        )
        print("INFO: Received response from OpenAI API")
        
        content = response.choices[0].message.content.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        questions = json.loads(content)
        
        if len(questions) != 10:
            raise ValueError(f"Expected 10 questions, got {len(questions)}")
        
        return questions
        
    except asyncio.TimeoutError:
        print("ERROR: OpenAI API request timed out after 30 seconds")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Question generation service unavailable - request timeout. Please try again."
        )
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse LLM response: {str(e)}"
        )
    except Exception as e:
        print(f"ERROR: OpenAI API error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Question generation service unavailable: {str(e)}"
        )

def save_quiz_session(user_id: str, session_id: str, level: str, 
                      questions_json: str) -> str:
    quiz_sessions[session_id] = {
        "user_id": user_id,
        "session_id": session_id,
        "level": level,
        "questions_json": questions_json,
        "created_at": datetime.utcnow().isoformat()
    }
    print(f"Saving quiz session: {session_id} for user: {user_id}")
    return session_id

def get_quiz_session(session_id: str) -> Optional[dict]:
    print(f"Getting quiz session: {session_id}")
    return quiz_sessions.get(session_id)

def save_quiz_result(user_id: str, session_id: str, score: float, 
                     total: int, answers: List[str]) -> None:
    print(f"Saving result for session: {session_id}, score: {score}")

def get_user_stats(user_id: str) -> Optional[dict]:
    print(f"Getting stats for user: {user_id}")
    return None

def get_quiz_history(user_id: str, limit: int = 5) -> List[dict]:
    print(f"Getting history for user: {user_id}")
    return []

def update_user_progress(user_id: str, new_score: float) -> None:
    print(f"Updating progress for user: {user_id}, score: {new_score}")


@app.post("/api/quiz/start", response_model=QuizStartResponse, 
          status_code=status.HTTP_200_OK)
async def start_quiz(request: QuizStartRequest):
    try:
        session_id = str(uuid.uuid4())
        questions_data = await generate_quiz_questions(request.level)
        questions_json = json.dumps(questions_data)
        save_quiz_session(
            user_id=request.user_id,
            session_id=session_id,
            level=request.level,
            questions_json=questions_json
        )
        
        questions_for_response = [
            Question(
                question_number=idx + 1,
                question=q["question"],
                options=q["options"]
            )
            for idx, q in enumerate(questions_data)
        ]
        
        return QuizStartResponse(
            session_id=session_id,
            level=request.level,
            total_questions=10,
            questions=questions_for_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start quiz: {str(e)}"
        )


@app.get("/api/quiz/questions/{session_id}", response_model=QuizStartResponse,
         status_code=status.HTTP_200_OK)
async def get_quiz_questions(session_id: str):
    try:
        session_data = get_quiz_session(session_id)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz session not found"
            )
        
        questions_data = json.loads(session_data["questions_json"])
        questions_for_response = [
            Question(
                question_number=idx + 1,
                question=q["question"],
                options=q["options"]
            )
            for idx, q in enumerate(questions_data)
        ]
        
        return QuizStartResponse(
            session_id=session_id,
            level=session_data["level"],
            total_questions=len(questions_data),
            questions=questions_for_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quiz questions: {str(e)}"
        )


@app.post("/api/quiz/submit", response_model=QuizSubmitResponse,
          status_code=status.HTTP_200_OK)
async def submit_quiz(request: QuizSubmitRequest):
    try:
        session_data = get_quiz_session(request.session_id)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz session not found"
            )
        
        if session_data["user_id"] != request.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User ID does not match quiz session"
            )
        
        questions_data = json.loads(session_data["questions_json"])
        results = []
        correct_count = 0
        
        for idx, (user_answer, question) in enumerate(zip(request.answers, questions_data)):
            correct_answer = question["correct_answer"]
            is_correct = user_answer == correct_answer
            
            if is_correct:
                correct_count += 1
            
            results.append(QuestionResult(
                question_number=idx + 1,
                user_answer=user_answer,
                correct_answer=correct_answer,
                is_correct=is_correct
            ))
        
        total_questions = len(questions_data)
        score = (correct_count / total_questions) * 100
        save_quiz_result(
            user_id=request.user_id,
            session_id=request.session_id,
            score=score,
            total=total_questions,
            answers=request.answers
        )
        
        update_user_progress(request.user_id, score)
        
        return QuizSubmitResponse(
            session_id=request.session_id,
            score=round(score, 2),
            total_questions=total_questions,
            correct_count=correct_count,
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit quiz: {str(e)}"
        )


@app.get("/api/dashboard/{user_id}", response_model=DashboardResponse,
         status_code=status.HTTP_200_OK)
async def get_dashboard(user_id: str):
    try:
        user_stats = get_user_stats(user_id)
        
        if not user_stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        quiz_history = get_quiz_history(user_id, limit=5)
        
        history_items = [
            QuizHistoryItem(
                session_id=quiz["session_id"],
                date=quiz["date"],
                level=quiz["level"],
                score=round(quiz["score"], 2)
            )
            for quiz in quiz_history
        ]
        
        return DashboardResponse(
            user_id=user_id,
            current_level=user_stats["current_level"],
            total_quizzes=user_stats["total_quizzes"],
            average_score=round(user_stats["avg_score"], 2),
            recent_history=history_items
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard: {str(e)}"
        )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "openai_configured": OPENAI_API_KEY is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)