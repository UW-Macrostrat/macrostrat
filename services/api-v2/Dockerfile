# 
# Paleomacro project - Macrostrat API image
# 
# The image 'paleomacro_msapi_preload' is built from the file 'Dockerfile-preload'
# in this directory. You can pull the latest version of that image from the remote
# container repository associated with this project using the command 'pbdb pull mariadb'.
# Alternatively, you can build locally it using the command 'pbdb build preload mariadb'.
# See the file Dockerfile-preload for more information.
# 
# Once you have the preload image, you can build the container image using the command
# 'macrostrat build msapi'.

FROM paleomacro_msapi_preload

ENV LANG=en_US.UTF-8

# To build this image with a proper timezone setting, use --build-arg TZ=xxx
# where xxx specifies the timezone in which the server is located, for example
# "America/Chicago". The 'pbdb build' command will do this automatically. If no
# such argument is given the container will default to UTC, with no local time
# available.

ARG TZ=Etc/UTC

ENV TZ=$TZ

RUN sh -c "cp /usr/share/zoneinfo/$TZ /etc/localtime" && echo "$TZ" > /etc/timezone

# Copy in files that specify the applications for our installation.

WORKDIR /var/paleomacro/msapi

COPY msapi /var/paleomacro/msapi

COPY tileserver /var/paleomacro/tileserver

ENV NPM_CONFIG_LOGLEVEL warn

# RUN npm install --production

EXPOSE 5000 5500 5050 5555

CMD [ "pm2-runtime", "start", "ecosystem.yml" ]

LABEL maintainer="mmcclenn@geology.wisc.edu"
LABEL description="Paleomacro project - Macrostrat API container image"

