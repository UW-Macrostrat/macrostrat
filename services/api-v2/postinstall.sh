#! /bin/bash

npm install --prefix ./v1 ./v1
npm install --prefix ./v2 ./v2
cp v1/credentials.example.js v1/credentials.js
cp v2/credentials.example.js v2/credentials.js
