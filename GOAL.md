### **Final Goal Specification for `ppt2video`**

**1. Core Objective**
The script's purpose is to convert a presentation file (e.g., Markdown) and a corresponding narration script file into a synchronized video.

**2. Inputs**
*   **Presentation File**: A file like `@maga_presentation.md` containing the visual text to be displayed on screen, slide by slide.
*   **Script File**: A file like `@maga_presentation_script.md` containing the narration script to be read aloud, synchronized with the presentation slides.

**3. Video Generation**
The process generates a single video with the following features:
*   **Visuals**: The content from the presentation file is displayed on screen.
*   **Narration**: The corresponding text from the script file is read aloud using a text-to-speech (TTS) engine.
*   **Synchronization**: The display of each slide is timed to match the duration of its corresponding narration.
*   **Pauses**: If a slide has visual content but no accompanying narration, it will be displayed for a specified duration with silence.

**4. Command-Line Interface**
The script must be configurable via the following command-line options, each with a sensible default:
*   `--presentation <file>`: Path to the presentation file.
*   `--script <file>`: Path to the narration script file.
*   `--output <file>`: Specify the output video file name.
*   `--resolution <WxH>`: Set the video resolution.
*   `--bg-color <color>`: Set the video background color.
*   `--bg-image <path>`: Use an image for the background (overrides `--bg-color`).
*   `--voice <name>`: Set the TTS voice.
*   `--font-file <path>`: Path to a `.ttf` or `.ttc` font file.
*   `--font-size <num>`: Set the font size.
*   `--help`: Display a help message.

**5. Robustness**
*   The script should gracefully handle mismatches between the number of presentation slides and narration blocks.
*   It must continue to support CJK characters for both on-screen text and TTS narration.
