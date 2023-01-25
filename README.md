# KronosCollider
Compile [Kronos](https://kronoslang.io/) code to SuperCollider UGens. It requires the `kc` executable to be installed in your `$PATH`.

## Installation

`git clone --recursive https://github.com/vitreo12/KronosCollider`

## Usage

Run the `kronoscollider.py` script. 

```
usage: kronoscollider.py [-h] [-s] [-e] [-r] file

Compile Kronos code to SuperCollider UGens

positional arguments:
  file                The .k file to compile

options:
  -h, --help          show this help message and exit
  -s, --scPath        The path to the SuperCollider source files. Defaults to:
                      '~/Sources/supercollider/'
  -e, --extPath       The path to the SuperCollider extensions directory. Defaults to:
                      '~/.local/share/SuperCollider/Extensions/'
  -r, --removeCache   Remove the build files from the cache folder in: '~/.cache/KronosCollider/'
```