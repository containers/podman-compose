FROM busybox
ARG buildno=1
ARG httpd_port=80
ARG other_variable=not_set
ENV httpd_port ${httpd_port}
ENV other_variable ${other_variable}
RUN mkdir -p /var/www/html/ && \
    echo "ALT buildno=$buildno port=$httpd_port `date -Iseconds`" > /var/www/html/index.txt
CMD httpd -f -p "$httpd_port" -h /var/www/html
