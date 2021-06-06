FROM python:3.7

WORKDIR /app_setup
COPY deps/common_requirements.txt /app_setup/
COPY deps/vcs_requirements.txt /app_setup/

RUN pip3 install -r vcs_requirements.txt

# Used as a bind-mount by docker-compose.
WORKDIR /app
EXPOSE 8088/tcp

#RUN chown -R nobody:nogroup /proxy/*
#USER nobody:nogroup
# CMD ["/usr/local/bin/python", "-m", "/proxy/gce_vcs_proxy.py"]
# Address weird werkzeug bug ("Restarting with stat" + can't import yaml module) with -m parameter.
CMD ["/usr/local/bin/python", "-m", "gce_vcs_proxy"]
