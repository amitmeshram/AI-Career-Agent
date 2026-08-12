# Phase 2 V2 Plan

## Goal

Improve the CV Optimization Report quality without changing the Phase 2 architecture.

## Current Phase 2 V1 Flow

Evaluation Report + CV
↓
Optimization Input JSON
↓
Optimization Draft JSON
↓
Enhanced Draft JSON
↓
DOCX Report

## V2 Enhancements

1. Dynamic ATS Bullet Generation
2. Structured STAR Story Extraction
3. Automatic Keyword Scoring
4. Batch Optimization Report Generation

## Sprint 1: Dynamic ATS Bullet Generation

Replace hardcoded CV bullets with role-specific bullets generated from:

- personalization_plan
- strong_points
- weak_points
- cv_evidence.professional_experience
- cv_evidence.selected_business_impact

## Guardrails

- No invented experience
- No invented certifications
- No invented tools
- No invented achievements
- Every bullet must map to existing CV evidence