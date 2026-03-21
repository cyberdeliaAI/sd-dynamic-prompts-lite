from __future__ import annotations

import logging
from itertools import cycle, islice, product

from dynamicprompts.generators.promptgenerator import PromptGenerator

logger = logging.getLogger(__name__)


def get_seeds(
    p,
    num_seeds,
    use_fixed_seed,
    is_combinatorial=False,
    combinatorial_batches=1,
) -> tuple[list[int], list[int]]:
    if p.subseed_strength != 0:
        seed = int(p.all_seeds[0])
        subseed = int(p.all_subseeds[0])
    else:
        seed = int(p.seed)
        subseed = int(p.subseed)

    if use_fixed_seed:
        if is_combinatorial:
            all_seeds = []
            all_subseeds = [subseed] * num_seeds
            for i in range(combinatorial_batches):
                all_seeds.extend([seed + i] * (num_seeds // combinatorial_batches))
        else:
            all_seeds = [seed] * num_seeds
            all_subseeds = [subseed] * num_seeds
    else:
        if p.subseed_strength == 0:
            all_seeds = [seed + i for i in range(num_seeds)]
        else:
            all_seeds = [seed] * num_seeds

        all_subseeds = [subseed + i for i in range(num_seeds)]

    return all_seeds, all_subseeds


def should_freeze_prompt(p):
    # When using a variation seed, the prompt shouldn't change between generations
    return p.subseed_strength > 0


def generate_prompts(
    prompt_generator: PromptGenerator,
    negative_prompt_generator: PromptGenerator,
    prompt: str,
    negative_prompt: str | None,
    num_prompts: int,
    seeds: list[int] | None,
) -> tuple[list[str], list[str]]:
    all_prompts = prompt_generator.generate(prompt, num_prompts, seeds=seeds) or [""]

    negative_seeds = seeds if negative_prompt else None

    all_negative_prompts = negative_prompt_generator.generate(
        negative_prompt,
        num_prompts,
        seeds=negative_seeds,
    ) or [""]

    if num_prompts is None:
        return generate_prompt_cross_product(all_prompts, all_negative_prompts)

    return all_prompts, repeat_iterable_to_length(all_negative_prompts, num_prompts)


def generate_prompt_cross_product(
    prompts: list[str],
    negative_prompts: list[str],
) -> tuple[list[str], list[str]]:
    if not (prompts and negative_prompts):
        return [], []

    new_positive_prompts, new_negative_prompts = zip(
        *product(prompts, negative_prompts),
    )
    return list(new_positive_prompts), list(new_negative_prompts)


def repeat_iterable_to_length(iterable, length: int) -> list:
    return list(islice(cycle(iterable), length))
