server {
	listen 80;
	server_name "";

	return 307 $scheme://iomirea.ml$request_uri;
}

server {
	listen 443 ssl;

	server_name iomirea.ml www.iomirea.ml;

	ssl_certificate /etc/letsencrypt/live/iomirea.ml/fullchain.pem;
	ssl_certificate_key /etc/letsencrypt/live/iomirea.ml/privkey.pem;
	include /etc/letsencrypt/options-ssl-nginx.conf;
	ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

	location /api/ {
		include proxy_params;

		# redirect requests from /api/* to the latest API endpoint /api/v0/*
		rewrite ^/api/((?!v\d+).*)$ /api/v0/$1 last;
	}

	location /api/oauth2 {
		include proxy_params;
	}

	location / {
                root /www/static;
                try_files $uri @backend;
	}

	location @backend {
		include proxy_params;
	}
}


server {
	if ($host = www.iomirea.ml) {
		return 307 https://$host$request_uri;
	} # managed by Certbot


	if ($host = iomirea.ml) {
		return 307 https://$host$request_uri;
	} # managed by Certbot


	listen 80;

	server_name iomirea.ml www.iomirea.ml;
	return 404; # managed by Certbot
}
