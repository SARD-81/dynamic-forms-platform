FROM nginx:1.28-alpine
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY validate-proxy.sh /docker-entrypoint.d/05-validate-proxy.sh
RUN chmod +x /docker-entrypoint.d/05-validate-proxy.sh
