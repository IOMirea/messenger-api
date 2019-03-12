server {
	listen 443 ssl;

	server_name iomirea.ml www.iomirea.ml;

	ssl_certificate /etc/letsencrypt/live/iomirea.ml/fullchain.pem;
	ssl_certificate_key /etc/letsencrypt/live/iomirea.ml/privkey.pem;
	include /etc/letsencrypt/options-ssl-nginx.conf;
	ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

	location / {
		proxy_set_header Host             $http_host;
		proxy_set_header X-Forwarded-For  $proxy_add_x_forwarded_for;

		proxy_redirect   off;
		proxy_buffering  off;

		proxy_pass http://iomirea;

		# redirect requests from /api/* to the latest API endpoint /api/v0/*
		rewrite ^/api/((?!v\d+).*)$ /api/v0/$1 permanent;
	}
}


server {
    if ($host = www.iomirea.ml) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    if ($host = iomirea.ml) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


	listen 80;

	server_name iomirea.ml www.iomirea.ml;
    return 404; # managed by Certbot
}
