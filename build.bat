f:
cd \Github\research-agent
pyinstaller --noconfirm --onedir --windowed --icon "C:/Users/furre/OneDrive/Documents/Icons/Lumicons/Reader Adobe PDF.ico" --name "Research Viewer" --clean --add-data "config.yaml;." research_viewer.py > build_log.txt 2>&1
type build_log.txt
