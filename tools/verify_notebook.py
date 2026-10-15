"""实际执行 Notebook，并与脚本产物逐张核对；不改变 Notebook 源文件。"""
import argparse
import asyncio
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, default=Path("docs/notebook-verification.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("Loading Notebook execution dependencies...", flush=True)
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import KernelManager

    notebook = nbformat.read(root / "WeatherForNanjing.ipynb", as_version=4)
    nbformat.validate(notebook)
    parameters = [cell for cell in notebook.cells if "parameters" in cell.metadata.get("tags", [])]
    if len(parameters) != 1:
        raise ValueError("Notebook must contain exactly one parameters cell")
    parameters[0].source += f"\nOUTPUT = Path({str(args.output.resolve())!r})\n"
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    client = NotebookClient(notebook, timeout=180, km=manager, resources={"metadata": {"path": str(root)}})
    print(f"Executing Notebook with {sys.executable}", flush=True)
    try:
        client.execute()
    finally:
        if client.kc is not None:
            client.kc.stop_channels()
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    reference = json.loads((args.reference / "manifest.json").read_text(encoding="utf-8"))
    actual = json.loads((args.output / "manifest.json").read_text(encoding="utf-8"))
    wanted = {image["name"]: image["sha256"] for image in reference["images"]}
    observed = {image["name"]: image["sha256"] for image in actual["images"]}
    if observed != wanted:
        differences = sorted(set(wanted) ^ set(observed) | {name for name in wanted.keys() & observed.keys() if wanted[name] != observed[name]})
        raise ValueError(f"Notebook/script output differs: {differences}")
    evidence = {"notebook_executed": True, "matching_png_count": len(observed), "input_sha256": actual["input"]["sha256"], "versions": actual["versions"], "executed_python": sys.version.split()[0]}
    with args.evidence.open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"Notebook executed; {len(observed)} PNG hashes match the script output.", flush=True)


if __name__ == "__main__":
    main()
