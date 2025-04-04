from setuptools import setup, find_packages

setup(
    name="sports_card_analyzer",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'streamlit',
        'pandas',
        'numpy',
        'plotly',
        'firebase-admin',
        'requests'
    ],
) 