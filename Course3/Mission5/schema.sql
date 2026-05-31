-- mars_weather 테이블 생성 스크립트
-- MySQL Workbench 또는 mysql CLI에서 실행

CREATE DATABASE IF NOT EXISTS mars_db
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE mars_db;

CREATE TABLE IF NOT EXISTS mars_weather (
    weather_id INT NOT NULL AUTO_INCREMENT,
    mars_date  DATETIME NOT NULL,
    temp       FLOAT,
    storm      INT,
    PRIMARY KEY (weather_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
