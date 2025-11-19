"""Setup script for MeetTranscribe."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="meettranscribe",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="State-of-the-art meeting transcription with speaker identification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/MeetTranscribe",
    packages=find_packages(exclude=["tests", "examples", "docs"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "meettranscribe=cli:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
