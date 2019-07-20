FROM python:3.7

WORKDIR /app_setup
COPY requirements.txt /app_setup/
COPY vcs_requirements.txt /app_setup/
COPY dev_requirements.txt /app_setup/

RUN apt-get -y install default-libmysqlclient-dev

# Install dependencies.
RUN pip3 install -r /app_setup/requirements.txt
RUN pip3 install -r /app_setup/dev_requirements.txt
RUN pip3 install mysqlclient==1.4.1

# Used as a bind-mount by docker-compose.
WORKDIR /app
EXPOSE 8080/tcp

#USER nobody:nogroup