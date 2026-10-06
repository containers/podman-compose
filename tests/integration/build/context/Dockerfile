FROM busybox
RUN mkdir -p /var/www/html/ && echo "web1-test-content" > /var/www/html/index.txt
CMD ["busybox", "httpd", "-f", "-p", "80", "-h", "/var/www/html"]
