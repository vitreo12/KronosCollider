# KronosCollider
Compile [Kronos](https://kronoslang.io/) code to SuperCollider UGens. It requires the `kc` executable to be installed in your `$PATH`.

## Installation

`git clone --recursive https://github.com/vitreo12/KronosCollider`

## Usage

To specify `Params` and `Buffers`, `KronosCollider` leverages the [KronosExternal](https://github.com/vitreo12/KronosExternal) module, which is automatically imported. 

- To declare a parameter, use the `Param` package:

    ```
    Main() {
        ; Different ways to declare a parameter. p2 also implements min / max ranges.
        p1 = Param:New("p1" #1)
        p2 = Param:New("p2" #1 #0 #1)

        ... your code ...
    }
    ```

- To declare a `Buffer`, use the `Buffer` package:

    ```
    Main() {
        ; Different ways to declare a Buffer. b2 limits the maximum size to 48000 samples.
        ; If not specified, the default is 48000 * 30 (30 seconds of mono at 48khz).
        ; Note that a higher value does not impact performance or binary size, but just compilation times.
        b1 = Buffer:New("b1")
        b2 = Buffer:New("b2" #48000)

        ... your code ...
    }
    ```

- To declare audio inputs, the standard `Audio:Input` function will work:

    ```
    Import IO

    Main() {
        (in1 in2) = Audio:Input(0 0)

        ... your code ...
    }
    ```

## Compilation

Run the `kronoscollider.py` script. 

```
usage: kronoscollider.py [-h] [-s] [-e] [-r] [-i] file

Compile Kronos code to SuperCollider UGens

positional arguments:
  file                The .k file to compile

options:
  -h, --help          show this help message and exit
  -s, --scPath        The path to the SuperCollider source files. Defaults to: '~/Sources/supercollider/'
  -e, --extPath       The path to the SuperCollider extensions directory. Defaults to: '~/.local/share/SuperCollider/Extensions/'
  -r, --removeCache   Remove the build files from the cache folder in: '~/.cache/KronosCollider/'. Defaults to 1
  -i, --external      Import the KronosExternal module automatically. Defaults to 1
```