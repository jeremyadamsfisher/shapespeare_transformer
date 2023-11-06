import re

import typer

app = typer.Typer(pretty_exceptions_enable=False)


def check_for_repo_versioned_without_uncommited_changes():
    """If the current commit has unstaged/uncommited changes or lacks a version
    tag, throw an exception."""
    import git

    repo = git.Repo(search_parent_directories=True)

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


@app.command()
def train(
    config: str, log_periodicity: int = 100, dirty: bool = False, profile: bool = False
):
    # import here to avoid doing so for --help ingress
    from gpt import config as C
    from gpt.model import Gpt
    from gpt.train import train as train_
    from gpt.wikipedia import WikipediaDataModule

    if dirty is False:
        check_for_repo_versioned_without_uncommited_changes()

    try:
        model_config = {
            "baby": C.gpt_baby,
            "small": C.gpt3_small,
            "small_char": C.gpt3_small_char,
            "mini_v0": C.gpt_mini_v0,
            "mini_v1": C.gpt_mini_v1,
        }[config.replace("-", "_").lower()]
    except KeyError:
        print(f"Unknown config: {config}")
        return

    dm = WikipediaDataModule(model_config, profile=profile)
    model = Gpt(model_config)

    train_(model, model_config, dm, log_periodicity, profile, silent=dirty)


if __name__ == "__main__":
    app()
