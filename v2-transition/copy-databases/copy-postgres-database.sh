
# Manage ssh keys in the docker container
rm -rf /root/.ssh
mkdir /root/.ssh
cp -R /root/ssh/* /root/.ssh/
chmod -R 600 /root/.ssh/*

# Set up the SSH tunnel
ssh \
  $SSH_DEBUG \
  -o StrictHostKeyChecking=no \
  -N $TUNNEL_HOST \
  -L *:$LOCAL_PORT:$REMOTE_HOST:$REMOTE_PORT

# Keep the tunnel alive
while true; do sleep 30; done;