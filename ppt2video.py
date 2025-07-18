#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import tempfile
import shutil
import atexit
import subprocess
import os
import re

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert a presentation file (.tex or .pdf) and a script file into a narrated video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--presentation", required=True, help="Path to the presentation file (either .tex or .pdf).")
    parser.add_argument("--script", required=True, help="Path to the narration script Markdown file.")
    parser.add_argument("--output", default="output.mp4", help="Output video file name.")
    parser.add_argument("--resolution", default="1920x1080", help="Video resolution in WxH format.")
    parser.add_argument("--voice", default="Tingting", help="TTS voice to use (macOS only).")
    parser.add_argument("--list-voices", action="store_true", help="List available TTS voices and exit.")
    parser.add_argument("--silent-duration", type=int, default=3, help="Duration for silent slides in seconds.")
    return parser.parse_args()

def check_dependencies(is_tex: bool):
    """Checks for required command-line tool dependencies."""
    if is_tex and not shutil.which("pdflatex"):
        print("Error: pdflatex command not found. Is a LaTeX distribution (like MacTeX) installed?")
        sys.exit(1)
    if not shutil.which("ffmpeg"):
        print("Error: ffmpeg command not found. Please install it.")
        sys.exit(1)
    if not shutil.which("ffprobe"):
        print("Error: ffprobe command not found. Please install it.")
        sys.exit(1)
    if sys.platform == "darwin" and not shutil.which("say"):
        print("Error: 'say' command not found. This script currently relies on macOS for TTS.")
        sys.exit(1)

def get_available_voices() -> list[str]:
    """Returns a list of available voices from the 'say' command."""
    try:
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=True)
        return [line.split()[0] for line in result.stdout.splitlines() if line.strip()]
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

def compile_latex_to_pdf(tex_file: str, temp_dir: str) -> str:
    """Compiles a .tex file into a .pdf using xelatex."""
    print(f"   - Compiling {os.path.basename(tex_file)} to PDF using xelatex...")
    pdf_path = os.path.join(temp_dir, os.path.basename(tex_file).replace(".tex", ".pdf"))
    command = [
        "xelatex",
        "-interaction=nonstopmode",
        "-output-directory", temp_dir,
        tex_file
    ]
    try:
        # Run twice to ensure all cross-references are resolved
        subprocess.run(command, check=True, capture_output=True, text=True)
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"     - PDF generated: {pdf_path}")
        return pdf_path
    except subprocess.CalledProcessError as e:
        print("Error during LaTeX compilation.")
        # Attempt to read the log file for more details
        log_file = os.path.join(temp_dir, os.path.basename(tex_file).replace(".tex", ".log"))
        if os.path.exists(log_file):
            print(f"--- LaTeX Log File ({log_file}) ---")
            with open(log_file, 'r') as f:
                print(f.read())
            print("--- End Log File ---")
        else:
            print(f"stdout:\n{e.stdout}")
            print(f"stderr:\n{e.stderr}")
        sys.exit(1)

def get_pdf_page_count(pdf_path: str) -> int:
    """Gets the number of pages in a PDF file using pdfinfo."""
    try:
        command = ["pdfinfo", pdf_path]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.lower().startswith("pages:"):
                return int(line.split(':')[1].strip())
        raise ValueError("Could not find page count in pdfinfo output.")
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting PDF page count: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def extract_pdf_pages_as_images(pdf_path: str, page_count: int, resolution: str, temp_dir: str) -> list[str]:
    """Extracts each page of a PDF into a PNG image file using pdftoppm."""
    print("   - Extracting PDF pages as images using pdftoppm...")
    width, height = resolution.split('x')
    output_prefix = os.path.join(temp_dir, "slide")
    command = [
        "pdftoppm",
        "-png",
        "-scale-to-x", width,
        "-scale-to-y", height,
        pdf_path,
        output_prefix
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        # Find generated images, sort them, and verify the count.
        generated_files = sorted([
            os.path.join(temp_dir, f)
            for f in os.listdir(temp_dir)
            if f.startswith("slide-") and f.endswith(".png")
        ])
        if len(generated_files) != page_count:
            raise RuntimeError(
                f"pdftoppm generated {len(generated_files)} images, but {page_count} were expected."
            )
        for path in generated_files:
            print(f"     - Image found: {path}")
        return generated_files
    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError) as e:
        print(f"Error during PDF page extraction (pdftoppm): {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)


def parse_script_file(filename: str, total_slides: int) -> dict[int, str]:
    """Parses the script file into a dictionary mapping slide numbers to narrations."""
    narrations = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        blocks = [block.strip() for block in content.split('\n---\n') if block.strip()]
        
        for block in blocks:
            match = re.search(r'\(幻灯片\s*(\d+):', block)
            if match:
                slide_num = int(match.group(1))
                if 1 <= slide_num <= total_slides:
                    narrations[slide_num] = block
    except FileNotFoundError:
        print(f"Error: Script file not found at '{filename}'")
        sys.exit(1)
    return narrations

def preprocess_text_for_tts(text: str) -> str:
    """Preprocesses text to improve TTS pronunciation and remove metadata."""
    text = re.sub(r'\(幻灯片\s*\d+:[^\)]*\)', '', text)
    text = re.sub(r'\[cite[^\]]*\]', '', text)
    text = re.sub(r'\bAI\b', 'A. I.', text, flags=re.IGNORECASE)
    return text.strip()

def generate_audio_file(text: str, voice: str, output_path: str, temp_dir: str) -> str:
    """Generates an AIFF audio file from text using the 'say' command."""
    try:
        processed_text = preprocess_text_for_tts(text)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=temp_dir, suffix=".txt") as temp_text_file:
            temp_text_file.write(processed_text)
            temp_text_path = temp_text_file.name
        command = ["say", "-v", voice, "-o", output_path, "--file-format=AIFF", "-f", temp_text_path]
        subprocess.run(command, check=True, capture_output=True, text=True)
        os.remove(temp_text_path)
        return output_path
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error during audio generation: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def get_audio_duration(file_path: str) -> float:
    """Gets the duration of an audio file in seconds using ffprobe."""
    try:
        command = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError) as e:
        print(f"Error getting audio duration: {e}")
        sys.exit(1)

def generate_video_segment(image_path: str, audio_path: str, duration: float, output_path: str, resolution: str) -> str:
    """Generates a single video segment for a slide from its image and audio."""
    try:
        width, height = resolution.split('x')
        command = ["ffmpeg", "-y", "-loop", "1", "-i", image_path]
        
        if audio_path:
            command.extend(["-i", audio_path])
            audio_filter = "aformat=channel_layouts=stereo:sample_rates=44100"
            command.extend(["-af", audio_filter])
        else: # Silent slide
            command.extend(["-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100:d={duration}"])

        command.extend([
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-t", str(duration), 
            "-s", resolution, "-shortest", output_path
        ])
        
        subprocess.run(command, check=True, capture_output=True, text=True)
        return output_path
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error during video segment generation: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def concatenate_videos(segment_paths: list[str], output_path: str, temp_dir: str):
    """Concatenates multiple video segments into a single video file."""
    try:
        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_path, 'w') as f:
            for path in segment_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        command = [
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_path,
            "-c", "copy", "-y", output_path
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"\nFinal video successfully generated at: {output_path}")
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Error during video concatenation: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def main():
    """Main function to run the script."""
    args = parse_arguments()
    
    if args.list_voices:
        print("Available TTS voices:")
        voices = get_available_voices()
        if voices:
            for voice in voices:
                print(f"  - {voice}")
        else:
            print("Could not retrieve voices. Is 'say' command available?")
        sys.exit(0)

    is_tex = args.presentation.lower().endswith('.tex')
    check_dependencies(is_tex)
    temp_dir = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, temp_dir)

    print("---------------------------------")
    print("PPT to Video Converter (v2.0.0)")
    print("---------------------------------")
    
    if sys.platform == "darwin":
        available_voices = get_available_voices()
        if available_voices and args.voice not in available_voices:
            print(f"Error: Voice '{args.voice}' not found on this system.")
            print("Use --list-voices to see available options.")
            sys.exit(1)
    
    for key, value in vars(args).items():
        print(f"{key.replace('_', ' ').capitalize():<20}: {value}")
    print(f"{'Temporary dir':<20}: {temp_dir}")
    print("---------------------------------")

    if is_tex:
        print("1. Compiling LaTeX to PDF...")
        pdf_path = compile_latex_to_pdf(args.presentation, temp_dir)
    else:
        print("1. Using existing PDF...")
        pdf_path = args.presentation

    print("\n2. Preparing images from PDF...")
    page_count = get_pdf_page_count(pdf_path)
    image_paths = extract_pdf_pages_as_images(pdf_path, page_count, args.resolution, temp_dir)
    print(f"   - Found {page_count} pages in the PDF.")

    print("\n3. Parsing script and preparing audio...")
    narrations = parse_script_file(args.script, page_count)
    print(f"   - Found {len(narrations)} narration blocks.")

    slide_data_list = []
    for i, image_path in enumerate(image_paths):
        slide_num = i + 1
        data = {"image_path": image_path, "audio_path": None, "duration": args.silent_duration}
        narration = narrations.get(slide_num)
        
        if narration:
            print(f"   - Generating audio for Slide {slide_num}...")
            audio_path = os.path.join(temp_dir, f"slide_{slide_num}.aiff")
            generate_audio_file(narration, args.voice, audio_path, temp_dir)
            duration = get_audio_duration(audio_path)
            data["audio_path"] = audio_path
            data["duration"] = duration
            print(f"     - Audio generated: {audio_path} (Duration: {duration:.2f}s)")
        else:
            print(f"   - Slide {slide_num} is silent (Duration: {args.silent_duration}s).")
            
        slide_data_list.append(data)

    print("\n4. Generating video segments...")
    segment_paths = []
    for i, slide_data in enumerate(slide_data_list):
        print(f"   - Generating segment for Slide {i+1}...")
        segment_path = os.path.join(temp_dir, f"segment_{i+1}.mp4")
        generate_video_segment(slide_data["image_path"], slide_data["audio_path"], slide_data["duration"], segment_path, args.resolution)
        segment_paths.append(segment_path)
        print(f"     - Segment generated: {segment_path}")

    print("\n5. Assembling final video...")
    concatenate_videos(segment_paths, args.output, temp_dir)

    print("\n---------------------------------")
    print("Processing complete.")

if __name__ == "__main__":
    main()