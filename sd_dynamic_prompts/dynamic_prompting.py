from __future__ import annotations

import logging
import math
from functools import lru_cache
from string import Template

import dynamicprompts
import gradio as gr
import modules.scripts as scripts
from dynamicprompts.generators.promptgenerator import GeneratorException
from dynamicprompts.parser.parse import ParserConfig
from dynamicprompts.wildcards import WildcardManager
from modules.processing import fix_seed
from modules.shared import opts

from sd_dynamic_prompts import __version__, callbacks
from sd_dynamic_prompts.element_ids import make_element_id
from sd_dynamic_prompts.generator_builder import GeneratorBuilder
from sd_dynamic_prompts.helpers import (
    generate_prompts,
    get_seeds,
    repeat_iterable_to_length,
    should_freeze_prompt,
)
from sd_dynamic_prompts.paths import (
    get_extension_base_path,
    get_wildcard_dir,
)
from sd_dynamic_prompts.prompt_writer import PromptWriter

VERSION = __version__

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

is_debug = getattr(opts, "is_debug", False)

if is_debug:
    logger.setLevel(logging.DEBUG)


def _get_effective_prompt(prompts: list[str], prompt: str) -> str:
    return prompts[0] if prompts else prompt


loaded_count = 0


@lru_cache(maxsize=1)
def _get_install_error_message() -> str | None:
    try:
        from sd_dynamic_prompts.version_tools import get_dynamicprompts_install_result

        get_dynamicprompts_install_result().raise_if_incorrect()
    except RuntimeError as rte:
        return str(rte)
    except Exception:
        logger.exception("Failed to get dynamicprompts install result")
    return None


def _get_hr_fix_prompts(
    prompts: list[str],
    original_hr_prompt: str,
    original_prompt: str,
) -> list[str]:
    if original_prompt == original_hr_prompt:
        return list(prompts)
    return repeat_iterable_to_length([original_hr_prompt], len(prompts))


class Script(scripts.Script):
    def __init__(self):
        global loaded_count

        loaded_count += 1

        self._prompt_writer = PromptWriter()
        self._wildcard_manager = WildcardManager(get_wildcard_dir())

        if loaded_count % 2 == 0:
            return

        callbacks.register_prompt_writer(self._prompt_writer)
        callbacks.register_on_infotext_pasted()
        callbacks.register_wildcards_tab(self._wildcard_manager)

    def title(self):
        return f"Dynamic Prompts Lite v{VERSION}"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        install_message = _get_install_error_message()
        correct_lib_version = bool(not install_message)

        with gr.Group(elem_id=make_element_id("dynamic-prompting")):
            title = "Dynamic Prompts Lite"
            if not correct_lib_version:
                title += " [incorrect installation]"
            with gr.Accordion(title, open=False):
                is_enabled = gr.Checkbox(
                    label="Dynamic Prompts enabled",
                    value=correct_lib_version,
                    interactive=correct_lib_version,
                    elem_id=make_element_id("dynamic-prompts-enabled"),
                )

                if not correct_lib_version:
                    gr.HTML(
                        f"""<span class="warning sddp-warning">Dynamic Prompts is not installed correctly</span>.
                        {install_message}""",
                    )

                with gr.Group(visible=correct_lib_version):
                    is_combinatorial = gr.Checkbox(
                        label="Combinatorial generation",
                        value=False,
                        elem_id=make_element_id("is-combinatorial"),
                    )

                    max_generations = gr.Slider(
                        label="Max generations (0 = all combinations - the batch count value is ignored)",
                        minimum=0,
                        maximum=1000,
                        step=1,
                        value=0,
                        elem_id=make_element_id("max-generations"),
                    )

                    combinatorial_batches = gr.Slider(
                        label="Combinatorial batches",
                        minimum=1,
                        maximum=10,
                        step=1,
                        value=1,
                        elem_id=make_element_id("combinatorial-times"),
                    )

                with gr.Group():
                    with gr.Accordion("Advanced options", open=False):
                        gr.HTML(
                            "Some settings have been moved to the settings tab. Find them in the Dynamic Prompts section.",
                        )

                        unlink_seed_from_prompt = gr.Checkbox(
                            label="Unlink seed from prompt",
                            value=False,
                            elem_id=make_element_id("unlink-seed-from-prompt"),
                        )

                        use_fixed_seed = gr.Checkbox(
                            label="Fixed seed",
                            value=False,
                            elem_id=make_element_id("is-fixed-seed"),
                        )

                        gr.Checkbox(
                            label="Write raw prompt to image",
                            value=False,
                            visible=False,
                            elem_id=make_element_id("write-raw-template"),
                        )

                        no_image_generation = gr.Checkbox(
                            label="Don't generate images",
                            value=False,
                            elem_id=make_element_id("no-image-generation"),
                        )

                gr.Checkbox(
                    label="Write prompts to file",
                    value=False,
                    elem_id=make_element_id("write-prompts"),
                    visible=False,
                )

        return [
            is_enabled,
            is_combinatorial,
            combinatorial_batches,
            use_fixed_seed,
            unlink_seed_from_prompt,
            no_image_generation,
            max_generations,
        ]

    def process(
        self,
        p,
        is_enabled: bool,
        is_combinatorial: bool,
        combinatorial_batches: int,
        use_fixed_seed: bool,
        unlink_seed_from_prompt: bool,
        no_image_generation: bool,
        max_generations: int,
    ):
        if not is_enabled:
            logger.debug("Dynamic prompts disabled - exiting")
            return p

        ignore_whitespace = opts.dp_ignore_whitespace

        self._prompt_writer.enabled = opts.dp_write_prompts_to_file
        self._auto_purge_cache = opts.dp_auto_purge_cache
        self._wildcard_manager.dedup_wildcards = not opts.dp_wildcard_manager_no_dedupe
        self._wildcard_manager.sort_wildcards = not opts.dp_wildcard_manager_no_sort
        self._wildcard_manager.shuffle_wildcards = opts.dp_wildcard_manager_shuffle

        parser_config = ParserConfig(
            variant_start=opts.dp_parser_variant_start,
            variant_end=opts.dp_parser_variant_end,
            wildcard_wrap=opts.dp_parser_wildcard_wrap,
        )

        fix_seed(p)

        original_prompt = _get_effective_prompt(p.all_prompts, p.prompt)
        original_negative_prompt = _get_effective_prompt(
            p.all_negative_prompts,
            p.negative_prompt,
        )
        hr_fix_enabled = getattr(p, "enable_hr", False)

        if hr_fix_enabled and hasattr(p, "all_hr_prompts"):
            original_hr_prompt = _get_effective_prompt(p.all_hr_prompts, p.hr_prompt)
            original_negative_hr_prompt = _get_effective_prompt(
                p.all_hr_negative_prompts,
                p.hr_negative_prompt,
            )
        else:
            original_hr_prompt = original_prompt
            original_negative_hr_prompt = original_negative_prompt

        original_seed = p.seed
        num_images = p.n_iter * p.batch_size

        if is_combinatorial:
            if max_generations == 0:
                num_images = None
            else:
                num_images = max_generations

        combinatorial_batches = int(combinatorial_batches)
        if self._auto_purge_cache:
            self._wildcard_manager.clear_cache()

        try:
            logger.debug("Creating generator")

            generator_builder = (
                GeneratorBuilder(
                    self._wildcard_manager,
                    ignore_whitespace=ignore_whitespace,
                    parser_config=parser_config,
                )
                .set_is_combinatorial(is_combinatorial, combinatorial_batches)
                .set_is_dummy(False)
                .set_unlink_seed_from_prompt(unlink_seed_from_prompt)
                .set_seed(original_seed)
                .set_freeze_prompt(should_freeze_prompt(p))
            )

            generator = generator_builder.create_generator()

            all_seeds = None
            if num_images and not unlink_seed_from_prompt:
                p.all_seeds, p.all_subseeds = get_seeds(
                    p,
                    num_images,
                    use_fixed_seed,
                    is_combinatorial,
                    combinatorial_batches,
                )
                all_seeds = p.all_seeds

            all_prompts, all_negative_prompts = generate_prompts(
                prompt_generator=generator,
                negative_prompt_generator=generator,
                prompt=original_prompt,
                negative_prompt=original_negative_prompt,
                num_prompts=num_images,
                seeds=all_seeds,
            )

        except GeneratorException as e:
            logger.exception(e)
            all_prompts = [str(e)]
            all_negative_prompts = [str(e)]

        updated_count = len(all_prompts)
        p.n_iter = math.ceil(updated_count / p.batch_size)

        if num_images != updated_count:
            p.all_seeds, p.all_subseeds = get_seeds(
                p,
                updated_count,
                use_fixed_seed,
                is_combinatorial,
                combinatorial_batches,
            )

        if updated_count > 1:
            logger.info(
                f"Prompt matrix will create {updated_count} images in a total of {p.n_iter} batches.",
            )

        self._prompt_writer.set_data(
            positive_template=original_prompt,
            negative_template=original_negative_prompt,
            positive_prompts=all_prompts,
            negative_prompts=all_negative_prompts,
        )

        if opts.dp_write_raw_template:
            params = p.extra_generation_params
            if original_prompt:
                params["Template"] = original_prompt
            if original_negative_prompt:
                params["Negative Template"] = original_negative_prompt

        p.all_prompts = all_prompts
        p.all_negative_prompts = all_negative_prompts
        if no_image_generation:
            logger.debug("No image generation requested - exiting")
            p.batch_size = 1
            p.all_prompts = all_prompts[0:1]

        p.prompt_for_display = original_prompt
        p.prompt = original_prompt

        if hr_fix_enabled:
            p.all_hr_prompts = _get_hr_fix_prompts(
                all_prompts,
                original_hr_prompt,
                original_prompt,
            )
            p.all_hr_negative_prompts = _get_hr_fix_prompts(
                all_negative_prompts,
                original_negative_hr_prompt,
                original_negative_prompt,
            )


callbacks.register_settings()
