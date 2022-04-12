FROM node:14

WORKDIR /app

COPY package.json yarn.lock ./

RUN yarn install --production

COPY ./ ./

CMD yarn run start