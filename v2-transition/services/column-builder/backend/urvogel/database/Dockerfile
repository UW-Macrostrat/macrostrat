FROM postgis/postgis:14-3.1

## install pgjwt extension in image
RUN apt-get update && apt-get install -y make git

RUN git clone https://github.com/michelp/pgjwt && cd pgjwt && make install
