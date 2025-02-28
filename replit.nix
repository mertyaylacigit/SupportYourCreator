{ pkgs }: {
  deps = [
    pkgs.unixtools.ping
    pkgs.postgresql
    pkgs.glibcLocales
    pkgs.cacert
    pkgs.zip
    pkgs.python310
    pkgs.python310Packages.pip
  ];
}