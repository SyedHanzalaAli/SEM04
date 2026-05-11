
--  SmartEdu — MySQL Database Schema
--  Run: mysql -u root -p smartedu < schema.sql

CREATE DATABASE IF NOT EXISTS smartedu
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE smartedu;

--1. Users 
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


--2. Courses 
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


--  4. Lessons 
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


--  5. AI_Summaries
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

-- 7. Lesson_Materials 
-- Teachers attach notes, slides, question sheets, links, etc.
CREATE TABLE Lesson_Materials (
    id            INT           NOT NULL AUTO_INCREMENT,
    lesson_id     INT           NOT NULL,
    teacher_id    INT           NOT NULL,
    title         VARCHAR(200)  NOT NULL,
    material_type ENUM('notes','slides','questions','link','other') NOT NULL DEFAULT 'other',
    content       LONGTEXT,                  -- raw text / markdown content
    file_url      VARCHAR(500),              -- external link or future file URL
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT fk_mat_lesson
        FOREIGN KEY (lesson_id)  REFERENCES Lessons(id)  ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_mat_teacher
        FOREIGN KEY (teacher_id) REFERENCES Users(id)    ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_mat_lesson (lesson_id),
    INDEX idx_mat_teacher (teacher_id)
) ENGINE=InnoDB;


-- 8. Quizzes 
-- One row per quiz attempt — a student can take multiple quizzes per lesson
CREATE TABLE Quizzes (
    id              INT      NOT NULL AUTO_INCREMENT,
    lesson_id       INT      NOT NULL,
    student_id      INT      NOT NULL,
    score           INT      NOT NULL DEFAULT 0,
    total_questions INT      NOT NULL DEFAULT 5,
    submitted       TINYINT  NOT NULL DEFAULT 0,     -- 0=in-progress, 1=submitted
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at    DATETIME,

    PRIMARY KEY (id),
    CONSTRAINT fk_quiz_lesson
        FOREIGN KEY (lesson_id)  REFERENCES Lessons(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_quiz_student
        FOREIGN KEY (student_id) REFERENCES Users(id)   ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_quiz_student_lesson (student_id, lesson_id)
) ENGINE=InnoDB;


--  9. Quiz_Questions
-- 5 MCQ questions per quiz, each with 4 options
CREATE TABLE Quiz_Questions (
    id              INT         NOT NULL AUTO_INCREMENT,
    quiz_id         INT         NOT NULL,
    question_no     TINYINT     NOT NULL,               -- 1 to 5
    question_text   TEXT        NOT NULL,
    option_a        VARCHAR(400) NOT NULL,
    option_b        VARCHAR(400) NOT NULL,
    option_c        VARCHAR(400) NOT NULL,
    option_d        VARCHAR(400) NOT NULL,
    correct_option  ENUM('A','B','C','D') NOT NULL,
    student_answer  ENUM('A','B','C','D'),              -- NULL until answered
    is_correct      TINYINT,                            -- NULL until submitted

    PRIMARY KEY (id),
    CONSTRAINT fk_qq_quiz
        FOREIGN KEY (quiz_id) REFERENCES Quizzes(id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE KEY uq_quiz_qno (quiz_id, question_no),
    INDEX idx_qq_quiz (quiz_id)
) ENGINE=InnoDB;

