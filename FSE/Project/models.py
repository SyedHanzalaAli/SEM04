from datetime import datetime
from extensions import db

class User(db.Model):
    __tablename__ = "Users"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    email       = db.Column(db.String(150), unique=True, nullable=False)
    password    = db.Column(db.String(255), nullable=False)
    role        = db.Column(db.Enum("teacher", "student"), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    courses     = db.relationship("Course", backref="teacher", lazy=True)
    progress    = db.relationship("Progress", backref="student", lazy=True)
    quizzes     = db.relationship("Quiz", backref="student", lazy=True)
    materials   = db.relationship("LessonMaterial", backref="teacher", lazy=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email,
                "role": self.role, "created_at": self.created_at.isoformat()}


class Course(db.Model):
    __tablename__ = "Courses"
    id          = db.Column(db.Integer, primary_key=True)
    teacher_id  = db.Column(db.Integer, db.ForeignKey("Users.id", ondelete="CASCADE"), nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    lessons     = db.relationship("Lesson", backref="course", lazy=True, cascade="all, delete-orphan")

    def to_dict(self, lesson_count=0):
        return {"id": self.id, "title": self.title, "description": self.description,
                "teacher_id": self.teacher_id,
                "teacher_name": self.teacher.name if self.teacher else None,
                "lesson_count": lesson_count, "created_at": self.created_at.isoformat()}


class Lesson(db.Model):
    __tablename__ = "Lessons"
    id          = db.Column(db.Integer, primary_key=True)
    course_id   = db.Column(db.Integer, db.ForeignKey("Courses.id", ondelete="CASCADE"), nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    youtube_url = db.Column(db.String(500), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    summary     = db.relationship("AISummary", backref="lesson", uselist=False, cascade="all, delete-orphan")
    progress    = db.relationship("Progress", backref="lesson", lazy=True, cascade="all, delete-orphan")
    quizzes     = db.relationship("Quiz", backref="lesson", lazy=True, cascade="all, delete-orphan")
    materials   = db.relationship("LessonMaterial", backref="lesson", lazy=True, cascade="all, delete-orphan")

    def to_dict(self, include_summary=False):
        data = {"id": self.id, "course_id": self.course_id,
                "course_title": self.course.title if self.course else None,
                "title": self.title, "youtube_url": self.youtube_url,
                "has_summary": self.summary is not None,
                "created_at": self.created_at.isoformat()}
        if include_summary and self.summary:
            data["summary"] = self.summary.to_dict()
        return data


class AISummary(db.Model):
    __tablename__ = "AI_Summaries"
    id           = db.Column(db.Integer, primary_key=True)
    lesson_id    = db.Column(db.Integer, db.ForeignKey("Lessons.id", ondelete="CASCADE"), unique=True, nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "lesson_id": self.lesson_id,
                "summary_text": self.summary_text,
                "generated_at": self.generated_at.isoformat()}


class Progress(db.Model):
    __tablename__ = "Progress_Tracking"
    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("Users.id", ondelete="CASCADE"), nullable=False)
    lesson_id   = db.Column(db.Integer, db.ForeignKey("Lessons.id", ondelete="CASCADE"), nullable=False)
    status      = db.Column(db.Enum("not-started", "in-progress", "completed"), default="not-started")
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("student_id", "lesson_id"),)

    def to_dict(self):
        return {"id": self.id, "student_id": self.student_id, "lesson_id": self.lesson_id,
                "lesson_title": self.lesson.title if self.lesson else None,
                "status": self.status, "updated_at": self.updated_at.isoformat()}


class LessonMaterial(db.Model):
    __tablename__ = "Lesson_Materials"
    id            = db.Column(db.Integer, primary_key=True)
    lesson_id     = db.Column(db.Integer, db.ForeignKey("Lessons.id", ondelete="CASCADE"), nullable=False)
    teacher_id    = db.Column(db.Integer, db.ForeignKey("Users.id",   ondelete="CASCADE"), nullable=False)
    title         = db.Column(db.String(200), nullable=False)
    material_type = db.Column(db.Enum("notes", "slides", "questions", "link", "other"), default="other")
    content       = db.Column(db.Text)           # raw text / markdown
    file_url      = db.Column(db.String(500))    # external link
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":            self.id,
            "lesson_id":     self.lesson_id,
            "lesson_title":  self.lesson.title if self.lesson else None,
            "teacher_id":    self.teacher_id,
            "teacher_name":  self.teacher.name if self.teacher else None,
            "title":         self.title,
            "material_type": self.material_type,
            "content":       self.content,
            "file_url":      self.file_url,
            "created_at":    self.created_at.isoformat(),
        }


class Quiz(db.Model):
    __tablename__ = "Quizzes"
    id              = db.Column(db.Integer, primary_key=True)
    lesson_id       = db.Column(db.Integer, db.ForeignKey("Lessons.id", ondelete="CASCADE"), nullable=False)
    student_id      = db.Column(db.Integer, db.ForeignKey("Users.id",   ondelete="CASCADE"), nullable=False)
    score           = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=5)
    submitted       = db.Column(db.Boolean, default=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at    = db.Column(db.DateTime, nullable=True)
    questions       = db.relationship("QuizQuestion", backref="quiz", lazy=True,
                                      cascade="all, delete-orphan", order_by="QuizQuestion.question_no")

    def to_dict(self, include_questions=False):
        data = {
            "id":              self.id,
            "lesson_id":       self.lesson_id,
            "lesson_title":    self.lesson.title if self.lesson else None,
            "student_id":      self.student_id,
            "score":           self.score,
            "total_questions": self.total_questions,
            "submitted":       self.submitted,
            "created_at":      self.created_at.isoformat(),
            "submitted_at":    self.submitted_at.isoformat() if self.submitted_at else None,
            "pct":             round(self.score / self.total_questions * 100) if self.total_questions else 0,
        }
        if include_questions:
            data["questions"] = [q.to_dict() for q in self.questions]
        return data


class QuizQuestion(db.Model):
    __tablename__ = "Quiz_Questions"
    id              = db.Column(db.Integer, primary_key=True)
    quiz_id         = db.Column(db.Integer, db.ForeignKey("Quizzes.id", ondelete="CASCADE"), nullable=False)
    question_no     = db.Column(db.Integer, nullable=False)
    question_text   = db.Column(db.Text, nullable=False)
    option_a        = db.Column(db.String(400), nullable=False)
    option_b        = db.Column(db.String(400), nullable=False)
    option_c        = db.Column(db.String(400), nullable=False)
    option_d        = db.Column(db.String(400), nullable=False)
    correct_option  = db.Column(db.Enum("A","B","C","D"), nullable=False)
    student_answer  = db.Column(db.Enum("A","B","C","D"), nullable=True)
    is_correct      = db.Column(db.Boolean, nullable=True)
    __table_args__  = (db.UniqueConstraint("quiz_id", "question_no"),)

    def to_dict(self, reveal_answer=False):
        data = {
            "id":            self.id,
            "quiz_id":       self.quiz_id,
            "question_no":   self.question_no,
            "question_text": self.question_text,
            "option_a":      self.option_a,
            "option_b":      self.option_b,
            "option_c":      self.option_c,
            "option_d":      self.option_d,
            "student_answer": self.student_answer,
            "is_correct":    self.is_correct,
        }
        # Only reveal correct answer after submission
        if reveal_answer:
            data["correct_option"] = self.correct_option
        return data

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('Users.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('Courses.id', ondelete='CASCADE'), nullable=False)