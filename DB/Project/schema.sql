--  SmartEdu — MySQL Database Schema
--  Run: mysql -u root -p smartedu < schema.sql

CREATE DATABASE IF NOT EXISTS smartedu
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE smartedu;

-- 1. Users
CREATE TABLE Users (
    id          INT          NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(150) NOT NULL,
    password    VARCHAR(255) NOT NULL,           -- bcrypt hash
    role        ENUM('teacher', 'student') NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB;


-- 2. Courses 
CREATE TABLE Courses (
    id          INT          NOT NULL AUTO_INCREMENT,
    teacher_id  INT          NOT NULL,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT fk_courses_teacher
        FOREIGN KEY (teacher_id) REFERENCES Users(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_courses_teacher (teacher_id)
) ENGINE=InnoDB;


-- 3. Enrollments 
--  Junction table: which students are in which courses
CREATE TABLE Enrollments (
    id           INT      NOT NULL AUTO_INCREMENT,
    student_id   INT      NOT NULL,
    course_id    INT      NOT NULL,
    enrolled_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_enrollment (student_id, course_id),
    CONSTRAINT fk_enroll_student
        FOREIGN KEY (student_id) REFERENCES Users(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_enroll_course
        FOREIGN KEY (course_id) REFERENCES Courses(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_enroll_course (course_id)
) ENGINE=InnoDB;


--4. Lessons 
CREATE TABLE Lessons (
    id          INT          NOT NULL AUTO_INCREMENT,
    course_id   INT          NOT NULL,
    title       VARCHAR(200) NOT NULL,
    youtube_url VARCHAR(500) NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT fk_lessons_course
        FOREIGN KEY (course_id) REFERENCES Courses(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_lessons_course (course_id)
) ENGINE=InnoDB;


-- 5. AI_Summaries
CREATE TABLE AI_Summaries (
    id            INT      NOT NULL AUTO_INCREMENT,
    lesson_id     INT      NOT NULL,
    summary_text  TEXT     NOT NULL,
    generated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                           ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_summary_lesson (lesson_id),    -- one summary per lesson
    CONSTRAINT fk_summary_lesson
        FOREIGN KEY (lesson_id) REFERENCES Lessons(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;


-- 6. Progress_Tracking
CREATE TABLE Progress_Tracking (
    id          INT      NOT NULL AUTO_INCREMENT,
    student_id  INT      NOT NULL,
    lesson_id   INT      NOT NULL,
    status      ENUM('not-started', 'in-progress', 'completed')
                NOT NULL DEFAULT 'not-started',
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                         ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_progress (student_id, lesson_id),
    CONSTRAINT fk_progress_student
        FOREIGN KEY (student_id) REFERENCES Users(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_progress_lesson
        FOREIGN KEY (lesson_id) REFERENCES Lessons(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_progress_lesson (lesson_id),
    INDEX idx_progress_status (student_id, status)
) ENGINE=InnoDB;



--  SEED DATA  (for demo)


-- Passwords are "password123" — bcrypt hash (cost 12)
INSERT INTO Users (name, email, password, role) VALUES
  ('Dr. Sarah Ahmed',  'sarah@smartedu.com',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMlJbekRSU7zMGUGDrGi6/v2yy', 'teacher'),
  ('Prof. Omar Shaikh','omar@smartedu.com',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMlJbekRSU7zMGUGDrGi6/v2yy', 'teacher'),
  ('Ali Hassan',       'ali@smartedu.com',    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMlJbekRSU7zMGUGDrGi6/v2yy', 'student'),
  ('Fatima Khan',      'fatima@smartedu.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMlJbekRSU7zMGUGDrGi6/v2yy', 'student');

INSERT INTO Courses (teacher_id, title, description) VALUES
  (1, 'CS101 — Intro to Computer Science', 'Fundamentals of programming and computational thinking.'),
  (1, 'CS201 — Data Structures & Algorithms', 'Arrays, linked lists, trees, sorting, and graph algorithms.'),
  (2, 'CS301 — Web Development', 'HTML, CSS, JavaScript, REST APIs, and deployment basics.');

INSERT INTO Enrollments (student_id, course_id) VALUES
  (3, 1), (3, 2),
  (4, 1), (4, 3);

INSERT INTO Lessons (course_id, title, youtube_url) VALUES
  (1, 'What is an Algorithm?',        'https://www.youtube.com/watch?v=6hfOvs8pY1k'),
  (1, 'Variables and Data Types',     'https://www.youtube.com/watch?v=8mAITcNt710'),
  (1, 'Control Flow: If/Else & Loops','https://www.youtube.com/watch?v=eSYeHlwDCNA'),
  (2, 'Big-O Notation Explained',     'https://www.youtube.com/watch?v=Mo4vesaut8g'),
  (2, 'Linked Lists from Scratch',    'https://www.youtube.com/watch?v=njTh_OwMljA');

INSERT INTO AI_Summaries (lesson_id, summary_text) VALUES
  (1, 'An algorithm is a finite sequence of well-defined steps for solving a problem. Core properties: definiteness, finiteness, and effectiveness. Time complexity is measured with Big-O notation. Key paradigms include divide-and-conquer, dynamic programming, and greedy algorithms.'),
  (2, 'Variables are named memory locations that store typed data. Primitive types include int, float, bool, and char. Scope (local vs global) and mutability (const vs var) are essential concepts. Type coercion differs between statically and dynamically typed languages.'),
  (3, 'Control flow determines statement execution order. Conditionals (if/else, switch) select paths; loops (for, while, do-while) repeat blocks. break and continue alter loop behaviour. Short-circuit evaluation optimises logical expressions and prevents null errors.');

INSERT INTO Progress_Tracking (student_id, lesson_id, status) VALUES
  (3, 1, 'completed'),
  (3, 2, 'in-progress'),
  (3, 3, 'not-started'),
  (4, 1, 'completed');


--  SAMPLE COMPLEX QUERIES 
-- Q1: Student dashboard — name + course + lesson + summary + status
-- (4-table JOIN)
SELECT
    u.name                  AS student_name,
    c.title                 AS course_title,
    l.title                 AS lesson_title,
    ai.summary_text         AS ai_summary,
    COALESCE(pt.status, 'not-started') AS progress_status
FROM Users u
JOIN Enrollments e    ON e.student_id = u.id
JOIN Courses     c    ON c.id         = e.course_id
JOIN Lessons     l    ON l.course_id  = c.id
LEFT JOIN AI_Summaries    ai ON ai.lesson_id  = l.id
LEFT JOIN Progress_Tracking pt ON pt.lesson_id  = l.id AND pt.student_id = u.id
WHERE u.id = 3
ORDER BY c.title, l.created_at;


-- Q2: Teacher overview — each lesson's summary status and student completion count
SELECT
    l.title                              AS lesson_title,
    IF(ai.id IS NOT NULL, 'Yes', 'No')  AS has_ai_summary,
    COUNT(pt.id)                         AS students_started,
    SUM(pt.status = 'completed')         AS students_completed
FROM Lessons l
JOIN Courses c         ON c.id       = l.course_id
LEFT JOIN AI_Summaries ai ON ai.lesson_id = l.id
LEFT JOIN Progress_Tracking pt ON pt.lesson_id = l.id
WHERE c.teacher_id = 1
GROUP BY l.id
ORDER BY l.created_at;


-- Q3: Completion rate per course (aggregate)
SELECT
    c.title                                         AS course_title,
    COUNT(DISTINCT l.id)                            AS total_lessons,
    COUNT(DISTINCT CASE WHEN pt.status = 'completed' THEN pt.id END)
                                                    AS completed_by_student,
    ROUND(
      COUNT(DISTINCT CASE WHEN pt.status = 'completed' THEN pt.id END)
      / COUNT(DISTINCT l.id) * 100, 1
    )                                               AS completion_pct
FROM Courses c
JOIN Lessons l           ON l.course_id  = c.id
LEFT JOIN Progress_Tracking pt ON pt.lesson_id = l.id AND pt.student_id = 3
GROUP BY c.id
ORDER BY completion_pct DESC;
