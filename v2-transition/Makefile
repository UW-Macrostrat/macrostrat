# `mono` is our local CLI for managing a mono-repo,
# provided by macrostrat.packaging_tools
install:
	poetry run mono install

install-self:
	curl -sSL https://install.python-poetry.org | python3 -
	pip3 install ansible
	ansible-galaxy collection install community.docker

install-control-scripts:
	sudo ln -sf $(shell pwd)/bin/strat /usr/local/bin
	sudo ln -sf $(shell pwd)/bin/macrostrat /usr/local/bin/macrostrat
	sudo ln -sf $(shell pwd)/bin/macrostrat-maps /usr/local/bin/macrostrat-maps
