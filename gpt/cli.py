import re

import typer
from loguru import logger

app = typer.Typer(pretty_exceptions_enable=False)


def check_for_repo_versioned_without_uncommited_changes():
    """If the current commit has unstaged/uncommited changes or lacks a version
    tag, throw an exception."""
    import git

    try:
        repo = git.Repo(search_parent_directories=True)
    except git.exc.InvalidGitRepositoryError:
        return False

    if not repo.head.is_valid():
        raise Exception("The current directory is not part of a Git repository.")

    for tag in repo.tags:
        if tag.commit.hexsha == repo.head.commit.hexsha:
            if re.match(r"v\d+\.\d+\.\d+", tag.name):
                break
    else:
        raise Exception("No version tag found in the current commit!")

    if repo.index.diff(None):
        raise Exception("Uncommitted changes!")


def get_model(config):
    from gpt import config as C

    return {
        "baby": C.gpt_baby,
        "small": C.gpt3_small,
        "small_char": C.gpt3_small_char,
        "small_char_one_cycle": C.gpt3_small_char_one_cycle,
        "small_char_one_cycle_v2": C.gpt3_small_char_one_cycle_v2,
        "mini_v0": C.gpt_mini_v0,
        "mini_v1": C.gpt_mini_v1,
    }[config.replace("-", "_").lower()]


@app.command()
def train(
    config: str,
    log_periodicity: int = 100,
    dirty: bool = False,
    profile: bool = False,
    compile: bool = False
):
    # import here to avoid doing so for --help ingress

    from gpt.lightning_module import GptLightning
    from gpt.train import train as train_
    from gpt.wikipedia import WikipediaDataModule

    if dirty is False:
        check_for_repo_versioned_without_uncommited_changes()

    try:
        model_config = get_model(config)
    except KeyError:
        print(f"Unknown config: {config}")
        return

    logger.info("using config: {}", model_config)

    dm = WikipediaDataModule(model_config, profile=profile)
    model = GptLightning(model_config, compile=compile)

    train_(model, model_config, dm, log_periodicity, profile, silent=dirty)


@app.command()
def find_lr(config: str, fname="./lr.png"):
    import pytorch_lightning as L

    from gpt.lightning_module import GptLightning
    from gpt.wikipedia import WikipediaDataModule

    try:
        model_config = get_model(config)
    except KeyError:
        print(f"Unknown config: {config}")
        return

    logger.info("initializing model and tuner")
    trainer = L.Trainer()
    tuner = L.tuner.Tuner(trainer)
    model = GptLightning(model_config, compile=False)
    dm = WikipediaDataModule(model_config, profile=False)
    dm.setup()
    model.train_dataloader = dm.train_dataloader

    logger.info("finding the learning rate")
    lr_finder = tuner.lr_find(model)

    suggested_lr = lr_finder.suggestion()
    logger.info("suggested lr: {}", suggested_lr)

    fig = lr_finder.plot(suggest=True)
    fig.savefig(fname)


if __name__ == "__main__":
    app()
