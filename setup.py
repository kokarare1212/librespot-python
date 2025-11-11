import setuptools

setuptools.setup(name="librespot",
                 version="0.0.10",
                 description="Open Source Spotify Client",
                 long_description=open("README.md").read(),
                 long_description_content_type="text/markdown",
                 author="kokarare1212",
                 url="https://github.com/kokarare1212/librespot-python",
                 license="Apache-2.0",
                 packages=setuptools.find_packages("."),
                 install_requires=open("requirements.txt").read().splitlines(),
                 classifiers=[
                     "Development Status :: 1 - Planning",
                     "License :: OSI Approved :: Apache Software License",
                     "Topic :: Multimedia :: Sound/Audio"
                 ])
