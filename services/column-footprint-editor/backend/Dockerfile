FROM ghcr.io/davenquinn/geologic-map:latest 

## use https://linuxize.com/post/how-to-install-python-3-9-on-debian-10/
RUN apt update -y \
    && apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libsqlite3-dev libreadline-dev libffi-dev curl libbz2-dev \
    && wget https://www.python.org/ftp/python/3.9.1/Python-3.9.1.tgz \
    && tar -xf Python-3.9.1.tgz \
    && cd Python-3.9.1 && ./configure --enable-optimizations \
    && make -j 2 && make altinstall \
    && update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.9 1 \
    && apt install -y python3-pip

## before running pip we need to change the first line in lab_release
## #!/usr/bin/python3.5 -Es
RUN sed -i "1 s/3/3.5/g" /usr/bin/lsb_release

COPY requirements.txt ./requirements.txt

RUN python3 -m pip install -r ./requirements.txt


COPY . /python_app
RUN ["chmod", "+x", "/python_app/docker-scripts/run"]

ENV GEOLOGIC_MAP_CONFIG=/app/docker-assets/docker-map-config.json

EXPOSE 3006
EXPOSE 8000

#CMD ["cd","/python_app","&&","python3", "__init__.py"]
CMD /python_app/docker-scripts/run
