---
title: The Platform
description: Core concepts of the FAIR academic workflow system
sidebar:
  order: 1
---

This page explains how **FAIR Platform** is organized: users, courses, assignments, submissions, and artifacts.  It gives you a clear mental model of how FAIR works *before* you dive into extensions or advanced features.

FAIR is designed to feel familiar to professors and students, even if they’ve never used an AI-assisted grading tool before.

---

## What The Platform Is

FAIR is a platform where:

- **Professors create courses and assignments**  
- **Students submit work**  
- **FAIR collects the submissions, organizes them, and helps grade them**
- **Orchestrates AI to assist in the assessment process**.

---

## Users

FAIR has two main types of users:

1. **Professors**, who can:
   - Create courses  
   - Add assignments  
   - Configure grading rules or enable extensions  
   - Review or override grades  

2. **Students**, who can:
   - Join a course  
   - Upload work  
   - View feedback and grades  

_Administrators exist for larger deployments, but they are optional._

---

## Courses

A course in FAIR represents a class you teach or participate in. It contains:

- A name (e.g., “Physics II”)
- A roster (students enrolled)
- A list of assignments
- Optional resources or instructions
- The grading configuration for that course

If you use FAIR for research, you might only use courses to organize your experiments, but structuring them as real courses might sometimes be crucial since some extensions will use the course metadata and resources to make better assessments. You can create as many courses as you need.

---

## Assignments

Assignments are the core unit of work in FAIR.

An assignment defines:

- A title (e.g., “Lab Report 3”)
- Instructions for students
- Accepted submission formats (PDF, image, notebook, etc.)
- Deadlines

Assignments can be simple (“upload your report”) or advanced (“Final coding project revision”). You can even create assignments to self-study with AI revisions.

---

## Submissions

A **submission** is anything a student uploads in response to an assignment.

A submission can include:

- PDFs  
- Images / photos of handwritten work  
- Jupyter notebooks  
- ZIP files  
- Videos
- Forms
- Anything else you allow  

Each submission holds one or multiple **artifacts**.

---

## Artifacts

Artifacts are the internal representation of student work or media content in FAIR.

Most artifacts simply represent a file uploaded by a student, but they can also represent:
- Extracted text from images (OCR)  
- Transcriptions from audio or video  
- Parsed content from notebooks or documents  
- Any processed or transformed version of the original submission
- Form responses
- Structured data extracted in your custom format.

An artifact is FAIR’s way of saying:

> “Here is the student’s work, standardized and ready for analysis.”

These allow extensions to process submissions uniformly, regardless of the original format.

---

## Feedback and Grades

After a submission is processed, FAIR produces:

- A numeric or rubric-based grade  
- Comments (manual or generated)  
- Flags or warnings  
- Optional artifacts (like transcriptions or code execution logs)

Ideally, these products would be high-quality AI-generated feedback, but professors can always review and adjust them.

---

## Putting It All Together

Here’s the typical flow:

1. **Professor** creates a course and adds assignments  
2. **Students** upload their submissions  
3. FAIR converts each submission into **artifacts**  
4. FAIR runs any configured **extensions** (optional)  
5. FAIR presents results and **grades**  
6. Students receive **feedback**  
7. Professors can revise or export results  

The platform stays simple if you want it simple, and it becomes powerful if you enable extensions.

---

## Next: Extensions

Now that you know the structure of the platform, learn how to extend FAIR with:

- Plugins
- Workflows  
- Custom grading modules
