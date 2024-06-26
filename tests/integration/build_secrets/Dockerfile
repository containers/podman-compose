FROM busybox

RUN --mount=type=secret,required=true,id=build_secret \
    ls -l /run/secrets/ && cat /run/secrets/build_secret

RUN --mount=type=secret,required=true,id=build_secret,target=/tmp/secret \
    ls -l /run/secrets/ /tmp/ && cat /tmp/secret

CMD [ 'echo', 'nothing here' ]
