requirements:
	poetry export --without-hashes -f requirements.txt > requirements.txt

docker:
	docker build -t jakefromspace/crabber . \
	&& \
	docker push jakefromspace/crabber
