FROM python:3.7

WORKDIR /app_setup
COPY deps/common_requirements.txt /app_setup/
COPY deps/requirements.txt /app_setup/
COPY deps/vcs_requirements.txt /app_setup/
COPY deps/dev_requirements.txt /app_setup/


RUN apt-get -y install default-libmysqlclient-dev

# Install dependencies.
RUN pip3 install -r /app_setup/requirements.txt
RUN pip3 install -r /app_setup/vcs_requirements.txt
RUN pip3 install -r /app_setup/dev_requirements.txt

# Used as a bind-mount by docker-compose.
WORKDIR /app
EXPOSE 8080/tcp

#USER nobody:nogroup