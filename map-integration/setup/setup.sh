#! /bin/bash

psql < setup.sql && python import_macrostrat.py
