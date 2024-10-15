# Base image
FROM alpine:latest

# Install OpenSSH client
RUN apk add openssh

# Test the SSH agents during the build

RUN echo -n "default: " >> /result.log 
RUN --mount=type=ssh ssh-add -L >> /result.log

RUN echo -n "id1: " >> /result.log 
RUN --mount=type=ssh,id=id1 ssh-add -L >> /result.log

RUN echo -n "id2: " >> /result.log 
RUN --mount=type=ssh,id=id2 ssh-add -L >> /result.log
