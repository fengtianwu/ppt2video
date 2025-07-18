# AI Content Generation Specification for ppt2video (v2.0.0)

This document outlines the rules for generating the input files for the `ppt2video` tool. The tool requires two files: a **Presentation File** (either LaTeX or PDF) and a **Markdown Script File**.

---

## 1. File 1: The Presentation File (`.tex` or `.pdf`)

This file provides the visual content for each slide. The tool accepts two formats.

### **Option A: LaTeX Source (`presentation.tex`)**
This is the recommended format for generating new content, as it allows for easy editing and version control.

*   **File Format**: Must be a LaTeX (`.tex`) file.
*   **Document Class**: Must use the `beamer` document class (`\documentclass{beamer}`).
*   **Slide Structure**: Each slide (a single page in the final PDF) MUST be defined within a `frame` environment (`\begin{frame} ... \end{frame}`).
*   **Processing**: The `ppt2video` tool will automatically compile this file into a PDF using `pdflatex`.

### **Option B: PDF Document (`presentation.pdf`)**
This option is for cases where the LaTeX source is unavailable, or when manual edits have been made to the PDF itself.

*   **File Format**: Must be a Portable Document Format (`.pdf`) file.
*   **Processing**: The `ppt2video` tool will use this file directly, extracting each page as a slide image.

---

## 2. File 2: The Script File (`script.md`)

This file contains the narration script that will be spoken aloud, synchronized with the pages of the final PDF presentation.

### **Rules:**

1.  **File Format**: Must be a Markdown (`.md`) file.
2.  **Script Block Separation**: Each narration block MUST be separated by a Markdown horizontal rule (`---`).
3.  **Synchronization (Crucial Rule)**:
    *   Each narration block corresponds to exactly one page from the final PDF presentation.
    *   Each block MUST contain a **slide number marker** to identify which page it corresponds to.
    *   The marker format is `**(幻灯片 <number>: <description>)**`, where `<number>` is the page number in the PDF (starting from 1) and `<description>` is an optional description for readability.
    *   Example: `**(幻灯片 2: Introduction)**` links the narration to the second page of the PDF.
4.  **Silent Slides**: If a page in the PDF should have no narration, it MUST NOT have a corresponding block in the `script.md` file.
5.  **Multi-language Scripts**: If providing the script in multiple languages, each language's text should be preceded by a clear, bolded identifier (e.g., `**English:**`, `**Chinese (中文):**`).

### **Example `script.md`:**

```markdown
This script corresponds to the pages in the PDF.

---

**(幻灯片 2: Introduction)**

**English:**
"Hello everyone. On this second slide, I will introduce the main topic..."

**Chinese (中文):**
“大家好。在第二张幻灯片中，我将介绍主题...”

---

**(幻灯片 3: Key Data)**

**English:**
"Here we see the key data points..."

**Chinese (中文):**
“在这里，我们看到了关键数据点...”
```
*Notice that Page 1 is intentionally omitted from the script, meaning it will be a silent slide in the final video.*
