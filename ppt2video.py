#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import tempfile
import shutil
import atexit
import subprocess
import os

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
    parser.add_argument("--voice", default="Ting-Ting", help="TTS voice to use (macOS only).")
    parser.add_argument("--font-file", default="/System/Library/Fonts/PingFang.ttc", help="Path to a .ttf or .ttc font file.")
    parser.add_argument("--font-size", type=int, default=48, help="Font size for the text.")
    parser.add_argument("--silent-duration", type=int, default=3, help="Duration for silent slides in seconds.")
    return parser.parse_args()

def parse_presentation_file(filename: str) -> list[str]:
    """Parses the presentation file, splitting it into slides."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        return [slide.strip() for slide in content.split('\n---\n') if slide.strip()]
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

def format_text_for_ass(text: str) -> str:
    """Converts simple Markdown to ASS subtitle format."""
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
    return '\\N'.join(formatted_lines)

def generate_video_segment(slide_data: dict, i: int, args: argparse.Namespace, temp_dir: str) -> str:
    """Generates a single video segment for a slide using an ASS subtitle file."""
    try:
        # 1. Create ASS subtitle file
        display_text = format_text_for_ass(slide_data["content"])
        font_name = os.path.basename(args.font_file).split('.')[0]
        style = f"Style: Default,{font_name},{args.font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,7,100,100,100,1"
        end_time_seconds = slide_data['duration']
        end_time_str = f"{int(end_time_seconds // 3600)}:{int((end_time_seconds % 3600) // 60):02}:{end_time_seconds % 60:05.2f}"
        ass_content = f"[Script Info]\nTitle: ppt2video\nScriptType: v4.00+\nWrapStyle: 0\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n{style}\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:00.00,{end_time_str},Default,,0,0,0,,{display_text}\n"
        ass_path = os.path.join(temp_dir, f"slide_{i}.ass")
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)

        # 2. Build ffmpeg command
        command = ["ffmpeg"]
        if args.bg_image:
            command.extend(["-loop", "1", "-i", args.bg_image])
        else:
            command.extend(["-f", "lavfi", "-i", f"color=c={args.bg_color}:s={args.resolution}"])
        
        if slide_data["audio_path"]:
            command.extend(["-i", slide_data["audio_path"]])
        else:
            command.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

        video_filter = f"subtitles='{os.path.abspath(ass_path)}'"
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
        command = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_path, "-c", "copy", "-y", output_path]
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
    temp_dir = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, temp_dir)

    print("---------------------------------")
    print("PPT to Video Converter (Python)")
    print("---------------------------------")
    for key, value in vars(args).items():
        print(f"{key.replace('_', ' ').capitalize():<20}: {value}")
    print(f"{'Temporary dir':<20}: {temp_dir}")
    print("---------------------------------")

    # 1. Parse files
    print("1. Parsing files...")
    slides = parse_presentation_file(args.presentation)
    narrations = parse_script_file(args.script)
    print(f"   - Found {len(slides)} slides and {len(narrations)} narration blocks.")

    # 2. Generate audio and prepare slide data
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
            audio_path = os.path.join(temp_dir, f"slide_{i}.aiff")
            generate_audio_file(narration, args.voice, audio_path, temp_dir)
            duration = get_audio_duration(audio_path)
            data["audio_path"] = audio_path
            data["duration"] = duration
        slide_data_list.append(data)
    print("   - Slide data preparation complete.")

    # 3. Generate video segments
    print("\n3. Generating video segments...")
    segment_paths = []
    for i, slide_data in enumerate(slide_data_list):
        print(f"   - Generating segment for Slide {i+1} ('{slide_data['title']}')...")
        segment_path = generate_video_segment(slide_data, i + 1, args, temp_dir)
        segment_paths.append(segment_path)
        print(f"     - Segment generated: {segment_path}")

    # 4. Concatenate segments
    print("\n4. Assembling final video...")
    concatenate_videos(segment_paths, args.output, temp_dir)

    print("\n---------------------------------")
    print("Processing complete.")

if __name__ == "__main__":
    main()