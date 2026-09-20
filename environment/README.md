# Environment

The frozen run used Ubuntu 22.04.5, Python 3.12.3, OpenJDK 17, NVIDIA driver
595.71.05, and PyTorch 2.8.0 built for CUDA 12.8 on one 24GB RTX 3090.

Install the CUDA 12.8 PyTorch wheel from the official PyTorch index, then install
`requirements-core.txt` and this project. Verify the installed versions against
`runtime_manifest.json`; newer package versions are not equivalent to the frozen
run merely because imports succeed.

The data disk should hold `HF_HOME`, the ALFWorld dataset, Java temporary files,
model weights, and native outputs. The project does not require Docker. Model
revision hashes are in `configs/models.json`; environment-executor and
ScienceWorld-JAR hashes are in `research/CONFIRMATION_METHOD_LOCK.json`.
