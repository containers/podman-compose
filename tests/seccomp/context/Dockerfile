FROM busybox
RUN mkdir -p /var/www/html/ && date -Iseconds > /var/www/html/index.txt
CMD ["busybox", "httpd", "-f", "-p", "80", "-h", "/var/www/html"]
