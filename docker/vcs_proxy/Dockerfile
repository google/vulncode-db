FROM python:3.7

RUN mkdir -p /proxy/cert
RUN mkdir -p /proxy/vulnerable_code
RUN mkdir -p /proxy/cache
RUN touch /proxy/vcs_error.log

WORKDIR /proxy
VOLUME /proxy/cert

COPY vcs_requirements.txt /proxy
RUN pip install -r vcs_requirements.txt

COPY example_vcs_proxy.yaml /proxy/vcs_proxy.yaml
COPY lib /proxy/lib
COPY app /proxy/app
COPY cfg.py /proxy
COPY gce_vcs_proxy.py /proxy

EXPOSE 8088/tcp


RUN chown -R nobody:nogroup /proxy/*
USER nobody:nogroup
# CMD ["/usr/local/bin/python", "-m", "/proxy/gce_vcs_proxy.py"]
# Address weird werkzeug bug ("Restarting with stat" + can't import yaml module) with -m parameter.
CMD ["/usr/local/bin/python", "-m", "gce_vcs_proxy"]
