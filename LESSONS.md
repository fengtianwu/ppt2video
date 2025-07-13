### **Summary of Problems and Lessons Learned (ppt2video)**

This document summarizes the key problems encountered during the development of the `ppt2video` project. The process was iterative and involved several major refactors.

---

**1. Problem: Font Layout and Sizing (The Core Challenge)**
*   **Issue**: This was by far the most difficult and persistent problem. The core challenge was ensuring that text of any length would fit perfectly within the video frame without overflowing.
    1.  **Initial `drawtext` Failure**: The first approach using `ffmpeg`'s `drawtext` filter was abandoned because it does not support automatic text wrapping, which I mistakenly thought was a requirement.
    2.  **The `Pillow` Guesswork Fallacy**: The subsequent, and most time-consuming, error was trying to use the Python `Pillow` library to *predict* how `ffmpeg`'s ASS/`subtitles` filter would render text. This approach was fundamentally flawed because the two systems have completely different typographic engines. Their calculations for line height, character spacing, and margins are not interchangeable. This led to a frustrating cycle of the font being either too large (overflowing) or too small (too much padding).
    3.  **The `ffmpeg` Dry-Run Failure**: An attempt to have `ffmpeg` measure the text itself via a "dry-run" mode proved to be unreliable and inconsistent across environments, failing to return the necessary dimension data.
*   **Final Lesson & Solution**: The simplest path was the correct one all along. The final, successful algorithm returned to using `drawtext`, embracing its lack of automatic wrapping.
    1.  **Trust a Single Source of Truth**: All text measurement should be done in a single, consistent environment before being passed to the final renderer. The successful approach used `Pillow` to calculate the optimal font size based on the slide's longest line and total number of lines.
    2.  **No Magic Numbers**: The final algorithm does not rely on "magic number" multipliers for line spacing. It calculates the total height of the text block directly.
    3.  **Define the Requirement Clearly**: The breakthrough came when the requirement was clarified to **"Do not wrap lines; scale the font to fit."** This immediately made `drawtext` the correct tool for the job.

**2. Problem: External Command Integration (`say`, `ffprobe`, `ffmpeg`)**
*   **Issue**: Integrating with command-line tools presented several challenges.
    1.  **`say`**: The macOS TTS command failed silently if a voice was misspelled (e.g., `Ting-Ting` vs. `Tingting`). It also had issues when very long strings were passed directly on the command line.
    2.  **`afinfo`**: This macOS-specific tool for getting audio duration proved unreliable, with its output format being inconsistent and sometimes printing to `stderr` instead of `stdout`.
    3.  `ffmpeg`: The `concat` demuxer is very strict about stream properties. Mismatches in audio sample rates or channel layouts between silent and narrated segments caused the final video to have no sound.
*   **Lesson**: External commands are fragile dependencies.
    1.  **Validate Inputs**: Always validate inputs passed to external commands (e.g., check if a voice exists before calling `say`). The final script added a `--list-voices` option and a startup check.
    2.  **Use Robust Tools**: `ffprobe` is a much more reliable and standard tool for media introspection than `afinfo`.
    3.  **Standardize Streams**: When combining media, always re-encode or filter them to a common, standard format (`aformat` and `-c:a aac` in our case) before the final concatenation step.
    4.  **Avoid Passing Large Data via CLI**: Pass large blocks of text to commands via temporary files (`-f` for `say`, `textfile` for `drawtext`) to avoid shell argument length limits.

**3. Problem: Foundational Design (Shell vs. Python)**
*   **Issue**: The initial attempt to build the tool as a `bash` script quickly failed due to `bash`'s limitations in handling arrays portably and its lack of floating-point arithmetic.
*   **Lesson**: Use the right tool for the job. For a project involving process orchestration, floating-point math, and complex data manipulation, Python is a far superior choice to shell scripting.
