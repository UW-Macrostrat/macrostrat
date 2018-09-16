DROP TYPE IF EXISTS measurement_class;
ALTER TYPE measurement_class_new RENAME TO measurement_class CASCADE;

DROP TYPE IF EXISTS measurement_type;
ALTER TYPE measurement_class_new RENAME TO measurement_type CASCADE;
