requirements:
	poetry export --without-hashes -f requirements.txt > requirements.txt

docker: requirements
	docker build -t jakefromspace/crabber . \
	&& \
	docker push jakefromspace/crabber
