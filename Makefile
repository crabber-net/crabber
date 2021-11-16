requirements:
	poetry lock \
	&& \
	poetry export --without-hashes -f requirements.txt > requirements.txt

docker: requirements
	docker build -t jakefromspace/crabber . \
	&& \
	docker push jakefromspace/crabber

node:
	browserify static/scripts/_node_crabmidi.js > static/scripts/bundle.js
