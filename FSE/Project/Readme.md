# SmartEdu

An AI-powered, multi-role educational platform. Teachers can create courses and upload YouTube lessons, while students can enroll, learn, and test their knowledge with AI-generated quizzes and summaries.

## Features

* **Multi-Role Access**: Separate dashboards for Teachers and Students.
* **Course Management**: Teachers can create, manage, and delete courses.
* **Student Enrollment**: Students can browse available courses and enroll to track their progress.
* **AI-Powered Summaries**: Automatically generates study summaries from YouTube lecture transcripts using n8n and Gemini 1.5 Pro.
* **Interactive AI Quizzes**: Generates fresh 5-question quizzes based on lesson materials using Gemini.
* **Progress Tracking**: Tracks student completion percentages and quiz scores.
* **Lesson Materials**: Teachers can upload notes, slides, and links for each lesson.

## Tech Stack

* **Backend**: Python, Flask, Flask-JWT-Extended, SQLAlchemy
* **Database**: MySQL
* **Frontend**: Vanilla HTML/CSS/JavaScript
* **AI Pipeline**: n8n, Google Gemini API

## Setup Instructions

### 1. Prerequisites

* Python 3.8+
* MySQL Server
* Node.js & npm (for n8n)

### 2. Backend Setup

1. Create and activate a virtual environment:
`python -m venv venv`
`.\venv\Scripts\activate`
2. Install required packages:
`pip install Flask Flask-SQLAlchemy Flask-JWT-Extended Flask-CORS PyMySQL bcrypt requests`
3. Configure your MySQL database credentials in the backend (via `.env` or `config.py`).
4. Run the provided `cleanup.sql` to initialize/reset your database tables:
`mysql -u root -p smartedu < cleanup.sql`
5. Start the Flask server (runs on port 5000):
`python app.py`

### 3. Frontend Setup

1. Open a new terminal in the project root folder.
2. Start Python's built-in local HTTP server:
`python -m http.server 8000`
3. Open `http://localhost:8000` in your web browser.

### 4. AI Pipeline Setup (n8n)

1. Start your local n8n instance:
`npx n8n`
2. Open n8n in your browser (`http://localhost:5678`).
3. Import your SmartEdu workflow (YouTube Transcript -> Gemini Summary).
4. Ensure the workflow is toggled to **Active** so it can catch incoming webhook triggers from the Flask backend.

## Architecture & Routing

* `app.py`: Main Flask application entry point.
* `models.py`: SQLAlchemy database schemas.
* `routes/`: Modular Blueprints for API endpoints.
* `index.html`: Single-page application frontend.
* `cleanup.sql`: Database reset script.
