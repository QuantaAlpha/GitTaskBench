# GitTaskBench
## 👋Overview
GitTaskBench is a comprehensive benchmark designed to evaluate the capabilities of intelligent agents across multiple modalities and task complexities. It encompasses **54 tasks** spanning **7 key domains**.

Each domain features a curated set of tasks that reflect real-world applications and research challenges. These tasks assess an agent's ability to interpret complex instructions, process multi-modal inputs, perform reasoning, and deliver accurate, meaningful outputs.
## ✅Task Distribution

| Domain                     | Task List                                                                                                                                                                  |
|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Image Processing           | Style Transfer, Image Coloring, Image Restoration, Scratch Detection, Image Reconstruction, Image Enhancement, Background Removal, Background Editing, Watermark Embedding |
| Video Processing           | Video Action Analysis, Style Transfer, Video Coloring                                                                                                                      |
| Speech Processing          | Speech Recognition, Speech Parsing/Recognition, Speech Separation/Noise Reduction, Speech Separation, Speech Enhancement, Speech Analysis                                  |
| Physiological Signals      | EDA (Electrodermal Activity), ECG (Electrocardiogram), EOG (Electrooculogram)                                                                                              |
| Security & Privacy         | Data Simulation, Watermark Embedding, Watermark Decoding, Watermark Extraction                                                                                             |
| Web Scraping               | Web Crawling                                                                                                                                                               |
| Office Document Processing | Document Parsing, Content Extraction, Content Processing                                                                                                                   |

## ✨Key Features:
- **Multi-Modal Support**: Encompasses vision, language, audio, time-series, and web-based data.
- **Diverse Task Types**: Includes generation, recognition, enhancement, analysis, and simulation tasks.
- **Real-World Relevance**: Tasks are derived from practical applications in media, healthcare, automation, and data science.
- **Scalability**: Designed for future expansion with new tasks and evaluation metrics.




## 🚀 Set Up
You can install `gittaskbench` with pip:
```console
cd gittaskbench
pip install -e .
```
also you can
```console
pip install -r requirements.txt
```

## 🤖Quick Start
```console
gittaskbench [-v] grade --taskid <taskid> [--output_dir <output_dir>] [--result <result>]
```
### 🔧Options:

- --taskid <taskid>: (Required) The task identifier, e.g., Trafilatura_01.
- -v: (Optional) Enable verbose output to display detailed error messages.
- --output_dir : (Optional) The directory containing the agent's output files. If not specified, the default value is read from task_info.yaml.
- --result :(Optional) The directory containing the agent's test results files. If not specified, the default value is read from task_info.yaml.
## 💡Example:
```console
gittaskbench grade --taskid Trafilatura_01
```
