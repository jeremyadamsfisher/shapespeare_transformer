.PHONY: help
DOCKER_IMG=jeremyadamsfisher1123/shakespeare-gpt:$(shell bump-my-version show current_version)
CONDA=micromamba

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

bump:  ## bump patch version
	@bump-my-version bump patch

nuke:  ## remove current training environment
	@$(CONDA) remove -n shakespeare --all

bootstrap:  ## install training environment
	@conda-lock install --micromamba conda-linux-64.lock --name shakespeare

bootstrap_mac:  ## install training environment (mac)
	@conda-lock install --micromamba conda-osx-arm64.lock --name shakespeare

lint:  ## clean up the source code
	@isort .
	@black .

docker_build:  ## build the docker image
	@docker build -t $(DOCKER_IMG) .

docker_push:  ## push the docker image
	@docker push $(DOCKER_IMG) 

docker_poke: docker_build  ## run interactive docker shell
	@docker run \
		-e TOKENIZERS_PARALLELISM=false \
		-e "PYTHONPATH=." \
		-e "WANDB_AUTH=$$(base64 < ~/.netrc)" \
		--gpus "all" \
		--mount "type=bind,src=$(PWD),target=/app" \
		--rm -ti \
		$(DOCKER_IMG) \
		bash


lock:   ## lock the conda env
	@conda-lock lock --kind explicit --micromamba -f env.cuda.yml -f env.yml -p linux-64
	@conda-lock lock --kind explicit --micromamba -f env.yml -p osx-arm64

test:  ## run tests
	@PYTHONPATH=. pytest -vv

run:  ## run the training program
	@TOKENIZERS_PARALLELISM=false \
	 PYTHONPATH=. \
	 	$(CONDA) run -n shakespeare python -O gpt/cli.py train $(OPT)

rm_dataset:  ## remove the cached dataset
	@rm -rf wikipedia_ds

docker_train: docker_build  ## train on docker
	@docker run \
		-e TOKENIZERS_PARALLELISM=false \
		-e PYTHONPATH=. \
		-e "WANDB_AUTH=$$(base64 < ~/.netrc)" \
		--gpus "all" \
		--mount "type=bind,src=$(PWD),target=/app" \
		--rm -ti \
		$(DOCKER_IMG) \
		python -O gpt/cli.py train $(OPT)