FROM nginx:alpine
# Copy the maintenance page files to the Nginx web root
COPY src /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
