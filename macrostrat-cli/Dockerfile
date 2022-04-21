FROM python:3.9

WORKDIR /code

COPY ./setup.py ./setup.cfg ./README.md /code/
COPY ./macrostrat_cli/__init__.py /code/macrostrat_cli/

RUN python setup.py egg_info && pip install -r *.egg-info/requires.txt

COPY ./ /code/

RUN pip install -e .


CMD ["bash"]
