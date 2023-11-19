"""This script preprocesses wikipedia into a tokenized dataset. It should
be run before training."""

import yaml
from pathlib import Path
import argparse
import multiprocessing as mp
from typing import Callable, Dict, Sequence

from datasets import Dataset, load_dataset
from torch import Tensor
from tqdm import trange

from gpt.tokenizer import CharTokenizer

WIKIPEDIA_URI = "wikipedia"


def tokenize_wikipedia_dataset(
    ds,
    tokenize: Callable[[str], Tensor],
    min_block_size,
):
    """Tokenize a dataset of wikipedia articles. We need to tokenize the articles
    before training because we need to know how many tokens are in each article
    to index into them."""

    def wikipedia_batch_process(batch: Dict[str, Sequence]) -> Dict[str, Sequence]:
        tokens_batch = []
        for text in batch["text"]:
            tokens = tokenize(text)
            if min_block_size <= len(tokens):
                tokens_batch.append(tokens)
        return {"tokens": tokens_batch}

    return ds.map(
        wikipedia_batch_process,
        batched=True,
        remove_columns=["text"],
        num_proc=mp.cpu_count() - 1,
    )


def prepare_data(n_articles, dataset_uri, tokenizer, block_size):
    if tokenizer is not None:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(tokenizer)
    else:
        tokenizer = CharTokenizer()

    if n_articles:
        ds_full = load_dataset(
            "wikipedia", "20220301.en", split="train", streaming=True, cache_dir=Path.cwd() / "dataset_cache"
        )
        texts = []
        iter_ds = iter(ds_full)
        for _ in trange(n_articles, desc="Downloading wikipedia"):
            row = next(iter_ds)
            texts.append(row["text"])
        ds = Dataset.from_dict({"text": texts})
    else:
        ds = load_dataset(WIKIPEDIA_URI, "20220301.en", split="train", cache_dir=Path.cwd() / "dataset_cache")
        ds = ds.select_columns(["text"])

    ds = tokenize_wikipedia_dataset(
        ds,
        tokenize=tokenizer.encode,
        # We need a source block that is at least one token bigger than the
        # context width of the model
        min_block_size=block_size + 1,
    )

    ds = ds.train_test_split(test_size=0.0025)
    ds.save_to_disk(dataset_uri)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-fp", type=str, required=True)
    args = parser.parse_args()
    with open(args.config_fp) as f:
        config = yaml.safe_load(f)
    prepare_data(**config)
