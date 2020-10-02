# Based upon Dockerfile in version c2bcc418e037d6bc2d6b47c2d782900126b4f884:
# https://github.com/kotakanbe/go-cve-dictionary/blob/c2bcc418e037d6bc2d6b47c2d782900126b4f884/Dockerfile
FROM golang:alpine as builder
RUN apk add --no-cache \
    git \
    make \
    gcc \
    musl-dev

ENV REPOSITORY github.com/kotakanbe/go-cve-dictionary
COPY . $GOPATH/src/$REPOSITORY
RUN cd $GOPATH/src/$REPOSITORY && make install
# && sed -i 's/static.nvd.nist.gov/nvd.nist.gov/' nvd/nvd.go

FROM alpine:3.7
RUN apk add --no-cache perl mysql-client
MAINTAINER hikachan sadayuki-matsuno

ENV LOGDIR /var/log/vuls
ENV WORKDIR /vuls

RUN apk add --no-cache ca-certificates \
    && mkdir -p $WORKDIR $LOGDIR
COPY --from=builder /go/bin/go-cve-dictionary /usr/local/bin/

WORKDIR $WORKDIR
ENV PWD $WORKDIR

