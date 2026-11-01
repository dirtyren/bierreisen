FROM nginx:1.29-alpine

# Plain static site: the repo root IS the web root.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY . /usr/share/nginx/html

EXPOSE 80
