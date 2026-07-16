in eiger-detector/python/setup.cfg:54
    tickit-devices @ git+https://github.com/DiamondLightSource/tickit-devices@fix-stream2-start

cp /dls/science/users/mef65357/stream2/* tickit-devices/src/tickit_devices/eiger/data/stream2/

- launch tickit

python -m tickit all tickit-devices/examples/configs/eiger/eiger.yaml

- in another terminal

cd deploy
zellij -l layout.kdl

- run fastcs

python -m fastcs_eiger ioc EIGER --odin-ip 127.0.0.1

