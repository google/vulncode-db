FROM node:alpine

WORKDIR /app_setup
# Install eslint dependencies.
COPY package.json /app_setup/
RUN npm install
# Make eslint and other utilities available by adjusting the PATH variable.
ENV PATH="/app_setup/node_modules/.bin/:${PATH}"

# Install yapf, plyint and other dependencies.
RUN apk add --no-cache python py-pip bash
RUN pip install yapf futures pylint

WORKDIR /app
