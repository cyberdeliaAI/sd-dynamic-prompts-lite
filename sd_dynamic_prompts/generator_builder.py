from __future__ import annotations

import logging

from dynamicprompts.generators import (
    BatchedCombinatorialPromptGenerator,
    CombinatorialPromptGenerator,
    DummyGenerator,
    PromptGenerator,
    RandomPromptGenerator,
)
from dynamicprompts.parser.parse import default_parser_config

from sd_dynamic_prompts.frozenprompt_generator import FrozenPromptGenerator

logger = logging.getLogger(__name__)


class GeneratorBuilder:
    def __init__(
        self,
        wildcard_manager,
        parser_config=default_parser_config,
        ignore_whitespace=False,
    ):
        self._wildcard_manager = wildcard_manager

        self._is_dummy = False
        self._should_freeze_prompt = False
        self._is_combinatorial = False

        self._combinatorial_batches = 1
        self._ignore_whitespace = ignore_whitespace
        self._unlink_seed_from_prompt = False
        self._seed = -1
        self._parser_config = parser_config

    def set_is_dummy(self, is_dummy=True):
        self._is_dummy = is_dummy
        return self

    def set_is_combinatorial(self, is_combinatorial=True, combinatorial_batches=1):
        self._is_combinatorial = is_combinatorial
        self._combinatorial_batches = combinatorial_batches
        return self

    def set_unlink_seed_from_prompt(self, unlink_seed_from_prompt=True):
        self._unlink_seed_from_prompt = unlink_seed_from_prompt
        return self

    def set_seed(self, seed):
        self._seed = seed
        return self

    def set_freeze_prompt(self, should_freeze: bool):
        self._should_freeze_prompt = should_freeze
        return self

    def create_generator(self) -> PromptGenerator:
        if self._is_dummy:
            return DummyGenerator()

        generator = self._create_basic_generator()

        if self._should_freeze_prompt:
            generator = FrozenPromptGenerator(generator)

        return generator

    def _create_basic_generator(self) -> PromptGenerator:
        if self._is_combinatorial:
            prompt_generator = CombinatorialPromptGenerator(
                self._wildcard_manager,
                parser_config=self._parser_config,
                ignore_whitespace=self._ignore_whitespace,
            )
            return BatchedCombinatorialPromptGenerator(
                prompt_generator,
                batches=self._combinatorial_batches,
            )
        return RandomPromptGenerator(
            self._wildcard_manager,
            seed=self._seed,
            parser_config=self._parser_config,
            unlink_seed_from_prompt=self._unlink_seed_from_prompt,
            ignore_whitespace=self._ignore_whitespace,
        )
