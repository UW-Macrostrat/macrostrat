DROP TYPE IF EXISTS measurement_class CASCADE;
ALTER TYPE measurement_class_new RENAME TO measurement_class;

DROP TYPE IF EXISTS measurement_type CASCADE;
ALTER TYPE measurement_class_new RENAME TO measurement_type;
