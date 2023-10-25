ALTER TABLE lines.tiny RENAME TO lines_tiny;
ALTER TABLE lines.small RENAME TO lines_small;
ALTER TABLE lines.medium RENAME TO lines_medium;
ALTER TABLE lines.large RENAME TO lines_large;

ALTER TABLE lines.tiny SET SCHEMA maps;
ALTER TABLE lines.small SET SCHEMA maps;
ALTER TABLE lines.medium SET SCHEMA maps;
ALTER TABLE lines.large SET SCHEMA maps;

