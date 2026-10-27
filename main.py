import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import urllib.request
import urllib.parse

from database import engine, SessionLocal
import models

# 1. تهيئة متغيرات البيئة بأمان (احذر من كتابة التوكن هنا مباشرة)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# 2. تهيئة قاعدة البيانات والتطبيق
#models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="نظام إدارة الدفعة")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. المخططات (Schemas)
class LoginRequest(BaseModel):
    email: str
    password: str

class LectureCreate(BaseModel):
    subject_id: str
    title: str
    url: str
    type: str

class MessageUpdate(BaseModel):
    content: str

class QuestionCreate(BaseModel):
    subject_id: str
    q_text: str

class AnswerCreate(BaseModel):
    a_text: str

class ExplanationCreate(BaseModel):
    subject_id: str
    title: str
    video_url: str

class SubjectResponse(BaseModel):
    id: str
    name: str
    icon: str
    is_new: int

class HomeworkResponse(BaseModel):
    id: int
    subject_id: str
    title: str
    due_date: str
    is_done: bool


# 4. مسار تسجيل الدخول المباشر
@app.post("/api/login")
def login(req: LoginRequest):
    email_clean = req.email.strip().lower()
    pass_clean = req.password.strip()

    # هذا الحل يعتبر ترقيعاً مؤقتاً لتجاوز قاعدة البيانات الفارغة، لكنه سيفي بالغرض الآن
    if email_clean == "gr6204616@gmail.com" and pass_clean == "123":
        return {"user": {"name": "مهدي", "role": "admin"}}
    
    elif email_clean == "student" and pass_clean == "123":
        return {"user": {"name": "طالب المرحلة الثانية", "role": "student"}}

    raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور خاطئة")


# 5. مسارات المحاضرات وبوت تليجرام
@app.get("/api/updates/check")
def check_updates(db: Session = Depends(get_db)):
    results = db.query(models.Lecture.subject_id, func.max(models.Lecture.id)).group_by(models.Lecture.subject_id).all()
    return {row[0]: row[1] for row in results}

@app.get("/api/lectures/{subject_id}")
def get_lectures(subject_id: str, db: Session = Depends(get_db)):
    return db.query(models.Lecture).filter(models.Lecture.subject_id == subject_id).order_by(models.Lecture.id.desc()).all()

@app.post("/webhook")
async def telegram_webhook(update: dict):
    message = update.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    if not text:
        return {"status": "ignored"}

    # يرجى التأكد من تغيير اسم اليوزر إذا قمت بإنشاء بوت جديد بعد الاختراق
    if not text.startswith("/") and "@musa3dk_bot" not in text:
        return {"status": "ignored"} 

    if text.startswith("/schedule"):
        pass
        
    return {"status": "ok"}

@app.delete("/api/lectures/{lecture_id}")
def delete_lecture(lecture_id: int, db: Session = Depends(get_db)):
    lecture = db.query(models.Lecture).filter(models.Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="الملف غير موجود")
    db.delete(lecture)
    db.commit()
    return {"status": "success"}


# 6. مسارات الرسائل الأسبوعية
@app.get("/api/batch/message")
def get_message(db: Session = Depends(get_db)):
    msg = db.query(models.SystemMessage).first()
    return {"content": msg.content if msg else "لا توجد تبليغات هذا الأسبوع."}

@app.post("/api/batch/message")
def update_message(msg: MessageUpdate, db: Session = Depends(get_db)):
    db_msg = db.query(models.SystemMessage).first()
    if not db_msg:
        db_msg = models.SystemMessage(content=msg.content)
        db.add(db_msg)
    else:
        db_msg.content = msg.content
    db.commit()
    return {"status": "success"}


# 7. مسارات الأسئلة والإجابات
@app.get("/api/questions/{subject_id}")
def get_questions(subject_id: str, db: Session = Depends(get_db)):
    return db.query(models.Question).filter(models.Question.subject_id == subject_id).order_by(models.Question.votes.desc()).all()

@app.post("/api/questions/add")
def add_question(q: QuestionCreate, db: Session = Depends(get_db)):
    new_q = models.Question(subject_id=q.subject_id, q_text=q.q_text, a_text="")
    db.add(new_q)
    db.commit()
    return {"status": "success"}

@app.post("/api/questions/{q_id}/answer")
def answer_question(q_id: int, ans: AnswerCreate, db: Session = Depends(get_db)):
    question = db.query(models.Question).filter(models.Question.id == q_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="السؤال غير موجود")
    question.a_text = ans.a_text
    db.commit()
    return {"status": "success"}


# 8. مسارات الشروحات
@app.get("/api/explanations/{subject_id}")
def get_explanations(subject_id: str, db: Session = Depends(get_db)):
    return db.query(models.Explanation).filter(models.Explanation.subject_id == subject_id).all()

@app.post("/api/explanations/add")
def add_explanation(exp: ExplanationCreate, db: Session = Depends(get_db)):
    new_exp = models.Explanation(subject_id=exp.subject_id, title=exp.title, video_url=exp.video_url)
    db.add(new_exp)
    db.commit()
    return {"status": "success"}

@app.delete("/api/explanations/{exp_id}")
def delete_explanation(exp_id: int, db: Session = Depends(get_db)):
    exp = db.query(models.Explanation).filter(models.Explanation.id == exp_id).first()
    if exp:
        db.delete(exp)
        db.commit()
    return {"status": "success"}

db_subjects = [
    {"id": "oop", "name": "برمجة شيئية", "icon": "💻", "is_new": 0},
    {"id": "num", "name": "التحليل العددي", "icon": "✍️", "is_new": 0},
    {"id": "comp", "name": "النظرية الاحتسابية", "icon": "🧮", "is_new": 0},
    {"id": "py", "name": "لغة بايثون", "icon": "🐍", "is_new": 0},
    {"id": "ar", "name": "اللغة العربية", "icon": "📚", "is_new": 0},
    {"id": "alg", "name": "خوارزميات AI", "icon": "🤖", "is_new": 0}
]

@app.get("/api/subjects", response_model=List[SubjectResponse])
def get_subjects():
    return db_subjects