# AI Specification for ppt2video Project

## Narration Content Definition

In `script.md`, the narration content for each slide is defined as the text block that starts immediately after a `(幻灯片 n: ...)` marker and extends until the next `---` (three hyphens) separator or the end of the file. 

Content located between a `---` separator and a `(幻灯片 n: ...)` marker (e.g., section headers like `### **开场白**`) is considered structural and is NOT part of the narration for any slide. These structural elements are intended for speaker reference only.

The `(幻灯片 n: ...)` markers themselves will be removed during the text-to-speech preprocessing step, but the text following them (up to the next `---` or end of file) will be included in the narration.
