from time import sleep
from python_on_whales import docker

def main():
    print("starting stack")
    docker.compose.up(detach=True)
    sleep(10)
    docker.compose.execute("tickit", ["bash", "-c", "cd /workspaces/zeus/tickit-devices/ && uv run tickit all examples/configs/eiger/eiger.yaml"], tty=False, detach=True)
    sleep(2)
    docker.compose.execute("eiger-detector", ["cmake", "-DCMAKE_BUILD_TYPE:STRING=RelWithDebInfo", "-DCMAKE_INSTALL_PREFIX:STRING=/odin", "-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=TRUE", "-DCMAKE_C_COMPILER:FILEPATH=/usr/bin/gcc", "-DCMAKE_CXX_COMPILER:FILEPATH=/usr/bin/g++", "-DODINDATA_ROOT_DIR=/odin", "--no-warn-unused-cli", "-S", "/workspaces/zeus/eiger-detector/cpp", "-B", "/workspaces/zeus/eiger-detector/vscode_build", "-G", "Unix Makefiles"], tty=False)
    docker.compose.execute("eiger-detector", ["cmake", "--build", "/workspaces/zeus/eiger-detector/vscode_build", "--config", "RelWithDebInfo", "--target", "install", "VERBOSE=1", "-j", "20", "--"], tty=False)
    docker.compose.execute("eiger-detector", ["pip", "install", "-e", "/workspaces/zeus/eiger-detector/python[dev]", "--ignore-installed"], tty=False)
    docker.compose.execute("eiger-detector", ["zellij", "attach","--force-run-commands" ,"--create-background", "automated-session", "options", "--default-layout", "layout.kdl"],workdir="/workspaces/zeus/eiger-detector/deploy", tty=False, detach=True)
    docker.compose.execute("fastcs-eiger", ["uv", "run", "--directory", "/workspaces/zeus/fastcs-eiger", "-m", "fastcs_eiger", "ioc", "EIGER", "--odin-ip", "127.0.0.1"], tty=False, detach=True)
    sleep(300)
    #docker.compose.execute("fastcs-eiger", ["uv", "run", "--directory", "/workspaces/zeus/fastcs-eiger", "python", "run_acquisition.py"], tty=False, detach=True)


if __name__ == "__main__":
    main()
