"""Setup script for DCS Interconnection Diagram Generator."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dcs-interconnection-generator",
    version="1.0.0",
    author="Nayyer",
    author_email="nayyer@example.com",
    description="AI-powered DCS interconnection diagram generator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/dcs-interconnection-generator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Manufacturing",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
    ],
    python_requires=">=3.9",
    install_requires=[
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "pyyaml>=6.0",
        "svgwrite>=1.4.0",
        "reportlab>=4.0.0",
        "svglib>=1.5.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dcs-diagram=src.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.yaml", "templates/*.svg"],
    },
)
