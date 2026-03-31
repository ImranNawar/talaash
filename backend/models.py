"""
models.py - all Pydantic models for Talaash.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, field_validator


# Phase 1 input

class UserInput(BaseModel):
    research_interests: str
    technical_skills: str
    academic_level: str          # Undergrad / Master's / PhD / Postdoc / Faculty
    goal: str                    # Join a lab / Collaborate / Apply for PhD / Find internship
    keywords: Optional[str] = None
    preferred_region: Optional[str] = None   # comma-separated / "Global"


# Phase 4 extracted schema
class Publication(BaseModel):
    title: str
    year: int


class LabProfile(BaseModel):
    pi_name:              Optional[str]  = None
    co_pis:               list[str]      = []
    university:           Optional[str]  = None
    department:           Optional[str]  = None
    lab_name:             Optional[str]  = None
    research_areas:       list[str]      = []
    current_projects:     list[str]      = []
    methods_used:         list[str]      = []
    recent_publications:  list[Publication] = []
    lab_url:              str            = ""
    contact_email:        Optional[str]  = None
    github_url:           Optional[str]  = None
    is_accepting_students: Optional[bool] = None
    student_requirements: Optional[str]  = None

    @field_validator("co_pis", "research_areas", "current_projects", "methods_used", mode="before")
    @classmethod
    def coerce_list(cls, v):
        if v is None:
            return []
        return v

    @field_validator("recent_publications", mode="before")
    @classmethod
    def coerce_pubs(cls, v):
        if v is None:
            return []
        return v


# Phase 6 / 7 result
class MatchResult(BaseModel):
    profile:              LabProfile
    final_score:          float          # 0–100, composite; shown to user
    match_reasons:        list[str]      = []
    gaps:                 list[str]      = []
    has_recent_publication: bool         = False
    # internal - NOT forwarded to frontend
    _cosine_similarity:   float          = 0.0


class SearchResponse(BaseModel):
    results: list[MatchResult]
    total_candidates: int
    phases_completed: int


# SSE progress event
class PhaseEvent(BaseModel):
    phase: int          # 1-7
    label: str
    status: str         # "running" | "done" | "error"
    detail: Optional[str] = None
