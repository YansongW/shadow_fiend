from setuptools import find_packages, setup

setup(
    name="shadow-fiend",
    version="0.0.2",
    description="Local real-time subtitle translation for movies and shows",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="YansongW",
    license="MIT",
    python_requires=">=3.10",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    py_modules=["main", "pipeline_streaming"],
    include_package_data=True,
    package_data={
        "ui": ["assets/*.png"],
    },
    install_requires=[
        "pyaudio>=0.2.14",
        "numpy>=1.26.0",
        "funasr>=1.1.0",
        "torch>=2.3.0",
        "torchaudio>=2.3.0",
        "argostranslate>=1.9.6",
        "transformers>=4.40.0",
        "sentencepiece>=0.2.0",
        "PyQt6>=6.7.0",
        "requests>=2.32.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.2.0",
            "build>=1.0.0",
            "twine>=5.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "shadow-fiend=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
    ],
)
