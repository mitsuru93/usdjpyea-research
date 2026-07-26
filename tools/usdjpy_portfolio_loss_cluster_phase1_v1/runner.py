from pathlib import Path
_src = "".join((Path(__file__).with_name(n).read_text(encoding="utf-8") for n in ["runner_part1.inc", "runner_part2.inc"]))
exec(compile(_src, str(Path(__file__).with_name("runner_combined.py")), "exec"), globals())
