# demo.tape — regenerate demo.gif with: vhs demo.tape
Output demo.gif

Set FontSize 14
Set Width 120
Set Height 32
Set Theme "Dracula"

Type "export ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
Enter
Sleep 500ms

Type "python -m src.agent \"What is quantum computing?\" --depth 2"
Enter
Sleep 60s

Screenshot demo-screenshot.png
