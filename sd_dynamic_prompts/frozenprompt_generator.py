from __future__ import annotations

from dynamicprompts.generators import PromptGenerator


class FrozenPromptGenerator(PromptGenerator):
    """
    When using a variation seed, the prompt shouldn't change between generations.
    This wraps a generator and freezes it so it only generates once.
    """

    def __init__(self, generator: PromptGenerator):
        self._generator = generator

    def generate(self, template: str, count: int = 1, **kwargs) -> list[str]:
        prompts = self._generator.generate(template, 1, **kwargs)
        return prompts * count
