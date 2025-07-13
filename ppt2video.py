#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import tempfile
import shutil
import atexit
import subprocess
import os
from PIL import ImageFont

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert a presentation Markdown file and a script file into a narrated video.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--presentation", required=True, help="Path to the presentation Markdown file.")
    parser.add_argument("--script", required=True, help="Path to the narration script Markdown file.")
    parser.add_argument("--output", default="output.mp4", help="Output video file name.")
    parser.add_argument("--resolution", default="1920x1080", help="Video resolution in WxH format.")
    parser.add_argument("--bg-color", default="black", help="Video background color.")
    parser.add_argument("--bg-image", default=None, help="Path to a background image (overrides bg-color).")
    parser.add_argument("--voice", default="Tingting", help="TTS voice to use (macOS only).")
    parser.add_argument("--font-file", default="/System/Library/Fonts/Hiragino Sans GB.ttc", help="Path to a .ttf or .ttc font file.")
    parser.add_argument("--font-size", type=int, default=120, help="Maximum font size for the text.")
    parser.add_argument("--margin", type=int, default=100, help="Margin around the text.")
    parser.add_argument("--list-voices", action="store_true", help="List available TTS voices and exit.")
    parser.add_argument("--silent-duration", type=int, default=3, help="Duration for silent slides in seconds.")
    return parser.parse_args()

def get_available_voices() -> list[str]:
    """Returns a list of available voices from the 'say' command."""
    try:
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, check=True)
        return [line.split()[0] for line in result.stdout.splitlines() if line.strip()]
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

def parse_presentation_file(filename: str) -> list[str]:
    """Parses the presentation file, splitting it into slides."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [s.strip() for s in f.read().split('\n---\n') if s.strip()]
    except FileNotFoundError:
        print(f"Error: Presentation file not found at '{filename}'")
        sys.exit(1)

def parse_script_file(filename: str) -> dict[str, str]:
    """Parses the script file into a dictionary mapping slide titles to narrations."""
    narrations = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        blocks = [block.strip() for block in content.split('\n---\n') if block.strip()]
        if blocks and not blocks[0].startswith("###"):
            blocks = blocks[1:]
        for block in blocks:
            lines = block.split('\n')
            title = lines[0].replace('###', '').replace('**', '').strip()
            narration = '\n'.join(lines[1:]).strip()
            if title:
                narrations[title] = narration
        return narrations
    except FileNotFoundError:
        print(f"Error: Script file not found at '{filename}'")
        sys.exit(1)

def generate_audio_file(text: str, voice: str, output_path: str, temp_dir: str) -> str:
    """Generates an AIFF audio file from text using the 'say' command."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=temp_dir, suffix=".txt") as temp_text_file:
            temp_text_file.write(text)
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
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def markdown_to_plain_text(text: str) -> str:
    """Converts simple Markdown to plain text for measurement."""
    lines = text.split('\n')
    formatted_lines = []
    for line in lines:
        if line.startswith('## '):
            line = line[3:]
        elif line.startswith('# '):
            line = line[2:]
        if line.strip().startswith('- '):
            line = '  • ' + line.strip()[2:]
        line = line.replace('**', '')
        formatted_lines.append(line)
    return '\n'.join(formatted_lines)

def calculate_optimal_font_size(text: str, font_file: str, max_size: int, box_width: int, box_height: int) -> int:
    """Calculates the largest font size that allows the text to fit within the given box without wrapping."""
    plain_text = markdown_to_plain_text(text)
    lines = plain_text.split('\n')
    
    size = max_size
    while size > 10:
        font = ImageFont.truetype(font_file, size)
        
        # Check width
        max_w = 0
        for line in lines:
            max_w = max(max_w, font.getlength(line))
        
        # Check height
        total_h = sum(font.getmetrics()) * len(lines)

        if max_w <= box_width and total_h <= box_height:
            return size
        size -= 2
        
    return size

def generate_video_segment(slide_data: dict, i: int, args: argparse.Namespace, temp_dir: str) -> str:
    """Generates a single video segment for a slide using ffmpeg's drawtext filter."""
    try:
        width, height = map(int, args.resolution.split('x'))
        box_width = width - (2 * args.margin)
        box_height = height - (2 * args.margin)
        
        optimal_font_size = calculate_optimal_font_size(slide_data["content"], args.font_file, args.font_size, box_width, box_height)
        print(f"     - Calculated optimal font size: {optimal_font_size}")

        display_text = markdown_to_plain_text(slide_data["content"])
        text_file_path = os.path.join(temp_dir, f"slide_{i}.txt")
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(display_text)

        command = ["ffmpeg"]
        if args.bg_image:
            command.extend(["-loop", "1", "-i", args.bg_image])
        else:
            command.extend(["-f", "lavfi", "-i", f"color=c={args.bg_color}:s={args.resolution}"])
        
        if slide_data["audio_path"]:
            command.extend(["-i", slide_data["audio_path"]])
        else:
            command.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

        video_filter = (
            f"drawtext=fontfile='{args.font_file}':textfile='{text_file_path}':"
            f"fontcolor=white:fontsize={optimal_font_size}:"
            f"x=(w-text_w)/2:y=(h-text_h)/2"
        )
        audio_filter = "aformat=channel_layouts=stereo:sample_rates=44100"
        command.extend(["-vf", video_filter, "-af", audio_filter])
        
        output_path = os.path.join(temp_dir, f"segment_{i}.mp4")
        command.extend(["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-t", str(slide_data["duration"]), "-shortest", "-y", output_path])
        
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
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-y", output_path
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

    temp_dir = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, temp_dir)

    print("---------------------------------")
    print("PPT to Video Converter (Python)")
    print("---------------------------------")
    
    available_voices = get_available_voices()
    if available_voices and args.voice not in available_voices:
        print(f"Error: Voice '{args.voice}' not found on this system.")
        print("Use --list-voices to see available options.")
        sys.exit(1)
    
    for key, value in vars(args).items():
        print(f"{key.replace('_', ' ').capitalize():<20}: {value}")
    print(f"{'Temporary dir':<20}: {temp_dir}")
    print("---------------------------------")

    print("1. Parsing files...")
    slides = parse_presentation_file(args.presentation)
    narrations = parse_script_file(args.script)
    print(f"   - Found {len(slides)} slides and {len(narrations)} narration blocks.")

    print("\n2. Preparing slide data (and generating audio)...")
    slide_data_list = []
    for i, slide_content in enumerate(slides):
        slide_title = ""
        for line in slide_content.split('\n'):
            if line.startswith('## '):
                slide_title = line.replace('## ', '').strip()
                break
        
        data = {"title": slide_title, "content": slide_content, "audio_path": None, "duration": args.silent_duration}
        narration = narrations.get(slide_title)
        if narration:
            audio_path = os.path.join(temp_dir, f"slide_{i+1}.aiff")
            generate_audio_file(narration, args.voice, audio_path, temp_dir)
            duration = get_audio_duration(audio_path)
            data["audio_path"] = audio_path
            data["duration"] = duration
        slide_data_list.append(data)
    print("   - Slide data preparation complete.")

    print("\n3. Generating video segments...")
    segment_paths = []
    for i, slide_data in enumerate(slide_data_list):
        print(f"   - Generating segment for Slide {i+1} ('{slide_data['title']}')...")
        segment_path = generate_video_segment(slide_data, i + 1, args, temp_dir)
        segment_paths.append(segment_path)
        print(f"     - Segment generated: {segment_path}")

    print("\n4. Assembling final video...")
    concatenate_videos(segment_paths, args.output, temp_dir)

    print("\n---------------------------------")
    print("Processing complete.")

if __name__ == "__main__":
    main()