# AI Content Generation Specification for ppt2video

This document outlines the rules for generating two synchronized Markdown files: a **Presentation File** and a **Script File**. Adhering to this specification is crucial for the files to be correctly processed by the `ppt2video` tool.

---

## 1. File 1: The Presentation File (`presentation.md`)

This file contains the visual content that will be displayed on each slide of the video.

### **Rules:**

1.  **File Format**: Must be a Markdown (`.md`) file.
2.  **Slide Separation**: Each slide MUST be separated from the next by a Markdown horizontal rule (`---`).
3.  **Slide Identification**:
    *   Each slide's content MUST begin with a Level 2 Markdown Header (`##`).
    *   The header format MUST be `## Slide <N>: <Slide Title>`, where `<N>` is the sequential slide number and `<Slide Title>` is the title for that slide.
4.  **Content**: The body of the slide (e.g., bullet points, text) should follow its `##` header.

### **Example `presentation.md`:**

```markdown
# My Presentation Title

## Slide 1: Introduction
- This is the first point.
- This is the second point.

---

## Slide 2: Key Data
- Data point A.
- Data point B.

---

## Slide 3: Conclusion
- Summary of the presentation.
```

---

## 2. File 2: The Script File (`script.md`)

This file contains the narration script that will be spoken aloud, synchronized with the slides from the Presentation File.

### **Rules:**

1.  **File Format**: Must be a Markdown (`.md`) file.
2.  **Script Block Separation**: Each narration block MUST be separated by a Markdown horizontal rule (`---`).
3.  **Synchronization (Crucial Rule)**:
    *   Each narration block corresponds to exactly one slide from the `presentation.md` file.
    *   Each block MUST begin with a Level 3 Markdown Header (`###`).
    *   The text of this `###` header MUST **exactly match** the text of the corresponding `##` header from the `presentation.md` file. For example, if the slide header is `## Slide 2: Key Data`, the script header must be `### Slide 2: Key Data`.
4.  **Silent Slides**: If a slide in `presentation.md` should have no narration, it MUST NOT have a corresponding block in the `script.md` file.
5.  **Multi-language Scripts**: If providing the script in multiple languages, each language's text should be preceded by a clear, bolded identifier (e.g., `**English:**`, `**Chinese (中文):**`).

### **Example `script.md` (corresponding to the presentation example):**

```markdown
# My Presentation Speaker Notes

This script corresponds to the slides in `presentation.md`.

---

### Slide 1: Introduction

**English:**
"Hello everyone. In this first slide, I will introduce the main topic by explaining the first and second points."

**Chinese (中文):**
“大家好。在第一张幻灯片中，我将通过解释第一点和第二点来介绍主题。”

---

### Slide 3: Conclusion

**English:**
"To conclude, I will now summarize the key takeaways from this presentation."

**Chinese (中文):**
“最后，我现在将总结本次演讲的要点。”

```
*Notice that "Slide 2" is intentionally omitted from the script, meaning it will be a silent slide in the final video.*
