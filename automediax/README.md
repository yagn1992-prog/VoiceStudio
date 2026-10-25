# AutoMediaX reel voice-over (free, local)

Clone a voice from a short recording and voice an Instagram reel so each line starts on its caption.
Engine: OmniVoice (`k2-fsa/OmniVoice`, Apache-2.0), the default VoiceStudio engine. No paid API, no credits.

## 1. One-time setup on Windows (PowerShell)

```powershell
winget install --id Python.Python.3.11 -e
winget install --id Gyan.FFmpeg -e
winget install --id Git.Git -e
# close and reopen PowerShell
git clone https://github.com/yagn1992-prog/VoiceStudio C:\VoiceStudio
cd C:\VoiceStudio
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r automediax\requirements.txt
```

NVIDIA GPU? Replace `cpu` with `cu124` in the torch line; generation becomes 10-20x faster.
The first run downloads the OmniVoice model (about 2-3 GB) from Hugging Face.

## 2. Record your voice once

- 15-20 seconds, quiet room, fan/AC off, phone 6-8 inches from mouth, reel-style energy.
- Save it as `my_voice.wav` (any format works; ffmpeg converts).
- Put the exact words you spoke in `automediax\my_voice.txt`.

## 3. Write the reel script

Copy `automediax\day04_script.json`. Each line: `id`, `start` (second when its caption appears), `text`.
Write Hindi in Devanagari and English words in English. Brand names read better spelled out (`ऑटो मीडिया एक्स`).

## 4. Make the reel

```powershell
.\.venv\Scripts\Activate.ps1
python automediax\make_voiceover.py --video Day05.mp4 --script automediax\day05_script.json `
  --ref my_voice.wav --ref-text automediax\my_voice.txt --out Day05_final
```

Output: `Day05_final_Reel.mp4` (ready to post), plus `_voiceover.wav` and `_voiceover.mp3`.
To redo only some lines: add `--only 3 7` (line ids). `--steps 16` is about 2x faster with slightly lower quality.

## Limits

- On CPU each line takes 1-3 minutes; a 90-second reel takes about an hour.
- The clone can only be as good as the recording: noise, echo or a flat delivery carry over.
- Some English words may come out with Hindi-style pronunciation; regenerate that line, or try writing it in English letters (or in Devanagari) and compare.

## AutoMediaX male voice (Day 02)

Cut the reference from the Day 02 reel and use `automediax/day02_voice.txt` as its transcript:

```powershell
ffmpeg -i AUTOMEDIAX_Day02_Reel.mp4 -vn -ac 1 -ar 44100 day02.wav
ffmpeg -i day02.wav -filter_complex "[0:a]asplit=2[x][y];[x]atrim=3.42:12.02,asetpts=PTS-STARTPTS[a];[y]atrim=23.47:28.45,asetpts=PTS-STARTPTS[b];anullsrc=r=44100:cl=mono,atrim=0:0.35[g];[a][g][b]concat=n=3:v=0:a=1" -ar 24000 day02_voice.wav
python automediax/make_voiceover.py --video Day05.mp4 --script automediax/day05_script.json `
  --ref day02_voice.wav --ref-text automediax/day02_voice.txt --out Day05_final
```

Keep the reference at about 14 seconds: longer clips need more than 8 GB RAM on CPU.
