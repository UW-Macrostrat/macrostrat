install:
	pip3 install ansible
	ansible-galaxy collection install community.docker

install-control-scripts:
	sudo ln -sf $(shell pwd)/bin/strat /usr/local/bin
	sudo ln -sf $(shell pwd)/bin/macrostrat /usr/local/bin/macrostrat
	sudo ln -sf $(shell pwd)/bin/macrostrat-maps /usr/local/bin/macrostrat-maps