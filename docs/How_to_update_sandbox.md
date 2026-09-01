---
short-description: How to update the sandbox used by the Pitivi development environment
...

# Updating the sandbox

We use the same [Flatpak
manifest](https://gitlab.gnome.org/GNOME/pitivi/blob/master/build/flatpak/org.pitivi.Pitivi.json)
for both the [development environment](HACKING.md) sandbox and for the [nightly
build snapshot](Install_with_flatpak.md).

To have the CI run the tests as fast as possible, we use a Docker image with
all the sandbox dependencies cached. This image needs to be updated whenever
we want to update the manifest, otherwise the CI fails since it can't download
the latest dependencies.

## Update the flatpak runtime

To update the flatpak runtime version, look in `org.pitivi.Pitivi.json` for the
current version:

```
    "runtime-version": "50",
```

Check out what is the latest flatpak runtime version. For example:

```
$ flatpak remote-ls --user flathub | grep org.gnome.Platform
```

Install both the runtime used by the manifest and its SDK. For this update:

```
$ flatpak --user install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

Check out in the git history how we updated the runtime version in the past and
repeat with the latest SDK.


## Update the sandbox dependencies

Some of them can be updated automatically with
[flatpak-external-data-checker](https://github.com/flathub/flatpak-external-data-checker):

```
$ flatpak --user install flathub org.flathub.flatpak-external-data-checker
$ flatpak run --user --filesystem="$(pwd)" org.flathub.flatpak-external-data-checker build/flatpak/org.pitivi.Pitivi.json --update --edit-only
```

The checker can update the manifest even if one of its checks fails. Treat any
`Failed to check` message as an error: inspect the diff, fix the affected
`x-checker-data`, then run the command again before committing the result.
Stage only the files that belong to this update; do not use `git commit -a`,
which can include unrelated local changes.

```
$ git add build/flatpak/org.pitivi.Pitivi.json
$ git commit -m "build: Update deps with flatpak-external-data-checker"
```

`x265` is intentionally pinned to 3.6 because x265 4 changes an API used by
the GStreamer version built by this sandbox. Do not re-add an automatic
checker for it until that compatibility issue is resolved.

Other deps have to be checked and updated manually.

## Update gst-plugins-rs

Follow the [official integration steps](https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs/-/blob/main/video/gtk4/README.md?ref_type=heads#flatpak-integration).

To generate the list of dependencies, prepare a Python venv:

```
$ python3 -m venv /tmp/pitivi-cargo-venv
$ /tmp/pitivi-cargo-venv/bin/pip install aiohttp tomlkit
$ git clone --depth=1 https://github.com/aleb/flatpak-builder-tools.git /tmp/pitivi-flatpak-builder-tools
```

.. and use it to run flatpak-cargo-generator, as per the official integration steps:

```
$ curl --fail --location --output /tmp/gst-plugin-gtk4.tar.gz https://static.crates.io/crates/gst-plugin-gtk4/gst-plugin-gtk4-0.15.2.crate
$ tar -xzf /tmp/gst-plugin-gtk4.tar.gz -C /tmp
$ /tmp/pitivi-cargo-venv/bin/python3 /tmp/pitivi-flatpak-builder-tools/cargo/flatpak-cargo-generator.py /tmp/gst-plugin-gtk4-0.15.2/Cargo.lock -o build/flatpak/gst-plugin-gtk4-sources.json
```

Replace `0.15.2` with the version selected in the `gst-plugins-rs` module of
the manifest. The generated file is already written to the correct location.

Finally, check what optimizations you can enable. For example for Gtk version 4.14.4 we can enable the `gtk_v4_14` feature in the `cargo cinstall --features=...` line. To get the version of the Gtk library in the Sdk run:

```
$ . bin/pitivi-env
(ptv-flatpak) $ ptvenv python3 -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print(f'{Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}.{Gtk.MICRO_VERSION}')"
4.22.4
```

Run `ptvenv` in the host shell after sourcing `bin/pitivi-env`. It is an alias
defined by that script, so it is intentionally not available from a raw
`flatpak run --command=bash` shell.

## Check the Python version

Check the Python version in the sandbox. For example, last time it was:

```
$ flatpak run --user --command=python3 org.gnome.Sdk//50 --version
Python 3.13.x
```

When the Python version changes, update the `/app/lib/python3.13` occurrences
in the [flatpak
manifest](https://gitlab.gnome.org/GNOME/pitivi/blob/master/build/flatpak/org.pitivi.Pitivi.json)
and also update the [Python dependencies](Updating_Python_dependencies.md).

When updating pylint, make a separate commit to fix the issues it complains
about:

```
(ptv-flatpak) $ ptvenv pre-commit run -a pylint
```

## Sync with flathub

Check if any changes to the [flathub Pitivi
manifest](https://github.com/flathub/org.pitivi.Pitivi) need to be ported over.

In particular, pay attention to the `shared-modules` git submodule to copy
`libcanberra` into `build/flatpak`.

## Rebuild your local dev env

```
$ . bin/pitivi-env
(ptv-flatpak) $ ptvenv --update
```

Run the tests:

```
(ptv-flatpak) $ ptvtests
(ptv-flatpak) $ pitivi
```

These commands require a graphical session; in a headless shell they can fail
with `Gdk-WARNING **: cannot open display`.

If all goes well, push the branch to origin to be able to initiate the
generation of the CI image.

```
$ git checkout -b sdk
$ git push origin sdk
```


## Build the CI image

The "Build docker image for the CI" [GitLab
Schedule](https://gitlab.gnome.org/GNOME/pitivi/-/pipeline_schedules) rebuilds
every 24h the image we use for running the unittests. This image caches
the build of dependencies described in our Flatpak manifest.

Since it's using the "master" branch, you have to create a new schedule and
select the branch you just pushed ("sdk"). Leave Active unchecked.

Go back to the Schedules page and click the Play button of the schedule you just
created to start a pipeline. Notice in the Last Pipeline column a link to the
pipeline you just started.

After the pipeline succeeds, create a regular MR with your manifest changes and
notice the CI is green. If you fail to merge the MR, the "Build docker image for
the CI" will kick in later and recreate the image according to the manifest on
branch "master".
