from time import sleep
from python_on_whales import docker

def export_perf_txt():
    bash_script = """
    for f in /workspaces/zeus/perf_data/*.data; do
        [ -e "$f" ] || continue
        report_file="${f%.data}_report.txt"
        if [ ! -f "$report_file" ]; then
            echo "Generating report for $f..."
            perf report -i "$f" --stdio --no-children -g folded > "$report_file"
        fi
    done
    """
    docker.compose.execute(
        "eiger-detector", 
        ["bash", "-c",bash_script],
        tty=False
    )

def main():
    perf_events = [ "branch-instructions", "branches",
    "branch-misses", "bus-cycles", "cache-misses", "cache-references",
    "cpu-cycles", "cycles", "instructions", "ref-cycles",
    "alignment-faults", "bpf-output", "cgroup-switches", "context-switches",
    "cs", "cpu-clock", "cpu-migrations", "migrations",
    "dummy", "emulation-faults", "major-faults", "minor-faults",
    "page-faults", "faults", "task-clock", ]

    for event in perf_events:
        print("starting stack")
        docker.compose.up(detach=True)
        sleep(10)
        #Run Tickit
        docker.compose.execute("tickit", ["bash", "-c", "cd /workspaces/zeus/tickit-devices/ && uv run tickit all examples/configs/eiger/eiger.yaml"], tty=False, detach=True)
        sleep(2)
        #Build eiger-detector and install
        docker.compose.execute("eiger-detector", ["cmake", "-DCMAKE_BUILD_TYPE:STRING=RelWithDebInfo", "-DCMAKE_INSTALL_PREFIX:STRING=/odin", "-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=TRUE", "-DCMAKE_C_COMPILER:FILEPATH=/usr/bin/gcc", "-DCMAKE_CXX_COMPILER:FILEPATH=/usr/bin/g++", "-DODINDATA_ROOT_DIR=/odin", "--no-warn-unused-cli", "-S", "/workspaces/zeus/eiger-detector/cpp", "-B", "/workspaces/zeus/eiger-detector/vscode_build", "-G", "Unix Makefiles"], tty=False)
        docker.compose.execute("eiger-detector", ["cmake", "--build", "/workspaces/zeus/eiger-detector/vscode_build", "--config", "RelWithDebInfo", "--target", "install", "VERBOSE=1", "-j", "20", "--"], tty=False)
        docker.compose.execute("eiger-detector", ["pip", "install", "-e", "/workspaces/zeus/eiger-detector/python[dev]", "--ignore-installed"], tty=False)
        docker.compose.execute("eiger-detector", 
                               ["zellij", "attach","--force-run-commands" ,"--create-background", "automated-session", "options", "--default-layout", "layout.kdl"], 
                               envs={"PERF_EVENTS":event, "PERF_ENABLE":"1"},workdir="/workspaces/zeus/eiger-detector/deploy", tty=False, detach=True)

        #Run fastcs_eiger
        docker.compose.execute("fastcs-eiger", ["uv", "run", "--directory", "/workspaces/zeus/fastcs-eiger", "-m", "fastcs_eiger", "ioc", "EIGER", "--odin-ip", "127.0.0.1"], tty=False, detach=True)
        sleep(10)
        docker.compose.execute("fastcs-eiger", ["uv", "run", "--directory", "/workspaces/zeus/fastcs-eiger", "python", "run_acquisition.py"], tty=False, detach=True)
        sleep(30)
        # Send kill to perf to gracefully exit
        docker.compose.execute("eiger-detector", ["pkill", "-2", "-f", "perf record"], tty=False)
        docker.compose.execute("eiger-detector", ["zellij", "delete-session", "automated-session"], tty=False)
        export_perf_txt()
        sleep(20)
        docker.compose.down()
    #TODO: start doing perf runs
    #TODO: Script naming perf to something other than perf.data
    #TODO: perf env vars to collect different metrics
    #TODO: instead of tearing down containers, just kill processes and restart them using execute

if __name__ == "__main__":
    main()
