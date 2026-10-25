"""AutoMediaX reel voice-over: clone a voice with OmniVoice and place each line on the reel's caption timeline.

Usage (from the repository root):
    python automediax/make_voiceover.py --video Day04.mp4 --script automediax/day04_script.json \
        --ref my_voice.wav --ref-text automediax/my_voice.txt --out Day04_final

Script JSON: a list of {"id": 1, "start": 0.3, "text": "..."} ordered by start time (seconds).
Optional "dur" per line fixes its length; otherwise it is estimated and capped to the gap before the next line.
Outputs: <out>_voiceover.wav, <out>_voiceover.mp3 and <out>_Reel.mp4 (original video, audio replaced).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omnivoice.models.omnivoice import OmniVoice  # noqa: E402

SR = 44100


def ffprobe_duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", str(path)])
    return float(out.decode().strip())


def trim_silence(y, thresh=0.01):
    idx = np.where(np.abs(y) > thresh)[0]
    return y[idx[0]: idx[-1] + 1] if len(idx) else y


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", required=True)
    p.add_argument("--script", required=True)
    p.add_argument("--ref", required=True, help="10-20 s clean recording of the voice to clone")
    p.add_argument("--ref-text", required=True, help="text file with the exact words spoken in --ref")
    p.add_argument("--out", required=True)
    p.add_argument("--language", default="hi")
    p.add_argument("--steps", type=int, default=32, help="quality steps: 32 best, 16 about 2x faster")
    p.add_argument("--chars-per-sec", type=float, default=13.0, help="speaking pace used to estimate line length")
    p.add_argument("--only", type=int, nargs="*", help="regenerate only these line ids")
    a = p.parse_args()

    lines = sorted(json.load(open(a.script, encoding="utf-8")), key=lambda x: x["start"])
    ref_text = Path(a.ref_text).read_text(encoding="utf-8").strip()
    video_dur = ffprobe_duration(a.video)
    cache = Path(a.out + "_lines")
    cache.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=device,
                                      dtype=torch.float16 if device == "cuda" else torch.float32)
    prompt = model.create_voice_clone_prompt(ref_audio=a.ref, ref_text=ref_text)

    track = np.zeros(int(video_dur * SR), dtype=np.float32)
    cursor = 0.0
    for i, L in enumerate(lines):
        nxt = lines[i + 1]["start"] if i + 1 < len(lines) else video_dur - 0.3
        room = nxt - L["start"] - 0.12
        dur = L.get("dur") or max(1.0, min(room, len(L["text"]) / a.chars_per_sec))
        wav = cache / f"line_{L['id']:03d}.wav"
        if not wav.exists() or (a.only and L["id"] in a.only):
            audio = model.generate(text=L["text"], language=a.language, voice_clone_prompt=prompt,
                                   duration=dur, num_step=a.steps)
            import torchaudio
            torchaudio.save(str(wav), audio[0].cpu(), model.sampling_rate)
            print(f"line {L['id']}: {dur:.2f}s  {L['text']}", flush=True)
        y = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ac", "1", "-ar", str(SR),
                            "-f", "f32le", "-"], capture_output=True, check=True).stdout
        y = trim_silence(np.frombuffer(y, np.float32))
        start = max(L["start"], cursor + 0.1)
        s = int(start * SR)
        e = min(s + len(y), len(track))
        track[s:e] += y[: e - s]
        cursor = start + len(y) / SR

    raw = a.out + "_raw.f32"
    track.tofile(raw)
    vo = a.out + "_voiceover.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", raw,
                    "-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-ar", str(SR), vo], check=True)
    Path(raw).unlink()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vo, "-b:a", "192k", a.out + "_voiceover.mp3"], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.video, "-i", vo, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                    a.out + "_Reel.mp4"], check=True)
    print("Done:", a.out + "_Reel.mp4")


if __name__ == "__main__":
    main()
