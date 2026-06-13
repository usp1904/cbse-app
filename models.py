"""SQLAlchemy ORM models for all database tables.

Used alongside the existing db.py abstraction. Phased migration:
Phase 1: Model definitions + engine setup (this file + db_sa.py)
Phase 2: Migrate critical reads to SQLAlchemy
Phase 3: Migrate writes
"""

import os
import logging
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Date,
    ForeignKey, UniqueConstraint, Index, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session as SASession

log = logging.getLogger("cbse.models")


class Base(DeclarativeBase):
    pass


# ─── Content Tables ──────────────────────────────────────────────────────────


class Board(Base):
    __tablename__ = "boards"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    ncert_url = Column(String, nullable=True)

    subjects = relationship("Subject", back_populates="board", lazy="selectin")


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(String, primary_key=True)
    board_id = Column(String, ForeignKey("boards.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    ncert_url = Column(String, nullable=True)

    board = relationship("Board", back_populates="subjects", lazy="joined")
    books = relationship("Book", back_populates="subject", lazy="selectin")


class Book(Base):
    __tablename__ = "books"
    id = Column(String, primary_key=True)
    subject_id = Column(String, ForeignKey("subjects.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    ncert_url = Column(String, nullable=True)

    subject = relationship("Subject", back_populates="books", lazy="joined")


class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(String, primary_key=True)
    book_id = Column(String, ForeignKey("books.id"), nullable=True)
    subject_id = Column(String, nullable=False)
    board_id = Column(String, nullable=False)
    num = Column(Integer, nullable=False)
    title = Column(String, nullable=False)

    topics = relationship("Topic", back_populates="chapter", lazy="selectin",
                          order_by="Topic.num")


class Topic(Base):
    __tablename__ = "topics"
    id = Column(String, primary_key=True)
    chapter_id = Column(String, ForeignKey("chapters.id"), nullable=False)
    num = Column(Integer, nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)

    chapter = relationship("Chapter", back_populates="topics", lazy="joined")
    chunks = relationship("Chunk", back_populates="topic", lazy="selectin",
                          order_by="Chunk.seq")
    problems = relationship("Problem", back_populates="topic", lazy="selectin",
                            order_by="Problem.seq")


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(String, primary_key=True)
    topic_id = Column(String, ForeignKey("topics.id"), nullable=True)
    chapter_id = Column(String, nullable=True)
    parent_id = Column(String, nullable=True)
    level = Column(Integer, nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    content_type = Column(String, default="text")
    seq = Column(Integer, nullable=True)

    topic = relationship("Topic", back_populates="chunks", lazy="joined")


class Problem(Base):
    __tablename__ = "problems"
    id = Column(String, primary_key=True)
    topic_id = Column(String, ForeignKey("topics.id"), nullable=True)
    chapter_id = Column(String, nullable=False)
    problem_text = Column(Text, nullable=False)
    solution_text = Column(Text, nullable=True)
    problem_type = Column(String, nullable=True)
    seq = Column(Integer, nullable=True)

    topic = relationship("Topic", back_populates="problems", lazy="joined")


class ContentMeta(Base):
    __tablename__ = "content_meta"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)


# ─── Learner / Gamification Tables ───────────────────────────────────────────


class Learner(Base):
    __tablename__ = "learner"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, default="Learner")
    email = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_active = Column(String, nullable=True)
    lives = Column(Integer, default=5)
    max_lives = Column(Integer, default=5)
    last_life_refill = Column(String, nullable=True)
    total_xp_earned = Column(Integer, default=0)
    topics_completed = Column(Integer, default=0)
    quizzes_taken = Column(Integer, default=0)
    quiz_correct = Column(Integer, default=0)
    quiz_total = Column(Integer, default=0)
    mock_exams_taken = Column(Integer, default=0)


class Session(Base):
    __tablename__ = "sessions"
    token = Column(String, primary_key=True)
    learner_id = Column(Integer, default=1)
    created_at = Column(String, default=datetime.now)
    expires_at = Column(String, nullable=True)


class XPEvent(Base):
    __tablename__ = "xp_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    xp = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    chapter_id = Column(String, nullable=True)
    topic_id = Column(String, nullable=True)
    created_at = Column(String, default=datetime.now)


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(String, nullable=False)
    topic_id = Column(String, nullable=True)
    status = Column(String, default="locked")
    xp_earned = Column(Integer, default=0)
    time_spent = Column(Integer, default=0)
    last_accessed = Column(String, nullable=True)
    completions = Column(Integer, default=0)
    quiz_score = Column(Float, nullable=True)
    __table_args__ = (UniqueConstraint("chapter_id", "topic_id"),)


class LifelineLog(Base):
    __tablename__ = "lifeline_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    lifeline_type = Column(String, nullable=False)
    chapter_id = Column(String, nullable=True)
    topic_id = Column(String, nullable=True)
    xp_cost = Column(Integer, default=5)
    used_at = Column(String, default=datetime.now)


class DailyChallenge(Base):
    __tablename__ = "daily_challenges"
    challenge_date = Column(String, primary_key=True)
    board_id = Column(String, nullable=True)
    subject_id = Column(String, nullable=True)
    type_id = Column(String, nullable=True)
    question_ids = Column(String, nullable=True)
    bonus_xp = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    score = Column(Integer, default=0)
    total = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)


class ConceptView(Base):
    __tablename__ = "concept_views"
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(String, nullable=True)
    viewed_at = Column(String, default=datetime.now)


# ─── Badges ──────────────────────────────────────────────────────────────────


class Badge(Base):
    __tablename__ = "badges"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    nep_skill = Column(String, nullable=True)


class LearnerBadge(Base):
    __tablename__ = "learner_badges"
    learner_id = Column(Integer, default=1, primary_key=True)
    badge_id = Column(String, ForeignKey("badges.id"), primary_key=True)
    earned_at = Column(String, default=datetime.now)


# ─── Spaced Repetition ───────────────────────────────────────────────────────


class ReviewSchedule(Base):
    __tablename__ = "review_schedule"
    topic_id = Column(String, ForeignKey("topics.id"), primary_key=True)
    ease_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=0)
    repetitions = Column(Integer, default=0)
    next_review_date = Column(String, nullable=True)
    last_reviewed = Column(String, nullable=True)
    last_quality = Column(Integer, nullable=True)


# ─── Knowledge Graph ─────────────────────────────────────────────────────────


class KnowledgeGraph(Base):
    __tablename__ = "knowledge_graph"
    id = Column(String, primary_key=True)
    subject_id = Column(String, nullable=True)
    chapter_id = Column(String, nullable=True)
    topic_id = Column(String, nullable=True)
    concept_name = Column(String, nullable=False)
    difficulty = Column(Integer, default=1)
    parent_concept_id = Column(String, nullable=True)
    description = Column(Text, nullable=True)


class UserMastery(Base):
    __tablename__ = "user_mastery"
    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(String, nullable=False)
    learner_id = Column(Integer, default=1)
    mastery_level = Column(Float, default=0.0)
    attempts = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    total = Column(Integer, default=0)
    last_practiced = Column(String, nullable=True)
    streak = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("concept_id", "learner_id"),)


# ─── AI / Caching ────────────────────────────────────────────────────────────


class AIContentCache(Base):
    __tablename__ = "ai_content_cache"
    cache_key = Column(String, primary_key=True)
    result_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


# ─── Content Pillars ─────────────────────────────────────────────────────────


class ContentPillar(Base):
    __tablename__ = "content_pillars"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    icon = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    color = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)


class PillarContent(Base):
    __tablename__ = "pillar_content"
    id = Column(Integer, primary_key=True, autoincrement=True)
    pillar_id = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    content_id = Column(String, nullable=False)
    label = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("pillar_id", "content_type", "content_id"),)


# ─── Tutor ───────────────────────────────────────────────────────────────────


class TutorSession(Base):
    __tablename__ = "tutor_sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(String, nullable=False)
    started_at = Column(String, default=datetime.now)
    ended_at = Column(String, nullable=True)
    questions_asked = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    completed = Column(Integer, default=0)

    answers = relationship("TutorAnswer", back_populates="session", lazy="selectin")


class TutorAnswer(Base):
    __tablename__ = "tutor_answers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("tutor_sessions.id"), nullable=False)
    question = Column(Text, nullable=False)
    question_type = Column(String, nullable=True)
    student_answer = Column(Text, nullable=True)
    model_answer = Column(Text, nullable=False)
    self_assessment = Column(String, nullable=True)
    remedial_shown = Column(Integer, default=0)
    asked_at = Column(String, default=datetime.now)

    session = relationship("TutorSession", back_populates="answers", lazy="joined")


# ─── Mock Exam ───────────────────────────────────────────────────────────────


class MockExamPaper(Base):
    __tablename__ = "mock_exam_papers"
    id = Column(String, primary_key=True)
    board_id = Column(String, nullable=False)
    subject_id = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    total_marks = Column(Integer, default=80)
    template = Column(Text, nullable=True)
    section_config = Column(Text, nullable=True)
    created_at = Column(String, default=datetime.now)


class MockExamScore(Base):
    __tablename__ = "mock_exam_scores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String, nullable=False)
    paper_id = Column(String, nullable=False)
    board_id = Column(String, nullable=False)
    subject_id = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    grade = Column(String, nullable=False)
    section_scores = Column(Text, nullable=True)
    answers = Column(Text, nullable=True)
    created_at = Column(String, default=datetime.now)

    __table_args__ = (
        Index("idx_mock_scores_learner", "learner_id"),
        Index("idx_mock_scores_board", "board_id", "subject_id"),
    )


# ─── Monitoring ──────────────────────────────────────────────────────────────


class MonitoringPin(Base):
    __tablename__ = "monitoring_pins"
    pin = Column(String, primary_key=True)
    learner_id = Column(Integer, default=1)
    created_at = Column(String, default=datetime.now)
    expires_at = Column(String, nullable=True)
    is_active = Column(Integer, default=1)


# ─── Schema version tracking ─────────────────────────────────────────────────

SCHEMA_VERSION = "3.0"
ALL_MODELS = [
    Board, Subject, Book, Chapter, Topic, Chunk, Problem, ContentMeta,
    Learner, Session, XPEvent, LearningProgress, LifelineLog,
    DailyChallenge, ConceptView,
    Badge, LearnerBadge, ReviewSchedule,
    KnowledgeGraph, UserMastery,
    AIContentCache,
    ContentPillar, PillarContent,
    TutorSession, TutorAnswer,
    MockExamPaper, MockExamScore,
    MonitoringPin,
]
