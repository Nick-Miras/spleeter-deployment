import gradio as gr
import subprocess
import os
import shutil
from pathlib import Path
import sys

def separate_audio(audio_file):
    if audio_file is None:
        return [None, None, None, None, None, ""]
    
    out_dir = "gradio_output"
    os.makedirs(out_dir, exist_ok=True)
    
    # Run spleeter CLI to separate the audio
    # Using the local configs/config.json as seen in test.sh
    command = [
        sys.executable, "-m", "spleeter", "separate",
        "-o", out_dir,
        "-p", "configs/config.json",
        audio_file
    ]
    
    print(f"Running command: {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during separation: {e}")
        return [None, None, None, None, None, ""]
    
    # Spleeter outputs the stems into a folder named after the input file's original name
    filename = Path(audio_file).stem
    folder_path = Path(out_dir) / filename
    
    vocals_path = str(folder_path.resolve() / "vocals.wav")
    drums_path = str(folder_path.resolve() / "drums.wav")
    bass_path = str(folder_path.resolve() / "bass.wav")
    other_path = str(folder_path.resolve() / "other.wav")
    
    output_files = []
    if folder_path.exists():
        for f in folder_path.glob("*.wav"):
            output_files.append(str(f))
            
    srcdoc_content = f"""
        <html>
        <body style='font-family: sans-serif; margin: 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background: #fff; text-align: center;'>
            <h3 style='margin-top: 0; color: #333;'>Synced Playback</h3>
            <button onclick='playAll()' style='background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-right: 10px;'>Play All</button>
            <button onclick='pauseAll()' style='background: #f44336; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;'>Pause All</button>
            <script>
                function getStemAudios() {{
                    var stems = [];
                    // Gradio mounts inside a custom element that uses a Shadow DOM.
                    // We must recursively search through all Shadow DOMs to find the <audio> tags.
                    function findAudio(root) {{
                        if (!root) return;
                        if (root.tagName && root.tagName.toLowerCase() === 'audio') {{
                            if (root.src) stems.push(root);
                        }}
                        if (root.shadowRoot) {{
                            findAudio(root.shadowRoot);
                        }}
                        var children = root.children || root.childNodes;
                        if (children) {{
                            for (var i = 0; i < children.length; i++) {{
                                findAudio(children[i]);
                            }}
                        }}
                    }}
                    
                    findAudio(window.parent.document.body);
                    
                    // The first audio element is typically the input, so we return the rest
                    var outputStems = [];
                    for(var i=1; i<stems.length; i++) {{
                        outputStems.push(stems[i]);
                    }}
                    return outputStems;
                }}
                
                function playAll() {{
                    var stems = getStemAudios();
                    console.log("Found " + stems.length + " audio elements to play.");
                    stems.forEach(function(a) {{
                        a.currentTime = 0;
                        var playPromise = a.play();
                        if (playPromise !== undefined) {{
                            playPromise.catch(error => {{ console.log("Playback prevented:", error); }});
                        }}
                    }});
                }}
                function pauseAll() {{
                    var stems = getStemAudios();
                    stems.forEach(function(a) {{
                        a.pause();
                    }});
                }}
            </script>
        </body>
        </html>
    """
    
    srcdoc_escaped = srcdoc_content.replace('"', '&quot;')
    html_player = f"<iframe style='width: 100%; height: 120px; border: none;' srcdoc=\"{srcdoc_escaped}\"></iframe>"
            
    return vocals_path, drums_path, bass_path, other_path, html_player

demo = gr.Interface(
    fn=separate_audio,
    inputs=gr.Audio(type="filepath", label="Upload Audio"),
    outputs=[
        gr.Audio(label="Vocals"),
        gr.Audio(label="Drums"),
        gr.Audio(label="Bass"),
        gr.Audio(label="Other"),
        gr.HTML(label="Synced Player")
    ],
    title="Spleeter Audio Separation Demo",
    description="Upload an audio track to separate it into individual stems.",
    allow_flagging="never"
)

if __name__ == "__main__":
    demo.launch()
