    # SigmaOS-wine-installer

    Wine prefix setup & Windows app installer

    Part of the **SigmaOS** sovereign operating-system ecosystem — a multi-repository
    distribution modelled on Linux Mint and Omarchy Linux. See the parent
    [`SigmaOS`](https://github.com/AaryanSinghChauhan09/SigmaOS) repository for the
    full component index.

    ## Upstream inspirations
    - https://github.com/linuxmint/wine-installer

    ## Design principles applied
    - **Defensive Programming**
- **Fail-Fast**
- **Separation of Concerns**
- **KISS**
- **Deterministic Testing**

    ## Usage
    Verbs: `prefix-plan, deps, install-plan, run`

    ```
    $ sigma-wine prefix-plan games
WINEPREFIX=~/.local/share/wine/prefixes/games  WINEARCH=win64
$ sigma-wine deps --manager apt
cabextract p7zip-full samba wine wine32 wine64 winetricks
$ sigma-wine install-plan setup.msi --prefix games
wine msiexec /i setup.msi /qn
$ sigma-wine run Launcher.exe --prefix games -- --fullscreen
wine Launcher.exe --fullscreen

    ```

    ## Build & test
    ```
    make build
    make test
    ```

    ## Licence
    GNU General Public License v3.0 (FOSS).
