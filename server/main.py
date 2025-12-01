from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
import json
import uuid
import os
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class QuizStartRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    level: str = Field(..., description="Quiz difficulty level", 
                       pattern="^(beginner|intermediate|advanced)$")
    question_count: int = Field(
        default=10,
        ge=5,
        le=20,
        description="Number of questions to generate for the quiz"
    )
    focus: Optional[str] = Field(default="Vocabulary", description="Quiz focus area")

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
    answers: List[str] = Field(
        ...,
        min_items=1,
        max_items=50,
        description="Answers in the exact order of the quiz questions"
    )

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

quiz_sessions: Dict[str, Dict] = {}
quiz_results: Dict[str, Dict] = {}
user_stats: Dict[str, Dict] = {}

MAX_RECENT_HISTORY = 10

def _ensure_user_record(user_id: str) -> Dict:
    if user_id not in user_stats:
        user_stats[user_id] = {
            "current_level": "beginner",
            "total_quizzes": 0,
            "avg_score": 0.0,
            "total_score": 0.0,
            "recent_history": [],
            "latest_quiz": None,
        }
    return user_stats[user_id]

async def generate_quiz_questions(level: str, question_count: int) -> List[dict]:
    if not openai_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Question generation service unavailable - API key not configured"
        )
    
    prompt = f"""Generate {question_count} TOEFL vocabulary multiple-choice questions at {level} level. 
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
        
        if len(questions) != question_count:
            raise ValueError(f"Expected {question_count} questions, got {len(questions)}")
        
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
                      questions_json: str, question_count: int, focus: Optional[str]) -> str:
    quiz_sessions[session_id] = {
        "user_id": user_id,
        "session_id": session_id,
        "level": level,
        "focus": focus,
        "question_count": question_count,
        "questions_json": questions_json,
        "created_at": datetime.utcnow().isoformat()
    }
    _ensure_user_record(user_id)
    print(f"Saving quiz session: {session_id} for user: {user_id}")
    return session_id

def get_quiz_session(session_id: str) -> Optional[dict]:
    print(f"Getting quiz session: {session_id}")
    return quiz_sessions.get(session_id)

def save_quiz_result(user_id: str, session_id: str, score: float, 
                     total: int, answers: List[str]) -> None:
    submitted_at = datetime.utcnow().isoformat()
    session_data = quiz_sessions.get(session_id, {})
    quiz_results[session_id] = {
        "session_id": session_id,
        "user_id": user_id,
        "score": round(score, 2),
        "total_questions": total,
        "answers": answers,
        "level": session_data.get("level"),
        "focus": session_data.get("focus"),
        "submitted_at": submitted_at
    }
    print(f"Saving result for session: {session_id}, score: {score}")
    update_user_progress(
        user_id=user_id,
        new_score=score,
        session_data=session_data,
        submitted_at=submitted_at,
        total_questions=total,
        session_id=session_id
    )

def get_user_stats(user_id: str) -> Optional[dict]:
    print(f"Getting stats for user: {user_id}")
    return user_stats.get(user_id)

def get_quiz_history(user_id: str, limit: int = 5) -> List[dict]:
    print(f"Getting history for user: {user_id}")
    record = user_stats.get(user_id)
    if not record:
        return []
    return record.get("recent_history", [])[:limit]

def update_user_progress(user_id: str, new_score: float, 
                         session_data: Optional[dict] = None,
                         submitted_at: Optional[str] = None,
                         total_questions: Optional[int] = None,
                         session_id: Optional[str] = None) -> dict:
    record = _ensure_user_record(user_id)
    record["total_quizzes"] += 1
    record["total_score"] += new_score
    record["avg_score"] = record["total_score"] / record["total_quizzes"]
    level = session_data.get("level") if session_data else record["current_level"]
    if level:
        record["current_level"] = level
    timestamp = submitted_at or datetime.utcnow().isoformat()
    latest_quiz = {
        "session_id": session_id or (session_data.get("session_id") if session_data else None),
        "score": round(new_score, 2),
        "total": total_questions or (session_data.get("question_count") if session_data else None),
        "level": level or "beginner",
        "focus": (session_data.get("focus") if session_data else None) or "Vocabulary",
        "submitted_at": timestamp
    }
    record["latest_quiz"] = latest_quiz
    history_entry = {
        "session_id": latest_quiz["session_id"],
        "date": timestamp,
        "level": latest_quiz["level"],
        "score": latest_quiz["score"],
    }
    record["recent_history"].insert(0, history_entry)
    record["recent_history"] = record["recent_history"][:MAX_RECENT_HISTORY]
    return record


@app.post("/api/quiz/start", response_model=QuizStartResponse, 
          status_code=status.HTTP_200_OK)
async def start_quiz(request: QuizStartRequest):
    try:
        session_id = str(uuid.uuid4())
        questions_data = await generate_quiz_questions(request.level, request.question_count)
        questions_json = json.dumps(questions_data)
        save_quiz_session(
            user_id=request.user_id,
            session_id=session_id,
            level=request.level,
            questions_json=questions_json,
            question_count=request.question_count,
            focus=request.focus
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
            total_questions=len(questions_data),
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
            total_questions=session_data.get("question_count", len(questions_data)),
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
        if len(request.answers) != len(questions_data):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Number of answers does not match quiz questions"
            )
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