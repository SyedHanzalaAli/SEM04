-- ============================================================
--  SmartEdu v2 — Additional Tables
--  Run AFTER the original schema.sql:
--  mysql -u root -p smartedu < schema_v2.sql
-- ============================================================

USE smartedu;

-- ── 7. Lesson_Materials ───────────────────────────────────────────────────
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


-- ── 8. Quizzes ───────────────────────────────────────────────────────────
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


-- ── 9. Quiz_Questions ────────────────────────────────────────────────────
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


-- ============================================================
--  SAMPLE COMPLEX QUERIES — Quiz & Materials (for DBS rubric)
-- ============================================================

-- Q4: Student quiz history — all attempts with score and lesson title
SELECT
    q.id                                  AS quiz_id,
    l.title                               AS lesson_title,
    q.score                               AS score,
    q.total_questions                     AS total,
    ROUND(q.score / q.total_questions * 100, 0) AS pct,
    q.created_at                          AS taken_at
FROM Quizzes q
JOIN Lessons l ON l.id = q.lesson_id
WHERE q.student_id = 3
  AND q.submitted  = 1
ORDER BY q.created_at DESC;


-- Q5: Best score per lesson per student (aggregate)
SELECT
    l.title                       AS lesson_title,
    MAX(q.score)                  AS best_score,
    COUNT(q.id)                   AS attempts,
    q.total_questions             AS out_of
FROM Quizzes q
JOIN Lessons l ON l.id = q.lesson_id
WHERE q.student_id = 3 AND q.submitted = 1
GROUP BY q.lesson_id
ORDER BY best_score DESC;


-- Q6: Teacher materials per lesson
SELECT
    l.title             AS lesson_title,
    lm.title            AS material_title,
    lm.material_type,
    lm.created_at
FROM Lesson_Materials lm
JOIN Lessons l ON l.id = lm.lesson_id
WHERE lm.teacher_id = 1
ORDER BY l.id, lm.created_at;
