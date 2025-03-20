{ pkgs }: {
  deps = [
    pkgs.htop
    pkgs.tk
    pkgs.tcl
    pkgs.qhull
    pkgs.pkg-config
    pkgs.gtk3
    pkgs.gobject-introspection
    pkgs.ghostscript
    pkgs.freetype
    pkgs.ffmpeg-full
    pkgs.cairo
    pkgs.libGLU
    pkgs.libGL
    pkgs.tesseract
    pkgs.unixtools.ping
    pkgs.postgresql
    pkgs.glibcLocales
    pkgs.cacert
    pkgs.zip
    pkgs.python310
    pkgs.python310Packages.pip
  ];
}