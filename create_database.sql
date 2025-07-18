-- 1)  Create and switch to UFCStats
DROP DATABASE IF EXISTS UFCStats;
CREATE DATABASE UFCStats
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE UFCStats;

-- 2)  Base tables
CREATE TABLE event (
    event_id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    date       DATE         NOT NULL,
    location   VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE fighter (
    fighter_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    height_in  SMALLINT,
    reach_in   SMALLINT,
    dob        DATE
) ENGINE=InnoDB;

CREATE TABLE referee (
    referee_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(50)  NOT NULL
) ENGINE=InnoDB;

-- 3)  Fight table with ENUMs and FKs
CREATE TABLE fight (
    fight_id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_id          INT UNSIGNED NOT NULL,
    fighter_a_id      INT UNSIGNED NOT NULL,
    fighter_b_id      INT UNSIGNED NOT NULL,
    winner            VARCHAR(10),             -- 'A', 'B', 'Draw', 'NC'
    weight_class      SMALLINT,
    gender            VARCHAR(1) NOT NULL,     -- 'M' or 'F'
    title_fight       BOOLEAN             NOT NULL DEFAULT FALSE,
    method_of_victory VARCHAR(50),
    round_of_victory  TINYINT,
    time_of_victory   INT,                -- seconds
    time_format       TINYINT,            -- 3 or 5
    referee_id        INT UNSIGNED,

    FOREIGN KEY (event_id)     REFERENCES event(event_id)     ON DELETE CASCADE,
    FOREIGN KEY (fighter_a_id) REFERENCES fighter(fighter_id) ON DELETE CASCADE,
    FOREIGN KEY (fighter_b_id) REFERENCES fighter(fighter_id) ON DELETE CASCADE,
    FOREIGN KEY (referee_id)   REFERENCES referee(referee_id) ON DELETE SET NULL,

    INDEX idx_fight_event     (event_id),
    INDEX idx_fight_fighterA  (fighter_a_id),
    INDEX idx_fight_fighterB  (fighter_b_id),
    INDEX idx_fight_referee   (referee_id)
) ENGINE=InnoDB;

-- 4)  Round table
CREATE TABLE round (
    round_id     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    fight_id     INT UNSIGNED NOT NULL,
    round_number TINYINT      NOT NULL,

    FOREIGN KEY (fight_id) REFERENCES fight(fight_id) ON DELETE CASCADE,
    INDEX idx_round_fight (fight_id)
) ENGINE=InnoDB;

-- 5)  RoundStats table
CREATE TABLE roundstats (
    roundstats_id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    round_id                    INT UNSIGNED NOT NULL,
    fighter_id                  INT UNSIGNED NOT NULL,
    knockdowns                  TINYINT,
    non_sig_strikes_landed      SMALLINT,
    non_sig_strikes_attempted   SMALLINT,
    takedowns_landed            SMALLINT,
    takedowns_attempted         SMALLINT,
    submission_attempts         TINYINT,
    reversals                   TINYINT,
    control_time_seconds        INT,
    head_strikes_landed         SMALLINT,
    head_strikes_attempted      SMALLINT,
    body_strikes_landed         SMALLINT,
    body_strikes_attempted      SMALLINT,
    leg_strikes_landed          SMALLINT,
    leg_strikes_attempted       SMALLINT,
    distance_strikes_landed     SMALLINT,
    distance_strikes_attempted  SMALLINT,
    clinch_strikes_landed       SMALLINT,
    clinch_strikes_attempted    SMALLINT,
    ground_strikes_landed       SMALLINT,
    ground_strikes_attempted    SMALLINT,

    UNIQUE KEY uidx_round_fighter (round_id, fighter_id),

    FOREIGN KEY (round_id)    REFERENCES round(round_id)    ON DELETE CASCADE,
    FOREIGN KEY (fighter_id)  REFERENCES fighter(fighter_id) ON DELETE CASCADE,

    INDEX idx_rs_round   (round_id),
    INDEX idx_rs_fighter (fighter_id)
) ENGINE=InnoDB;

