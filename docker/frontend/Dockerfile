FROM python:2.7

WORKDIR /app
COPY . /app/

RUN apt-get -y install default-libmysqlclient-dev

# Install dependencies.
RUN pip install -r /app/requirements.txt
RUN pip install -r /app/dev_requirements.txt
RUN pip install mysqlclient==1.4.1

RUN mv example_app.yaml app.yaml

EXPOSE 8080/tcp

USER nobody:nogroup
CMD ["bash", "/app/run.sh"]