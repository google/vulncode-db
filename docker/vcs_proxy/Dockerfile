FROM python:3.7

RUN mkdir -p /proxy/cert
RUN mkdir -p /proxy/vulnerable_code && chown nobody:nogroup /proxy/vulnerable_code
RUN mkdir -p /proxy/cache && chown nobody:nogroup /proxy/cache
RUN touch /proxy/vcs_error.log && chown nobody:nogroup /proxy/vcs_error.log

WORKDIR /proxy
VOLUME /proxy/cert

COPY vcs_requirements.txt /proxy
RUN pip install -r vcs_requirements.txt
# manually install for now
RUN pip install gitpython

COPY lib /proxy/lib
COPY app /proxy/app
COPY cfg.py /proxy
COPY gce_vcs_proxy.py /proxy

EXPOSE 8080/tcp

USER nobody:nogroup

CMD ["/usr/local/bin/python", "/proxy/gce_vcs_proxy.py"]
