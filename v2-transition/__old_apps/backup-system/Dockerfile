# Copy databases from a remote host to the local host
# Based on https://github.com/cagataygurturk/docker-ssh-tunnel
FROM alpine:3.15

RUN apk add --update openssh-client postgresql15-client pv && rm -rf /var/cache/apk/*

CMD rm -rf /root/.ssh && mkdir /root/.ssh && cp -R /root/ssh/* /root/.ssh/ && chmod -R 600 /root/.ssh/* && \
  ssh \
  $SSH_DEBUG \
  -o StrictHostKeyChecking=no \
  -N $TUNNEL_HOST \
  -L *:$LOCAL_PORT:$REMOTE_HOST:$REMOTE_PORT \
  && while true; do sleep 30; done;
EXPOSE 1-65535

