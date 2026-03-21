/* global titles:true */
// Mouseover tooltips for various UI elements.
// `titles` is already defined by A1111, so we just merge into it...
titles = {
  ...titles,
  "Dynamic Prompts enabled": "Disable dynamic prompts by unchecking this box.",

  "Combinatorial generation": `
Instead of generating random prompts from a template, combinatorial generation produces every possible prompt from the given string.
The prompt 'I {love|hate} {New York|Chicago} in {June|July|August}' will produce 12 variants in total.

The value of the 'Seed' field is only used for the first image. To change this, look for 'Fixed seed' in the 'Advanced options' section.`.trim(),

  "Max generations (0 = all combinations - the batch count value is ignored)": `
Limit the maximum number of prompts generated. 0 (default) will generate all images. Useful to prevent an unexpected combinatorial explosion.
`.trim(),

  "Combinatorial batches": `Re-run your combinatorial batch this many times with a different seed each time.`,

  "Write prompts to file": `
The generated file is a slugified version of the prompt and can be found in the same directory as the generated images.
E.g. in ./outputs/txt2img-images/.`.trim(),

  "Don't generate images":
    "Be sure to check the 'Write prompts to file' checkbox if you don't want to lose the generated prompts. Note, one image is still generated.",
  "Unlink seed from prompt":
    "Check this if you want to generate random prompts, even if your seed is fixed",

  "Fixed seed": `
Select this if you want to use the same seed for every generated image.
This is useful if you want to test prompt variations while using the same seed.
If there are no wildcards then all the images will be identical.
`.trim(),
  "Write raw prompt to image":
    "Write the prompt template into the image metadata",
};
