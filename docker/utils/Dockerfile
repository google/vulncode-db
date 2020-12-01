FROM node:alpine

WORKDIR /app_setup
# Install eslint dependencies.
COPY package.json /app_setup/
RUN npm install
# Make eslint and other utilities available by adjusting the PATH variable.
ENV PATH="/app_setup/node_modules/.bin/:${PATH}"

# Install yapf, plyint and other dependencies.
RUN apk add --no-cache python3 bash build-base python3-dev
#RUN python3 -m ensurepip
#RUN pip3 install --upgrade pip
RUN pip3 install black futures pylint bandit mypy sqlalchemy-stubs mypy-extensions marshmallow

WORKDIR /app
