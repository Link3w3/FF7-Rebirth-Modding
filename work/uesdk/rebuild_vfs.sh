WIN=/tmp/scratch/sdk
cd /work/uesdk && python3 make_vfs.py vfs.yaml /work/uesdk/Engine /work/uesdk/Project /work/uesdk/gen $WIN/msvc/include $WIN/kits/ucrt $WIN/kits/shared $WIN/kits/um "$@"
